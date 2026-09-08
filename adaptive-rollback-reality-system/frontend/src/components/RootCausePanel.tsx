import React from 'react';
import { useAppContext } from '../context/AppContext';

export const RootCausePanel: React.FC = () => {
  const { rootCause, bufferLocked } = useAppContext();

  if (!bufferLocked) return null;
  if (!rootCause || rootCause.ranked_causes.length === 0) {
    return (
      <div className="p-6 border rounded shadow bg-white mt-6">
        <h3 className="text-xl font-bold mb-4">Root-Cause Analysis</h3>
        <p className="text-slate-500">Waiting for analysis...</p>
      </div>
    );
  }

  return (
    <div className="p-6 border rounded shadow bg-white mt-6">
      <h3 className="text-xl font-bold mb-4">Root-Cause Reconstruction</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h4 className="font-semibold text-slate-700 mb-3">Causal Dependency Graph (Estimated)</h4>
          <div className="flex flex-col gap-2">
            {rootCause.causal_graph.map((node, i) => (
              <div key={i} className="flex flex-col items-center">
                <div className="px-4 py-2 bg-slate-800 text-white rounded font-medium shadow w-full text-center">
                  {node.replace("_", " ").toUpperCase()}
                </div>
                {i < rootCause.causal_graph.length - 1 && (
                  <div className="h-6 border-l-2 border-slate-400 my-1"></div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="font-semibold text-slate-700 mb-3">Ranked Contributors</h4>
          <ul className="space-y-3">
            {rootCause.ranked_causes.map((cause, i) => (
              <li key={i} className="p-3 border rounded bg-slate-50 flex justify-between items-center">
                <div>
                  <span className="font-bold text-slate-800 block">{i+1}. {cause.parameter.replace("_", " ").toUpperCase()}</span>
                  {cause.first_deviation_index !== -1 ? (
                    <span className="text-sm text-slate-500">
                      Deviation at Step {cause.first_deviation_index + 1} (Max Z: {cause.max_deviation_z.toFixed(2)}σ)
                    </span>
                  ) : (
                    <span className="text-sm text-slate-400 italic">Nominal baseline (Max Z: {cause.max_deviation_z.toFixed(2)}σ)</span>
                  )}
                </div>
                <div className="text-right">
                  <span className="font-bold text-critical block">{cause.contribution_percent.toFixed(1)}%</span>
                  <span className="text-xs text-slate-400">Contribution</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
