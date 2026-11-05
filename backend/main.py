"""Thin HTTP adapter for the supplied simulation engine."""
import ast
from contextlib import asynccontextmanager
from copy import copy
import math
from pathlib import Path
import tempfile
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.dynamics import DynamicalSystem
from src.core.simulator import Simulator

Controller = Literal['P', 'PI', 'PD', 'PID', 'FSF']
systems: dict[str, DynamicalSystem] = {}


@asynccontextmanager
async def lifespan(app):
    yield
    systems.clear()


app = FastAPI(title='Controller Tuner API', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:3000', 'http://127.0.0.1:5173'], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


class SystemConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    dt: float = Field(default=0.01, ge=0.001, le=0.1)
    max_time: float = Field(default=5.0, ge=0.1, le=30)
    target: float = Field(default=0.0, ge=-100, le=100)
    min_control: float = Field(default=-10, ge=-100, le=100)
    max_control: float = Field(default=10, ge=-100, le=100)

    @model_validator(mode='after')
    def check_limits(self):
        if self.min_control >= self.max_control:
            raise ValueError('min_control must be less than max_control')
        if self.max_time / self.dt > 30000:
            raise ValueError('At most 30000 simulation steps are allowed')
        return self


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    controller_type: Controller = 'PID'
    params: dict[str, float]
    system_config: SystemConfig = Field(default_factory=SystemConfig)
    fixed_initial_state: list[float] | None = None


def get_system(system_id):
    if system_id not in systems:
        raise HTTPException(404, 'System not found. Please upload the dynamics file again.')
    return systems[system_id]


def check_source(source: bytes):
    """Basic screening only: uploaded Python is trusted code, not sandboxed."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, UnicodeError) as exc:
        raise HTTPException(400, 'File must contain valid Python source.') from exc
    blocked_calls = {'eval', 'exec', 'compile', 'open', '__import__', 'input', 'breakpoint', 'getattr', 'setattr', 'delattr', 'globals', 'locals', 'vars'}
    for node in ast.walk(tree):
        imports = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else ([node.module.split('.')[0]] if isinstance(node, ast.ImportFrom) and node.module else [])
        if any(name not in {'numpy', 'math'} for name in imports) or (isinstance(node, ast.ImportFrom) and node.level):
            raise HTTPException(400, 'Only numpy and math imports are supported.')
        if isinstance(node, ast.Attribute) and node.attr.startswith('_'):
            raise HTTPException(400, 'Private and special attribute access is not supported.')
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in blocked_calls:
            raise HTTPException(400, f'Unsupported call: {node.func.id}')
    if not any(isinstance(n, ast.FunctionDef) and n.name == 'dynamics' for n in tree.body):
        raise HTTPException(400, 'Define a top-level dynamics(t, x, u) function.')


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/api/v1/upload', status_code=201)
def upload(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() != '.py':
        raise HTTPException(400, 'Please upload a .py dynamics file.')
    source = file.file.read(256 * 1024 + 1)
    if len(source) > 256 * 1024:
        raise HTTPException(413, 'Dynamics files must be no larger than 256 KiB.')
    check_source(source)
    if len(systems) >= 100:
        raise HTTPException(503, 'Upload capacity reached. Restart the service to clear stored systems.')
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dynamics.py'
            path.write_bytes(source)
            system = DynamicalSystem(str(path))
    except Exception as exc:
        raise HTTPException(400, f'Could not initialize dynamics: {exc}') from exc
    system.name = Path(file.filename).stem
    system_id = str(uuid4())
    systems[system_id] = system
    return {'system_id': system_id, 'name': system.name, 'num_states': system.num_states}


@app.get('/api/v1/systems/{system_id}/schema')
def schema(system_id: str, controller_type: Controller = 'PID'):
    return get_system(system_id).get_param_schema(controller_type)


@app.post('/api/v1/systems/{system_id}/simulate')
def simulate(system_id: str, request: SimulationRequest):
    system = copy(get_system(system_id))
    ranges = system.get_param_schema(request.controller_type)
    if set(request.params) != set(ranges):
        raise HTTPException(422, f'Expected gains: {", ".join(ranges)}')
    for key, value in request.params.items():
        if not math.isfinite(value) or not ranges[key]['min'] <= value <= ranges[key]['max']:
            raise HTTPException(422, f'{key} must be between {ranges[key]["min"]} and {ranges[key]["max"]}')
    initial = request.fixed_initial_state
    if initial is not None and (len(initial) != system.num_states or any(not math.isfinite(v) or abs(v) > 100 for v in initial)):
        raise HTTPException(422, f'Initial state must contain {system.num_states} finite values between -100 and 100.')
    for key, value in request.system_config.model_dump().items():
        setattr(system, key, value)
    try:
        result = Simulator(system).evaluate(request.controller_type, request.params, fixed_initial_state=initial)
        expected = int(system.max_time / system.dt) + 1
        if len(result['trajectory']) != expected or len(result['control_signals']) != expected:
            raise ValueError('Dynamics stopped before completing the simulation.')
        if any(not math.isfinite(v) for key in ['trajectory', 'control_signals'] for v in result[key]):
            raise ValueError('Simulation diverged. Try different gains or a smaller time step.')
        # The engine may produce one extra time value due to floating-point arange.
        result['time_points'] = [i * system.dt for i in range(expected)]
        # Unreached settling/rise times are infinity in the engine; JSON uses null.
        result['metrics'] = {k: (v if not isinstance(v, float) or math.isfinite(v) else None) for k, v in result['metrics'].items()}
        result['target'] = system.target
        return result
    except Exception as exc:
        raise HTTPException(422, f'Simulation failed: {exc}') from exc
