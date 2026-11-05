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
- `DELETE /api/v1/systems/{id}`: remove a stored system.
- `GET /health`: service health.

```sh
backend/venv/bin/python -m unittest discover -s backend/tests -v
cd frontend
npm run build
```

Systems live in process memory (one API worker, maximum 100 uploads), expire after one hour, and are lost on restart. DELETE `/api/v1/systems/{id}` removes a system. Upload validation and each simulation run in fresh child processes with a 10-second timeout and at most two concurrent workers; excess requests return HTTP 503 with Retry-After. Timed-out workers are terminated. Defaults are dt=0.01 s, duration=5 s, target=0, control limits=[-10,10]. The UI uses initial state [1,0,…] for repeatable comparisons; disable fixed initial state to use the engine's random initialization. Stability is the engine's measured classification, not a guarantee for every gain selection. Nonfinite metrics are encoded as JSON null; unreached settling/rise times display “Not reached (∞)”, and other undefined metrics display “Unavailable”. Nonfinite or incomplete trajectories return an error.

Uploads are limited to 256 KiB and screened for imports other than numpy/math and obvious dangerous calls. This is a basic check, **not a Python security sandbox**: run only trusted dynamics locally. A child process and timeout do not prevent filesystem or network access. Arbitrary untrusted public uploads require a dedicated security sandbox. Simulations allow at most 30,000 steps. Docker runs the backend as a non-root user with a 512 MiB memory limit and binds service ports to localhost.

## Code layout

Backend routes are in `backend/main.py`, request/response models in `models.py`, source checks in `validation.py`, bounded process execution in `runner.py`, and expiring storage in `store.py`. The frontend separates API requests, charts, and metrics into components. API requests have a 20-second client timeout and show connection errors without generating fallback data. Uploaded filenames stay visible.

GitHub Actions runs the backend tests and frontend production build on pushes and pull requests.
