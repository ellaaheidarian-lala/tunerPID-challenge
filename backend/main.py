from contextlib import asynccontextmanager
import logging
import math
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.models import Controller, GainRange, SimulationRequest, SimulationResponse, UploadResponse
from backend.runner import execute
from backend.store import SystemStore
from backend.validation import check_source

logger = logging.getLogger(__name__)
systems = SystemStore()


@asynccontextmanager
async def lifespan(app):
    yield
    systems.clear()


app = FastAPI(title='Controller Tuner API', version='1.1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'http://localhost:5173', 'http://127.0.0.1:3000', 'http://127.0.0.1:5173'],
    allow_methods=['GET', 'POST', 'DELETE'],
    allow_headers=['Content-Type'],
)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/api/v1/upload', status_code=201, response_model=UploadResponse)
def upload(file: UploadFile = File(...)):
    try:
        if not file.filename or Path(file.filename).suffix.lower() != '.py':
            raise HTTPException(400, 'Please upload a .py dynamics file.')
        source = file.file.read(256 * 1024 + 1)
        if len(source) > 256 * 1024:
            raise HTTPException(413, 'Dynamics files must be no larger than 256 KiB.')
        check_source(source)
        metadata = execute(source)
        name = Path(file.filename.replace('\\', '/')).stem[:100]
        key = systems.add(source, name, metadata['num_states'], metadata['schemas'])
        logger.info('System uploaded: %s (%s states)', key, metadata['num_states'])
        return {'system_id': key, 'name': name, 'num_states': metadata['num_states']}
    finally:
        file.file.close()


@app.get('/api/v1/systems/{system_id}/schema', response_model=dict[str, GainRange])
def schema(system_id: str, controller_type: Controller = 'PID'):
    return systems.get(system_id).schemas[controller_type]


@app.delete('/api/v1/systems/{system_id}', status_code=204)
def delete_system(system_id: str):
    systems.delete(system_id)
    return Response(status_code=204)


@app.post('/api/v1/systems/{system_id}/simulate', response_model=SimulationResponse)
def simulate(system_id: str, request: SimulationRequest):
    system = systems.get(system_id)
    ranges = system.schemas[request.controller_type]
    if set(request.params) != set(ranges):
        raise HTTPException(422, f'Expected gains: {", ".join(ranges)}')
    for key, value in request.params.items():
        if not math.isfinite(value) or not ranges[key]['min'] <= value <= ranges[key]['max']:
            raise HTTPException(422, f'{key} must be between {ranges[key]["min"]} and {ranges[key]["max"]}')
    initial = request.fixed_initial_state
    if initial is not None and (len(initial) != system.num_states or any(not math.isfinite(v) or abs(v) > 100 for v in initial)):
        raise HTTPException(422, f'Initial state must contain {system.num_states} finite values between -100 and 100.')
    return execute(system.source, request.model_dump())
