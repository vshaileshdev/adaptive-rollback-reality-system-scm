import React from 'react';
import { useAppContext } from '../context/AppContext';
import { DigitalTwin } from './DigitalTwin';
import { AnomalyChart } from './Charts';
import { ReplayControls } from './ReplayControls';
import { RootCausePanel } from './RootCausePanel';
import { Play, Square, Database, Zap, RotateCcw } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { 
    status, simulationRunning, bufferLocked, startSimulation, stopSimulation, triggerFailure, resetSimulation,
    currentState, metrics, replayMode, replayState
  } = useAppContext();

  const displayState = replayMode ? replayState : currentState;

  return (
    <div className="min-h-screen p-6 font-sans">
      {/* Header */}
      <header className="mb-8 flex justify-between items-center bg-white p-4 rounded shadow border-l-4 border-slate-900">
        <div>
          <h1 className="text-2xl font-black text-slate-800 tracking-tight">Adaptive Rollback Reality System</h1>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span className="flex items-center gap-1 text-sm font-bold">
              <span className={`w-3 h-3 rounded-full ${status === 'SYSTEM ONLINE' ? 'bg-normal' : 'bg-slate-400'}`}></span>
              {status}
            </span>
            <span className="text-sm text-slate-500 bg-slate-100 px-2 py-1 rounded font-medium">
              MODE: {simulationRunning ? 'DATASET STREAMING' : (replayMode ? 'TRAJECTORY REPLAY' : 'IDLE (WAITING)')}
            </span>
            <span className={`text-sm px-2 py-1 rounded font-bold ${bufferLocked ? 'bg-red-100 text-critical border border-red-200' : 'bg-green-100 text-normal border border-green-200'}`}>
              BUFFER: {bufferLocked ? 'LOCKED' : 'ACTIVE'}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          {!simulationRunning ? (
            <>
              <button onClick={startSimulation} className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded shadow hover:bg-slate-800 font-bold text-sm">
                <Play size={16} /> Start Stream
              </button>
              <button onClick={triggerFailure} className="flex items-center gap-2 bg-critical text-white px-4 py-2 rounded shadow hover:bg-red-600 font-bold text-sm">
                <Zap size={16} /> Demo Failure
              </button>
              <button onClick={resetSimulation} className="flex items-center gap-2 bg-slate-200 text-slate-800 px-3 py-2 rounded shadow hover:bg-slate-300 font-bold text-sm">
                <RotateCcw size={16} /> Reset
              </button>
            </>
          ) : (
            <>
              <button onClick={triggerFailure} className="flex items-center gap-2 bg-critical text-white px-4 py-2 rounded shadow hover:bg-red-600 font-bold text-sm">
                <Zap size={16} /> Demo Failure
              </button>
              <button onClick={stopSimulation} className="flex items-center gap-2 bg-slate-200 text-slate-800 px-3 py-2 rounded shadow hover:bg-slate-300 font-bold text-sm">
                <Square size={16} /> Stop Stream
              </button>
              <button onClick={resetSimulation} className="flex items-center gap-2 bg-slate-100 text-slate-600 px-3 py-2 rounded shadow hover:bg-slate-200 font-bold text-sm">
                <RotateCcw size={16} /> Reset
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* Left Col - Twin & Metrics */}
        <div className="space-y-6">
          <DigitalTwin state={displayState} />
          
          <div className="p-6 border rounded shadow bg-white">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2"><Database size={20}/> Adaptive Checkpointing</h3>
            {metrics ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-slate-500">States Received</span>
                  <span className="font-mono font-bold text-lg">{metrics.total_states_received}</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b">
                  <span className="text-slate-500">Checkpoints Saved</span>
                  <span className="font-mono font-bold text-lg text-normal">{metrics.total_checkpoints}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Storage Saved</span>
                  <span className="font-mono font-bold text-lg text-blue-600">
                    {metrics.total_states_received > 0 
                      ? ((metrics.storage_saved / metrics.total_states_received) * 100).toFixed(1) 
                      : 0}%
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-slate-500 text-sm">No metrics available.</p>
            )}
          </div>
        </div>

        {/* Middle/Right Col - Charts & Controls */}
        <div className="lg:col-span-2 space-y-6">
          <AnomalyChart />
          <ReplayControls />
        </div>
      </div>

      <RootCausePanel />
    </div>
  );
};
