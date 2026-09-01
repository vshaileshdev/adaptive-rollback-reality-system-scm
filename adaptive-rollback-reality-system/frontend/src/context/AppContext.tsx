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

  useEffect(() => {
    // Initial fetch
    axios.get(`${API_URL}/status`).then(res => {
      setStatus(res.data.status);
      setBufferLocked(res.data.buffer_locked);
      setSimulationRunning(res.data.simulation_running);
    }).catch(console.error);

    axios.get(`${API_URL}/metrics`).then(res => setMetrics(res.data)).catch(console.error);

    // WebSocket connection
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'state_update') {
        setCurrentState(data.data);
        setMetrics(data.metrics);
        setBufferLocked(data.buffer_locked);
        setTrajectoryReady(data.trajectory_ready);
        
        setHistory(prev => {
          const newHistory = [...prev, data.data];
          if (newHistory.length > 50) newHistory.shift(); // keep last 50 for live chart
          return newHistory;
        });

        if (data.trajectory_ready && !trajectoryReadyRef.current) {
          // trajectory just became ready, fetch trajectory
          fetchTrajectory();
        }
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      } else if (ws.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => ws.close();
      }
    };
  }, []);

  const startSimulation = () => axios.post(`${API_URL}/simulation/start`);
  const stopSimulation = () => axios.post(`${API_URL}/simulation/stop`);
  const triggerFailure = () => axios.post(`${API_URL}/simulation/failure`);

  const fetchTrajectory = () => {
    axios.get(`${API_URL}/trajectory/latest`).then(res => {
      if (res.data && res.data.trajectory) {
        setReplayTrajectory(res.data.trajectory);
        setRootCause(res.data.root_cause);
      }
    }).catch(console.error);
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
      startSimulation, stopSimulation, triggerFailure, setReplayMode,
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
