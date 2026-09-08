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
    replayTrajectory,
    replayState
  } = useAppContext();

  if (!bufferLocked) {
    return (
      <div className="p-6 border rounded shadow bg-white">
        <h3 className="text-xl font-bold mb-4">Trajectory Replay</h3>
        <p className="text-slate-500">Buffer is active. Waiting for a failure event to lock the buffer and extract a trajectory.</p>
      </div>
    );
  }

  const isTrajectoryReady = replayTrajectory && replayTrajectory.length > 0;
  const currentIndex = isTrajectoryReady && replayState
    ? replayTrajectory.findIndex(s => s.timestamp === replayState.timestamp)
    : 0;

  return (
    <div className="p-6 border rounded shadow bg-slate-900 text-white">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold flex items-center gap-2">
            <AlertTriangle className="text-warning" />
            Trajectory Replay
          </h3>
          <span className="text-xs text-red-400 font-mono">RING BUFFER LOCKED (INCIDENT CAPTURED)</span>
        </div>
        <button 
          onClick={() => isTrajectoryReady && setReplayMode(!replayMode)}
          disabled={!isTrajectoryReady}
          className={`px-4 py-2 rounded font-bold transition-colors ${
            !isTrajectoryReady
              ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
              : (replayMode ? 'bg-critical hover:bg-red-600' : 'bg-normal hover:bg-emerald-600')
          }`}
        >
          {!isTrajectoryReady ? 'Extracting Trajectory...' : (replayMode ? 'Exit Replay' : 'Enter Replay Mode')}
        </button>
      </div>

      {replayMode && isTrajectoryReady && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between bg-slate-800 px-4 py-2 rounded text-xs font-mono">
            <span>STEP: {currentIndex >= 0 ? currentIndex + 1 : 1} / {replayTrajectory.length}</span>
            <span>TIME: {replayState?.timestamp || 'N/A'}</span>
            <span className={`font-bold ${replayState?.is_failure ? 'text-critical' : 'text-slate-300'}`}>
              STATUS: {replayState?.machine_status || 'UNKNOWN'}
            </span>
          </div>

          <div className="flex items-center justify-center gap-6 p-4 bg-slate-800 rounded">
            <button
              onClick={stepBackward}
              title="Step Backward (Earlier in time)"
              className="p-3 bg-slate-700 hover:bg-slate-600 rounded-full transition-colors flex items-center gap-1 font-bold text-sm"
            >
              <SkipBack size={20} /> Prev
            </button>
            <button
              onClick={resetReplay}
              title="Reset to Trajectory Start"
              className="p-3 bg-slate-700 hover:bg-slate-600 rounded-full transition-colors flex items-center gap-1 font-bold text-sm"
            >
              <RotateCcw size={20} /> Reset
            </button>
            <button
              onClick={stepForward}
              title="Step Forward (Closer to/past failure)"
              className="p-3 bg-slate-700 hover:bg-slate-600 rounded-full transition-colors flex items-center gap-1 font-bold text-sm"
            >
              Next <SkipForward size={20} />
            </button>
          </div>

          <div className="mt-2">
            <div className="flex justify-between text-xs text-slate-400 mb-1 font-mono">
              <span>PRE-FAILURE WINDOW</span>
              <span>FAILURE POINT</span>
              <span>POST-FAILURE WINDOW</span>
            </div>
            <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden flex p-0.5 gap-0.5">
              {replayTrajectory.map((s, i) => {
                let bg = 'bg-normal';
                if (s.is_failure) bg = 'bg-critical';
                else if (s.anomaly_score > 0.8) bg = 'bg-critical';
                else if (s.anomaly_score > 0.5) bg = 'bg-warning';
                const isCurrent = i === currentIndex;
                return (
                  <div
                    key={i}
                    title={`Step ${i+1}: ${s.timestamp} [${s.machine_status}] (score: ${s.anomaly_score.toFixed(3)})`}
                    className={`flex-1 ${bg} rounded-sm transition-all ${
                      isCurrent ? 'ring-2 ring-white scale-y-125 z-10 brightness-125' : 'opacity-70'
                    }`}
                  />
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
