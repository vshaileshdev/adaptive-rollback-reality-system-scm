import React from 'react';
import { SkipBack, SkipForward, RotateCcw, AlertTriangle } from 'lucide-react';
import { useAppContext } from '../context/AppContext';

export const ReplayControls: React.FC = () => {
  const { 
    replayMode, 
    setReplayMode, 
    stepForward, 
    stepBackward, 
    resetReplay,
    bufferLocked,
    replayTrajectory
  } = useAppContext();

  if (!bufferLocked) {
    return (
      <div className="p-6 border rounded shadow bg-white">
        <h3 className="text-xl font-bold mb-4">Trajectory Replay</h3>
        <p className="text-slate-500">Buffer is active. Waiting for a failure event to lock the buffer and extract a trajectory.</p>
      </div>
    );
  }

  return (
    <div className="p-6 border rounded shadow bg-slate-900 text-white">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold flex items-center gap-2">
          <AlertTriangle className="text-warning" />
          Trajectory Replay
        </h3>
        <button 
          onClick={() => setReplayMode(!replayMode)}
          className={`px-4 py-2 rounded font-bold ${replayMode ? 'bg-critical' : 'bg-normal'}`}
        >
          {replayMode ? 'Exit Replay' : 'Enter Replay Mode'}
        </button>
      </div>

      {replayMode && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-center gap-6 p-4 bg-slate-800 rounded">
            <button onClick={stepBackward} className="p-3 bg-slate-700 hover:bg-slate-600 rounded-full transition-colors">
              <SkipBack size={24} />
            </button>
            <button onClick={resetReplay} className="p-3 bg-slate-700 hover:bg-slate-600 rounded-full transition-colors">
              <RotateCcw size={24} />
            </button>
            <button onClick={stepForward} className="p-3 bg-slate-700 hover:bg-slate-600 rounded-full transition-colors">
              <SkipForward size={24} />
            </button>
          </div>
          
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-slate-400 mb-2">Replay Window ({replayTrajectory.length} states)</h4>
            <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden flex">
              {replayTrajectory.map((s, i) => {
                let bg = 'bg-normal';
                if (s.is_failure) bg = 'bg-critical';
                else if (s.anomaly_score > 0.8) bg = 'bg-critical';
                else if (s.anomaly_score > 0.5) bg = 'bg-warning';
                return <div key={i} className={`flex-1 ${bg} opacity-80 border-r border-slate-900 last:border-0`} />;
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
