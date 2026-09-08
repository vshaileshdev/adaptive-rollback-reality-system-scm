import React from 'react';
import type { PhysicalStateVector } from '../types';

interface Props {
  state: PhysicalStateVector | null;
}

export const DigitalTwin: React.FC<Props> = ({ state }) => {
  if (!state) return <div className="p-4 border rounded shadow bg-white h-64 flex items-center justify-center">Waiting for state...</div>;

  let colorClass = "bg-normal text-white";
  let pulseClass = "";

  if (state.machine_status === "WARNING") {
    colorClass = "bg-warning text-white";
    pulseClass = "animate-pulse";
  } else if (state.machine_status === "CRITICAL") {
    colorClass = "bg-critical text-white";
    pulseClass = "animate-pulse";
  } else if (state.machine_status === "FAILURE") {
    colorClass = "bg-slate-900 text-white";
  }

  // Calculate rotation animation duration based on speed
  const rotationDuration = state.rotational_speed > 0 ? `${60 / state.rotational_speed}s` : '0s';

  return (
    <div className="p-6 border rounded shadow bg-white flex flex-col items-center">
      <h3 className="text-xl font-bold mb-4">Digital Twin</h3>
      <div className={`w-48 h-48 rounded-full flex flex-col items-center justify-center transition-colors duration-300 ${colorClass} ${pulseClass}`}>
        <span className="text-2xl font-black">{state.machine_status}</span>
        {state.rotational_speed > 0 && (
            <svg
              className="mt-4 w-12 h-12 text-white opacity-80"
              style={{ animation: `spin ${rotationDuration} linear infinite` }}
              fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
        )}
      </div>
      <div className="mt-6 grid grid-cols-2 gap-4 w-full text-sm">
        <div className="bg-slate-100 p-2 rounded">
          <span className="font-semibold text-slate-500">Temp:</span> {state.air_temperature.toFixed(1)}°C
        </div>
        <div className="bg-slate-100 p-2 rounded">
          <span className="font-semibold text-slate-500">Vibration:</span> {state.vibration.toFixed(2)}
        </div>
        <div className="bg-slate-100 p-2 rounded">
          <span className="font-semibold text-slate-500">Speed:</span> {state.rotational_speed.toFixed(0)} rpm
        </div>
        <div className="bg-slate-100 p-2 rounded">
          <span className="font-semibold text-slate-500">Torque:</span> {state.torque.toFixed(1)} Nm
        </div>
      </div>
    </div>
  );
};
