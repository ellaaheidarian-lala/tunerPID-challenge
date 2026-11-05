# Controller Tuner Platform

Controller tuning app built with FastAPI, React, and Tailwind. Simulations use `src/core` directly. Engine calculations and case studies are unchanged; comments and introductory text have been shortened.

## Run with Docker

```sh
docker compose up --build
```

Open http://localhost:3000. API documentation: http://localhost:8000/docs.
Legacy Compose installations can use `docker-compose up --build`.

Choose `case_studies/BallBeam.py`, select PID, adjust the sliders, and click **Run Simulation**. The page displays the response and target, control input, all engine metrics, and stability. P, PI, PD, and FSF are also supported. Use **Reset to defaults** to restore gains and settings. DCMotor and InvPendulum work through the same upload flow.

## Local development

From the repository root, Python 3.11+:

```sh
python3 -m venv backend/venv
backend/venv/bin/pip install -r backend/requirements-dev.txt
backend/venv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

In a separate terminal:

```sh
cd frontend
npm ci
npm run dev
```

Vite and production Nginx proxy `/api` to the backend. To use a separate API origin in development, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_URL`, e.g. `http://localhost:8000`. Vite environment variables are applied at build time.

## API and checks

- `POST /api/v1/upload`: multipart `file`; returns system ID, name, and state count.
- `GET /api/v1/systems/{id}/schema?controller_type=PID`: engine gain ranges.
- `POST /api/v1/systems/{id}/simulate`: `controller_type`, `params`, optional `system_config` and `fixed_initial_state`.
- `GET /health`: service health.

```sh
backend/venv/bin/python -m unittest discover -s backend/tests -v
cd frontend
npm run build
```

Systems live in process memory (one worker, maximum 100 uploads) and are lost on restart. Each simulation uses a separate configuration copy. Defaults are dt=0.01 s, duration=5 s, target=0, control limits=[-10,10]. The UI uses initial state [1,0,…] for repeatable comparisons; disable fixed initial state to use the engine's random initialization. Stability is the engine's measured classification, not a guarantee for every gain selection. Unreached/infinite metrics are encoded as JSON null and displayed as “Not reached (∞)”. Nonfinite or incomplete trajectories return an error.

Uploads are limited to 256 KiB and screened for imports other than numpy/math and obvious dangerous calls. This is a basic check, **not a Python security sandbox**: run only trusted dynamics locally. Arbitrary untrusted public uploads require isolated execution with resource limits. Simulations allow at most 30,000 steps.
