import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import axios from 'axios';
import type { PhysicalStateVector, Metrics, RootCause } from '../types';
// Force Vite HMR cache update

interface AppContextType {
  status: string;
  bufferLocked: boolean;
  simulationRunning: boolean;
  currentState: PhysicalStateVector | null;
  metrics: Metrics | null;
  history: PhysicalStateVector[];
  replayMode: boolean;
  replayState: PhysicalStateVector | null;
  rootCause: RootCause | null;
  startSimulation: () => void;
  stopSimulation: () => void;
  triggerFailure: () => void;
  resetSimulation: () => void;
  setReplayMode: (val: boolean) => void;
  stepForward: () => void;
  stepBackward: () => void;
  resetReplay: () => void;
  fetchTrajectory: () => void;
  replayTrajectory: PhysicalStateVector[];
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState('OFFLINE');
  const [bufferLocked, setBufferLocked] = useState(false);
  const [trajectoryReady, setTrajectoryReady] = useState(false);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [currentState, setCurrentState] = useState<PhysicalStateVector | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [history, setHistory] = useState<PhysicalStateVector[]>([]);

  const [replayMode, setReplayMode] = useState(false);
  const [replayState, setReplayState] = useState<PhysicalStateVector | null>(null);
  const [replayTrajectory, setReplayTrajectory] = useState<PhysicalStateVector[]>([]);
  const [rootCause, setRootCause] = useState<RootCause | null>(null);

  const API_URL = "http://localhost:8001/api";
  const WS_URL = "ws://localhost:8001/ws";

  const bufferLockedRef = useRef(bufferLocked);
  useEffect(() => {
    bufferLockedRef.current = bufferLocked;
  }, [bufferLocked]);

  const trajectoryReadyRef = useRef(trajectoryReady);
  useEffect(() => {
    trajectoryReadyRef.current = trajectoryReady;
  }, [trajectoryReady]);

  const fetchTrajectory = () => {
    axios.get(`${API_URL}/trajectory/latest`).then(res => {
      if (res.data && res.data.trajectory) {
        setReplayTrajectory(res.data.trajectory);
        setRootCause(res.data.root_cause);
      }
    }).catch(console.error);
  };

  useEffect(() => {
    // Initial fetch
    axios.get(`${API_URL}/status`).then(res => {
      setStatus(res.data.status);
      setBufferLocked(res.data.buffer_locked);
      setSimulationRunning(res.data.simulation_running);
      if (res.data.trajectory_ready || res.data.buffer_locked) {
        fetchTrajectory();
      }
    }).catch(console.error);

    axios.get(`${API_URL}/metrics`).then(res => setMetrics(res.data)).catch(console.error);

    // WebSocket connection with auto-reconnect
    let isMounted = true;
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connectWs = () => {
      if (!isMounted) return;
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (isMounted) setStatus('SYSTEM ONLINE');
      };

      ws.onclose = () => {
        if (isMounted) {
          setStatus('OFFLINE');
          reconnectTimer = setTimeout(connectWs, 2000);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'state_update') {
            if (data.data !== undefined) {
              setCurrentState(data.data);
            }
            if (data.metrics !== undefined) {
              setMetrics(data.metrics);
            }
            if (data.buffer_locked !== undefined) {
              setBufferLocked(data.buffer_locked);
            }
            if (data.trajectory_ready !== undefined) {
              setTrajectoryReady(data.trajectory_ready);
            }
            if (data.simulation_running !== undefined) {
              setSimulationRunning(data.simulation_running);
            }

            if (data.data) {
              setHistory(prev => {
                const newHistory = [...prev, data.data];
                if (newHistory.length > 50) newHistory.shift(); // keep last 50 for live chart
                return newHistory;
              });
            }

            if (data.trajectory_ready && !trajectoryReadyRef.current) {
              fetchTrajectory();
            }
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };
    };

    connectWs();

    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        const socket = ws;
        if (socket.readyState === WebSocket.OPEN) {
          socket.close();
        } else if (socket.readyState === WebSocket.CONNECTING) {
          socket.onopen = () => socket.close();
        }
      }
    };
  }, []);

  const startSimulation = () => {
    setReplayMode(false);
    setReplayState(null);
    setSimulationRunning(true);
    axios.post(`${API_URL}/simulation/start`).catch(console.error);
  };

  const stopSimulation = () => {
    setSimulationRunning(false);
    axios.post(`${API_URL}/simulation/stop`).catch(console.error);
  };

  const triggerFailure = () => {
    setReplayMode(false);
    setReplayState(null);
    setTrajectoryReady(false);
    setBufferLocked(false);
    setRootCause(null);
    setReplayTrajectory([]);
    setSimulationRunning(true);
    axios.post(`${API_URL}/simulation/failure`).catch(console.error);
  };

  const resetSimulation = () => {
    setReplayMode(false);
    setReplayState(null);
    setTrajectoryReady(false);
    setBufferLocked(false);
    setRootCause(null);
    setReplayTrajectory([]);
    setCurrentState(null);
    setHistory([]);
    setSimulationRunning(false);
    axios.post(`${API_URL}/simulation/reset`).catch(console.error);
  };

  const stepForward = () => {
    axios.post(`${API_URL}/replay/step-forward`).then(res => setReplayState(res.data.state));
  };

  const stepBackward = () => {
    axios.post(`${API_URL}/replay/step-backward`).then(res => setReplayState(res.data.state));
  };

  const resetReplay = () => {
    axios.post(`${API_URL}/replay/reset`).then(res => setReplayState(res.data.state));
  };

  useEffect(() => {
    if (replayMode) {
      axios.post(`${API_URL}/replay/start`).then(() => resetReplay());
    }
  }, [replayMode]);

  return (
    <AppContext.Provider value={{
      status, bufferLocked, simulationRunning, currentState, metrics, history,
      replayMode, replayState, rootCause, replayTrajectory,
      startSimulation, stopSimulation, triggerFailure, resetSimulation, setReplayMode,
      stepForward, stepBackward, resetReplay, fetchTrajectory
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error("useAppContext must be used within AppProvider");
  return context;
};
