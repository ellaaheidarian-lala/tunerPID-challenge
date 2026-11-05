import logging
import math
import multiprocessing
from pathlib import Path
from threading import BoundedSemaphore
import tempfile

from fastapi import HTTPException
from src.core.dynamics import DynamicalSystem
from src.core.simulator import Simulator
from backend.models import SimulationRequest

logger = logging.getLogger(__name__)
_slots = BoundedSemaphore(2)
TIMEOUT_SECONDS = 10


def evaluate(system, request):
    for key, value in request.system_config.model_dump().items():
        setattr(system, key, value)
    result = Simulator(system).evaluate(request.controller_type, request.params, fixed_initial_state=request.fixed_initial_state)
    expected = int(system.max_time / system.dt) + 1
    if len(result['trajectory']) != expected or len(result['control_signals']) != expected:
        raise ValueError('Dynamics stopped before completing the simulation.')
    if any(not math.isfinite(v) for key in ['trajectory', 'control_signals'] for v in result[key]):
        raise ValueError('Simulation diverged. Try different gains or a smaller time step.')
    # Avoid an extra timestamp from floating-point rounding in arange.
    result['time_points'] = [i * system.dt for i in range(expected)]
    # Encode infinite metrics as JSON null.
    result['metrics'] = {k: (v if not isinstance(v, float) or math.isfinite(v) else None) for k, v in result['metrics'].items()}
    result['target'] = system.target
    return result


def _worker(connection, source, payload):
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dynamics.py'
            path.write_bytes(source)
            system = DynamicalSystem(str(path))
            if payload is None:
                result = {
                    'num_states': system.num_states,
                    'schemas': {c: system.get_param_schema(c) for c in ['P', 'PI', 'PD', 'PID', 'FSF']},
                }
            else:
                result = evaluate(system, SimulationRequest(**payload))
            connection.send(('ok', result))
    except Exception:
        logger.exception('Dynamics execution failed')
        connection.send(('error', None))
    finally:
        connection.close()


def execute(source, payload=None, timeout=None):
    if not _slots.acquire(blocking=False):
        raise HTTPException(503, 'Simulation workers are busy. Please try again shortly.', headers={'Retry-After': '2'})
    context = multiprocessing.get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(sender, source, payload), daemon=True)
    started = False
    try:
        process.start()
        started = True
        sender.close()
        if not receiver.poll(TIMEOUT_SECONDS if timeout is None else timeout):
            raise HTTPException(408, 'Dynamics execution timed out. Check the dynamics code or reduce the simulation duration.')
        try:
            status, result = receiver.recv()
        except EOFError as exc:
            raise HTTPException(422, 'Dynamics process stopped unexpectedly.') from exc
        if status != 'ok':
            raise HTTPException(400 if payload is None else 422, 'Could not load dynamics.' if payload is None else 'Simulation failed. Check dynamics, gains, and time step.')
        return result
    finally:
        receiver.close()
        sender.close()
        if started:
            process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
        _slots.release()
