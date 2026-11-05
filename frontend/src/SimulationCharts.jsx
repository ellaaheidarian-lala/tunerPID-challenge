import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend } from 'recharts';
export default function SimulationCharts({ data }) {
  if (!data || !data.time_points) return null;
  const chartData = data.time_points.map((t, index) => ({
    time: t,
    output: data.trajectory[index],
    target: data.target ?? 0,
    control: data.control_signals[index],
  }));
  return (
    <div className="space-y-6 w-full">
      <div className="bg-gray-800/50 border border-gray-700/50 p-4 rounded-xl shadow-lg backdrop-blur-sm">
        <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500"></span>
          System Output vs Desired Target
        </h3>
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
              <XAxis type="number" domain={['dataMin', 'dataMax']} unit=" s" dataKey="time" stroke="#9ca3af" fontSize={12} tickLine={false} />
              <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', borderRadius: '0.5rem', color: '#fff' }} />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
              <Line type="linear" isAnimationActive={false} dataKey="output" stroke="#3b82f6" name="System Output" dot={false} strokeWidth={2} />
              <Line type="linear" isAnimationActive={false} dataKey="target" stroke="#ef4444" name="Desired Target" strokeDasharray="4 4" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="bg-gray-800/50 border border-gray-700/50 p-4 rounded-xl shadow-lg backdrop-blur-sm">
        <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          Control Input (Effort)
        </h3>
        <div className="h-[220px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
              <XAxis type="number" domain={['dataMin', 'dataMax']} unit=" s" dataKey="time" stroke="#9ca3af" fontSize={12} tickLine={false} />
              <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', borderRadius: '0.5rem', color: '#fff' }} />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
              <Line type="linear" isAnimationActive={false} dataKey="control" stroke="#10b981" name="Control Input (u)" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
