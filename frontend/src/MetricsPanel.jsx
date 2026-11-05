export default function MetricsPanel({ metrics }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
      <h2 className="text-xl mb-4">
        Performance metrics{" "}
        <span
          className={`text-sm ml-2 ${metrics.stable ? "text-emerald-400" : "text-amber-400"}`}
        >
          {metrics.stable ? "Stable" : "Unstable"}
        </span>
      </h2>
      <dl className="grid grid-cols-2 sm:grid-cols-3 gap-5">
        {Object.entries(metrics)
          .filter(([key]) => key !== "stable")
          .map(([key, value]) => (
            <div key={key}>
              <dt className="text-gray-400 text-sm">
                {{
                  mse: "MSE",
                  rmse: "RMSE",
                  settling_time: "Settling time (s)",
                  rise_time: "Rise time (s)",
                  overshoot: "Overshoot (%)",
                  ss_error: "Steady-state error",
                  control_effort: "Control effort",
                  zero_crossings: "Zero crossings",
                }[key] || key}
              </dt>
              <dd className="text-lg font-mono">
                {value === null
                  ? ["settling_time", "rise_time"].includes(key)
                    ? "Not reached (∞)"
                    : "Unavailable"
                  : Number.isInteger(value)
                    ? value
                    : value.toPrecision(5)}
              </dd>
            </div>
          ))}
      </dl>
    </div>
  );
}
