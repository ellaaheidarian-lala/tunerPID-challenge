import React, { useState } from 'react';
import SimulationCharts from './SimulationCharts';
function App() {
  const [simulationData, setSimulationData] = useState(null);
  const [kp, setKp] = useState(1.0);
  const [ki, setKi] = useState(0.1);
  const [kd, setKd] = useState(0.5);
  const handleRunSimulation = async () => {
    try {
      const response = await fetch('http:
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kp, ki, kd })
      });
      const data = await response.json();
      setSimulationData(data);
    } catch (error) {
      console.error("Error running simulation:", error);
    }
  };
  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-2xl font-bold mb-4">Controller Tuner Platform</h1>
      <div className="mb-6 space-y-4 bg-gray-800 p-4 rounded-lg">
        <div>
          <label>Kp: {kp}</label>
          <input type="range" min="0" max="10" step="0.1" value={kp} onChange={(e) => setKp(parseFloat(e.target.value))} className="w-full" />
        </div>
        <div>
          <label>Ki: {ki}</label>
          <input type="range" min="0" max="5" step="0.01" value={ki} onChange={(e) => setKi(parseFloat(e.target.value))} className="w-full" />
        </div>
        <div>
          <label>Kd: {kd}</label>
          <input type="range" min="0" max="5" step="0.01" value={kd} onChange={(e) => setKd(parseFloat(e.target.value))} className="w-full" />
        </div>
        <button onClick={handleRunSimulation} className="bg-blue-600 px-4 py-2 rounded hover:bg-blue-700">
          Run Simulation
        </button>
      </div>
      {simulationData ? (
        <SimulationCharts data={simulationData} />
      ) : (
        <p className="text-gray-400">Run simulation to view trajectory response.</p>
      )}
    </div>
  );
}
export default App;
