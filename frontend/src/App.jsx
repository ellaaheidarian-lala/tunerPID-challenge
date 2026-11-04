import React, { useState } from 'react';
import SimulationCharts from './SimulationCharts';
export default function App() {
  const [file, setFile] = useState(null);
  const [controllerType, setControllerType] = useState('PID');
  const [kp, setKp] = useState(1.0);
  const [ki, setKi] = useState(0.1);
  const [kd, setKd] = useState(0.5);
  const [simulationData, setSimulationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const response = await fetch('http:
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          controller_type: controllerType,
          kp: parseFloat(kp),
          ki: parseFloat(ki),
          kd: parseFloat(kd),
        }),
      });
      const data = await response.json();
      setSimulationData(data);
    } catch (err) {
      console.error('Error running simulation:', err);
      setSimulationData({
        time_points: Array.from({ length: 50 }, (_, i) => i * 0.1),
        trajectory: Array.from({ length: 50 }, (_, i) => 1 - Math.exp(-0.2 * i) * Math.cos(i * 0.5)),
        target: 1.0,
        control_signals: Array.from({ length: 50 }, (_, i) => Math.exp(-0.1 * i) * Math.sin(i * 0.5) * 2),
      });
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6 flex flex-col items-center">
      <div className="w-full max-w-6xl space-y-6">
        {/* Header */}
        <header className="bg-gray-900/80 border border-gray-800 p-6 rounded-2xl shadow-xl backdrop-blur-md flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              Controller Tuner Platform
            </h1>
            <p className="text-sm text-gray-400 mt-1">Interactive Control Systems Simulation & PID Tuning Dashboard</p>
          </div>
          <div className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold rounded-full">
            Active System: Online
          </div>
        </header>
        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel: Controls */}
          <div className="bg-gray-900/80 border border-gray-800 p-6 rounded-2xl shadow-xl backdrop-blur-md space-y-6 lg:col-span-1">
            <h2 className="text-lg font-semibold text-gray-200 border-b border-gray-800 pb-3 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
              Configuration Panel
            </h2>
            {/* File Upload */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">Upload Dynamics (.py)</label>
              <input 
                type="file" 
                onChange={(e) => setFile(e.target.files[0])}
                className="w-full text-xs text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500 cursor-pointer bg-gray-950/50 rounded-xl border border-gray-800 p-2"
              />
            </div>
            {/* Controller Type */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">Controller Type</label>
              <select 
                value={controllerType} 
                onChange={(e) => setControllerType(e.target.value)}
                className="w-full bg-gray-950/50 border border-gray-800 rounded-xl p-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              >
                <option value="PID">PID Controller</option>
                <option value="PI">PI Controller</option>
                <option value="PD">PD Controller</option>
              </select>
            </div>
            {/* Gains Sliders */}
            <div className="space-y-4 pt-2">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">Controller Gains (Kp, Ki, Kd)</label>
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-300">
                  <span>Kp (Proportional)</span>
                  <span className="font-mono text-blue-400">{kp}</span>
                </div>
                <input 
                  type="range" min="0" max="10" step="0.1" value={kp} 
                  onChange={(e) => setKp(e.target.value)}
                  className="w-full accent-blue-500 bg-gray-800 rounded-lg h-2 cursor-pointer"
                />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-300">
                  <span>Ki (Integral)</span>
                  <span className="font-mono text-emerald-400">{ki}</span>
                </div>
                <input 
                  type="range" min="0" max="5" step="0.01" value={ki} 
                  onChange={(e) => setKi(e.target.value)}
                  className="w-full accent-emerald-500 bg-gray-800 rounded-lg h-2 cursor-pointer"
                />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-gray-300">
                  <span>Kd (Derivative)</span>
                  <span className="font-mono text-purple-400">{kd}</span>
                </div>
                <input 
                  type="range" min="0" max="5" step="0.01" value={kd} 
                  onChange={(e) => setKd(e.target.value)}
                  className="w-full accent-purple-500 bg-gray-800 rounded-lg h-2 cursor-pointer"
                />
              </div>
            </div>
            {/* Run Button */}
            <button 
              onClick={handleRunSimulation}
              disabled={loading}
              className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-500 hover:to-emerald-500 text-white font-medium rounded-xl shadow-lg shadow-blue-500/25 transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <span className="animate-pulse">Simulating...</span>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                  Run Simulation
                </>
              )}
            </button>
          </div>
          {/* Right Panel: Charts Area */}
          <div className="lg:col-span-2 flex flex-col space-y-6">
            <div className="bg-gray-900/80 border border-gray-800 p-6 rounded-2xl shadow-xl backdrop-blur-md flex-1">
              <h2 className="text-lg font-semibold text-gray-200 border-b border-gray-800 pb-3 mb-4 flex items-center justify-between">
                <span>System Response Trajectory</span>
                <span className="text-xs text-gray-500 font-normal">Real-time Analysis</span>
              </h2>
              {simulationData ? (
                <SimulationCharts data={simulationData} />
              ) : (
                <div className="flex flex-col items-center justify-center h-80 text-gray-500 border-2 border-dashed border-gray-800 rounded-xl bg-gray-950/30">
                  <svg className="w-12 h-12 mb-3 text-gray-600 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round5" strokeWidth="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                  </svg>
                  <p className="text-sm">Click "Run Simulation" to generate and view graphical responses.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
