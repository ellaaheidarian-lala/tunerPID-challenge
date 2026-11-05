import json
from pathlib import Path
import unittest

import numpy as np
from fastapi.testclient import TestClient

from backend.main import app, systems
from src.core.dynamics import DynamicalSystem
from src.core.simulator import Simulator

ROOT = Path(__file__).resolve().parents[2]


class ApiTests(unittest.TestCase):
    def setUp(self):
        systems.clear()
        self.client = TestClient(app)

    def upload(self, name='BallBeam'):
        response = self.client.post('/api/v1/upload', files={'file': (name + '.py', (ROOT / 'case_studies' / (name + '.py')).read_bytes())})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()['num_states'], 2)
        return response.json()['system_id']

    def test_all_examples_and_controllers_match_engine(self):
        for name in ['BallBeam', 'DCMotor', 'InvPendulum']:
            system_id = self.upload(name)
            direct = DynamicalSystem(str(ROOT / 'case_studies' / (name + '.py')))
            for controller in ['P', 'PI', 'PD', 'PID', 'FSF']:
                with self.subTest(system=name, controller=controller):
                    response = self.client.get(f'/api/v1/systems/{system_id}/schema', params={'controller_type': controller})
                    self.assertEqual(response.status_code, 200)
                    schema = response.json()
                    self.assertEqual(schema, direct.get_param_schema(controller))
                    gains = {k: {'Kp': 1, 'Ki': .1, 'Kd': .5}.get(k, 1) for k in schema}
                    response = self.client.post(f'/api/v1/systems/{system_id}/simulate', json={'controller_type': controller, 'params': gains, 'fixed_initial_state': [1, 0]})
                    self.assertEqual(response.status_code, 200, response.text)
                    actual = response.json()
                    expected = Simulator(direct).evaluate(controller, gains, [1, 0])
                    np.testing.assert_allclose(actual['trajectory'], expected['trajectory'])
                    np.testing.assert_allclose(actual['control_signals'], expected['control_signals'])
                    for key, value in expected['metrics'].items():
                        self.assertEqual(actual['metrics'][key], None if isinstance(value, float) and not np.isfinite(value) else value)
                    self.assertEqual(len(actual['time_points']), len(actual['trajectory']))
                    self.assertEqual(len(actual['control_signals']), 501)
                    json.dumps(actual, allow_nan=False)

    def test_validation_and_missing_system(self):
        self.assertEqual(self.client.get('/api/v1/systems/missing/schema').status_code, 404)
        system_id = self.upload()
        endpoint = f'/api/v1/systems/{system_id}/simulate'
        valid = {'controller_type': 'PID', 'params': {'Kp': 1, 'Ki': .1, 'Kd': .5}}
        for patch in [{'controller_type': 'INVALID'}, {'params': {'Kp': 1}}, {'params': {'Kp': 100, 'Ki': .1, 'Kd': .5}}, {'fixed_initial_state': [1]}, {'system_config': {'dt': 0}}, {'system_config': {'min_control': 10, 'max_control': -10}}, {'system_config': {'dt': .001, 'max_time': 30}}]:
            self.assertEqual(self.client.post(endpoint, json={**valid, **patch}).status_code, 422)
        self.assertEqual(self.client.post(endpoint, json=valid).status_code, 200)

    def test_upload_screening(self):
        for name, source in [('file.txt', b'def dynamics(t,x,u): return x'), ('file.py', b'import os\ndef dynamics(t,x,u): return x'), ('file.py', b'not python !!!'), ('file.py', b'x = 1')]:
            self.assertEqual(self.client.post('/api/v1/upload', files={'file': (name, source)}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/upload', files={'file': ('big.py', b'x' * (256 * 1024 + 1))}).status_code, 413)

    def test_configuration_does_not_leak(self):
        system_id = self.upload()
        endpoint = f'/api/v1/systems/{system_id}/simulate'
        payload = {'controller_type': 'P', 'params': {'Kp': 1}, 'fixed_initial_state': [1, 0]}
        first = self.client.post(endpoint, json=payload).json()
        changed = self.client.post(endpoint, json={**payload, 'system_config': {'target': 2, 'max_time': 1}}).json()
        again = self.client.post(endpoint, json=payload).json()
        self.assertEqual(first, again)
        self.assertEqual(changed['target'], 2)
        self.assertEqual(len(changed['trajectory']), 101)

    def test_failed_dynamics_returns_error(self):
        source = b'import numpy as np\ndef dynamics(t,x,u):\n if t > .02: raise ValueError("broken")\n return np.array([x[1],u])\n'
        response = self.client.post('/api/v1/upload', files={'file': ('broken.py', source)})
        self.assertEqual(response.status_code, 201)
        response = self.client.post('/api/v1/systems/' + response.json()['system_id'] + '/simulate', json={'controller_type': 'P', 'params': {'Kp': 1}})
        self.assertEqual(response.status_code, 422)

    def test_delete_system(self):
        system_id = self.upload()
        endpoint = f'/api/v1/systems/{system_id}'
        self.assertEqual(self.client.delete(endpoint).status_code, 204)
        self.assertEqual(self.client.get(endpoint + '/schema').status_code, 404)
        self.assertEqual(self.client.delete(endpoint).status_code, 404)

    def test_timeout_releases_worker(self):
        from backend.runner import execute
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as error:
            execute(b'while True: pass', timeout=0.3)
        self.assertEqual(error.exception.status_code, 408)
        self.upload()

    def test_nonfinite_trajectory_is_rejected(self):
        source = b'import numpy as np\ndef dynamics(t,x,u):\n return np.array([float("nan"),0.0])\n'
        response = self.client.post('/api/v1/upload', files={'file': ('nan.py', source)})
        self.assertEqual(response.status_code, 201)
        endpoint = '/api/v1/systems/' + response.json()['system_id'] + '/simulate'
        self.assertEqual(self.client.post(endpoint, json={'params': {'Kp': 1, 'Ki': .1, 'Kd': .5}}).status_code, 422)

    def test_busy_workers_return_retry_after(self):
        from backend.runner import _slots
        system_id = self.upload()
        _slots.acquire()
        _slots.acquire()
        try:
            response = self.client.post(f'/api/v1/systems/{system_id}/simulate', json={'controller_type': 'P', 'params': {'Kp': 1}})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers['retry-after'], '2')
        finally:
            _slots.release()
            _slots.release()


class StoreTests(unittest.TestCase):
    def test_capacity_expiration_and_deletion(self):
        from unittest.mock import patch
        from fastapi import HTTPException
        from backend.store import SystemStore
        store = SystemStore(capacity=1, ttl=10)
        with patch('backend.store.monotonic', return_value=100):
            key = store.add(b'source', 'example', 2, {})
            self.assertEqual(store.get(key).name, 'example')
            with self.assertRaises(HTTPException) as error:
                store.add(b'other', 'example', 2, {})
            self.assertEqual(error.exception.status_code, 503)
        with patch('backend.store.monotonic', return_value=111):
            with self.assertRaises(HTTPException) as error:
                store.get(key)
            self.assertEqual(error.exception.status_code, 404)
            next_key = store.add(b'new', 'example', 2, {})
            store.delete(next_key)
            with self.assertRaises(HTTPException):
                store.get(next_key)
