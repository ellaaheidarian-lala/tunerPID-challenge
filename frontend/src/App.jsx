import React, { lazy, Suspense, useState } from "react";
const SimulationCharts = lazy(() => import("./SimulationCharts"));

import { api } from "./api";
import MetricsPanel from "./MetricsPanel";

const defaults = {
  dt: 0.01,
  max_time: 5,
  target: 0,
  min_control: -10,
  max_control: 10,
};
const preferred = { Kp: 1, Ki: 0.1, Kd: 0.5 };
const defaultGains = (schema) =>
  Object.fromEntries(
    Object.entries(schema).map(([key, range]) => [
      key,
      Math.min(
        range.max,
        Math.max(range.min, preferred[key] ?? (range.min + range.max) / 2),
      ),
    ]),
  );

export default function App() {
  const [system, setSystem] = useState(null);
  const [selectedFileName, setSelectedFileName] = useState("");
  const [controller, setController] = useState("PID");
  const [schema, setSchema] = useState({});
  const [gains, setGains] = useState({});
  const [config, setConfig] = useState(defaults);
  const [fixed, setFixed] = useState(true);
  const [initial, setInitial] = useState("1, 0");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function upload(file) {
    if (!file) return;
    const previous = system;
    setSelectedFileName(file.name);
    setError("");
    setResult(null);
    setSystem(null);
    setSchema({});
    setGains({});
    if (file.size > 256 * 1024) {
      setError("Choose a file no larger than 256 KiB.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".py")) {
      setError("Choose a .py dynamics file.");
      return;
    }
    setBusy("Uploading…");
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await api("/upload", { method: "POST", body: form });
      const nextSchema = await api(
        `/systems/${uploaded.system_id}/schema?controller_type=${controller}`,
      );
      setSystem(uploaded);
      setSchema(nextSchema);
      setGains(defaultGains(nextSchema));
      setInitial([1, ...Array(uploaded.num_states - 1).fill(0)].join(", "));
      if (previous)
        api(`/systems/${previous.system_id}`, { method: "DELETE" }).catch(
          () => {},
        );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  async function changeController(value) {
    setController(value);
    setResult(null);
    setError("");
    setSchema({});
    setGains({});
    if (!system) return;
    setBusy("Loading gains…");
    try {
      const next = await api(
        `/systems/${system.system_id}/schema?controller_type=${value}`,
      );
      setSchema(next);
      setGains(defaultGains(next));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  async function run(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setBusy("Simulating…");
    try {
      if (
        Object.values(config).some(
          (v) => v === "" || !Number.isFinite(Number(v)),
        )
      )
        throw new Error("Fill in all simulation settings with finite numbers.");
      if (config.min_control >= config.max_control)
        throw new Error("Minimum control must be less than maximum control.");
      let state = null;
      if (fixed) {
        const parts = initial.split(",");
        state = parts.map(Number);
        if (
          parts.some((p) => !p.trim()) ||
          state.length !== system.num_states ||
          state.some((v) => !Number.isFinite(v) || Math.abs(v) > 100)
        )
          throw new Error(
            `Enter ${system.num_states} comma-separated initial state values.`,
          );
      }
      const data = await api(`/systems/${system.system_id}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          controller_type: controller,
          params: gains,
          system_config: config,
          fixed_initial_state: state,
        }),
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  async function removeSystem() {
    setBusy("Removing system…");
    setError("");
    try {
      await api(`/systems/${system.system_id}`, { method: "DELETE" });
      setSystem(null);
      setSelectedFileName("");
      setSchema({});
      setGains({});
      setResult(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }
  function reset() {
    setGains(defaultGains(schema));
    setConfig(defaults);
    setFixed(true);
    setInitial([1, ...Array((system?.num_states || 2) - 1).fill(0)].join(", "));
    setResult(null);
    setError("");
  }
  return (
    <main className="min-h-screen p-4 sm:p-8 text-gray-100 max-w-7xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-blue-400">
          Controller Tuner Platform
        </h1>
        <p className="text-gray-400 mt-2">
          Upload dynamics, tune a controller, and inspect the engine’s response.
        </p>
      </header>
      {error && (
        <div
          role="alert"
          className="mb-5 p-4 border border-red-500 rounded-xl text-red-200 bg-red-950"
        >
          {error}
        </div>
      )}
      <div className="grid lg:grid-cols-3 gap-6">
        <form
          onSubmit={run}
          className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-5"
        >
          <fieldset
            disabled={Boolean(busy)}
            className="space-y-5 disabled:opacity-60"
          >
            <div>
              <label htmlFor="dynamics" className="block mb-2 font-semibold">
                1. Upload dynamics (.py)
              </label>
              <div className="flex items-center gap-3 min-w-0">
                <label
                  htmlFor="dynamics"
                  className="cursor-pointer rounded-lg bg-gray-700 px-3 py-2 text-sm shrink-0 focus-within:ring-2 focus-within:ring-blue-400"
                >
                  Choose file
                  <input
                    id="dynamics"
                    type="file"
                    accept=".py"
                    aria-describedby="selected-file-name"
                    onClick={(e) => {
                      e.currentTarget.value = "";
                    }}
                    onChange={(e) => upload(e.target.files[0])}
                    className="sr-only"
                  />
                </label>
                <span
                  id="selected-file-name"
                  className="text-sm text-gray-300 break-all"
                >
                  {selectedFileName || "No file chosen"}
                </span>
              </div>
            </div>
            {system && (
              <div className="space-y-2">
                <p role="status" className="text-emerald-400">
                  {system.name} · {system.num_states} states
                </p>
                <button
                  type="button"
                  onClick={removeSystem}
                  className="text-sm underline text-gray-400 hover:text-white"
                >
                  Remove system
                </button>
              </div>
            )}
            <div>
              <label htmlFor="controller" className="block mb-2 font-semibold">
                2. Controller
              </label>
              <select
                id="controller"
                value={controller}
                onChange={(e) => changeController(e.target.value)}
                className="field"
              >
                {["P", "PI", "PD", "PID", "FSF"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
            {Object.entries(schema).map(([key, range]) => (
              <div key={key}>
                <label htmlFor={key} className="flex justify-between mb-2">
                  <span>{key}</span>
                  <span className="font-mono text-blue-300">
                    {gains[key]?.toFixed(2)}
                  </span>
                </label>
                <input
                  id={key}
                  type="range"
                  min={range.min}
                  max={range.max}
                  step="0.01"
                  value={gains[key] ?? range.min}
                  onChange={(e) => {
                    setGains({ ...gains, [key]: Number(e.target.value) });
                    setResult(null);
                  }}
                  className="w-full accent-blue-500"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>{range.min}</span>
                  <span>{range.max}</span>
                </div>
              </div>
            ))}
            <details>
              <summary className="cursor-pointer font-semibold">
                Simulation settings
              </summary>
              <div className="space-y-3 mt-3">
                {Object.entries(defaults).map(([key]) => (
                  <label key={key} className="block text-sm">
                    {
                      {
                        dt: "Time step (s)",
                        max_time: "Duration (s)",
                        target: "Target",
                        min_control: "Minimum control",
                        max_control: "Maximum control",
                      }[key]
                    }
                    <input
                      className="field mt-1"
                      type="number"
                      step="any"
                      min={
                        key === "dt" ? 0.001 : key === "max_time" ? 0.1 : -100
                      }
                      max={key === "dt" ? 0.1 : key === "max_time" ? 30 : 100}
                      required
                      value={config[key]}
                      onChange={(e) => {
                        setConfig({
                          ...config,
                          [key]:
                            e.target.value === "" ? "" : Number(e.target.value),
                        });
                        setResult(null);
                      }}
                    />
                  </label>
                ))}
                <label className="block">
                  <input
                    type="checkbox"
                    checked={fixed}
                    onChange={(e) => {
                      setFixed(e.target.checked);
                      setResult(null);
                    }}
                  />{" "}
                  Fixed initial state
                </label>
                {fixed && (
                  <label className="block text-sm">
                    Initial state (comma-separated)
                    <input
                      className="field mt-1"
                      value={initial}
                      onChange={(e) => {
                        setInitial(e.target.value);
                        setResult(null);
                      }}
                    />
                  </label>
                )}
              </div>
            </details>
            <button
              type="submit"
              disabled={!system || !Object.keys(schema).length}
              className="w-full bg-blue-600 hover:bg-blue-500 rounded-xl p-3 font-semibold disabled:opacity-40"
            >
              3. Run Simulation
            </button>
            <button
              type="button"
              onClick={reset}
              className="w-full border border-gray-600 rounded-xl p-2 hover:bg-gray-800"
            >
              Reset to defaults
            </button>
          </fieldset>
          {busy && (
            <p role="status" className="text-blue-300">
              {busy}
            </p>
          )}
        </form>
        <section
          aria-live="polite"
          aria-busy={Boolean(busy)}
          className="lg:col-span-2 space-y-6 min-w-0"
          aria-label="Simulation results"
        >
          {result ? (
            <>
              <Suspense fallback={<p role="status">Loading charts…</p>}>
                <SimulationCharts data={result} />
              </Suspense>
              <MetricsPanel metrics={result.metrics} />
            </>
          ) : (
            <div className="bg-gray-900 border border-dashed border-gray-700 rounded-2xl p-10 text-gray-400">
              Upload a system and run a simulation to see response, control
              input, and metrics.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
