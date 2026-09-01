import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';
import { useAppContext } from '../context/AppContext';


export const AnomalyChart: React.FC = () => {
  const { history, replayMode, replayTrajectory } = useAppContext();
  
  const data = replayMode ? replayTrajectory : history;
  
  if (!data || data.length === 0) {
    return <div className="h-64 flex items-center justify-center bg-white border rounded shadow">No data available</div>;
  }

  // Format data for chart
  const chartData = data.map((d, i) => ({
    time: i, // simple index for x-axis
    score: d.anomaly_score,
    isFailure: d.is_failure
  }));

  const failurePoint = chartData.find(d => d.isFailure);

  return (
    <div className="p-6 border rounded shadow bg-white h-80">
      <h3 className="text-xl font-bold mb-4">Anomaly Timeline</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="time" hide />
          <YAxis domain={[0, 1.1]} ticks={[0, 0.5, 0.8, 1.0]} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', color: '#fff', borderRadius: '4px' }}/>
          <ReferenceLine y={0.5} stroke="#f59e0b" strokeDasharray="3 3" label="WARNING" />
          <ReferenceLine y={0.8} stroke="#ef4444" strokeDasharray="3 3" label="CRITICAL" />
          {failurePoint && (
            <ReferenceLine x={failurePoint.time} stroke="#000" label="FAILURE" />
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
