import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';
import { useAppContext } from '../context/AppContext';


export const AnomalyChart: React.FC = () => {
  const { history, replayMode, replayTrajectory, replayState } = useAppContext();

  const data = replayMode ? replayTrajectory : history;

  if (!data || data.length === 0) {
    return <div className="h-64 flex items-center justify-center bg-white border rounded shadow">No data available</div>;
  }

  // Format data for chart
  const chartData = data.map((d, i) => ({
    index: i,
    time: d.timestamp ? (d.timestamp.includes(' ') ? d.timestamp.split(' ')[1] : d.timestamp) : `${i}`,
    score: Number(d.anomaly_score.toFixed(4)),
    isFailure: d.is_failure,
    isCurrentReplay: replayMode && replayState ? d.timestamp === replayState.timestamp : false
  }));

  const failurePoint = chartData.find(d => d.isFailure);
  const activeReplayPoint = chartData.find(d => d.isCurrentReplay);

  return (
    <div className="p-6 border rounded shadow bg-white h-80">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold">Anomaly Timeline</h3>
        <span className="text-xs font-mono text-slate-500">
          {replayMode ? `REPLAY TRAJECTORY (${chartData.length} steps)` : `LIVE TELEMETRY (${chartData.length} steps)`}
        </span>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="index" hide />
          <YAxis domain={[0, 1.1]} ticks={[0, 0.5, 0.8, 1.0]} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: '4px' }}/>
          <ReferenceLine y={0.5} stroke="#f59e0b" strokeDasharray="3 3" label="WARNING" />
          <ReferenceLine y={0.8} stroke="#ef4444" strokeDasharray="3 3" label="CRITICAL" />
          {failurePoint && (
            <ReferenceLine x={failurePoint.index} stroke="#ef4444" strokeWidth={2} label={{ value: "FAILURE", fill: "#ef4444", fontWeight: "bold" }} />
          )}
          {activeReplayPoint && (
            <ReferenceLine x={activeReplayPoint.index} stroke="#3b82f6" strokeWidth={2} strokeDasharray="3 3" label={{ value: "REPLAY", fill: "#3b82f6", fontWeight: "bold" }} />
          )}
          <Line 
            type="monotone" 
            dataKey="score" 
            stroke="#3b82f6" 
            strokeWidth={3}
            dot={false}
            isAnimationActive={!replayMode}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
