from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from backend.runner import execute


class RunnerTests(unittest.TestCase):
    def test_simulation_timeout_and_recovery(self):
        source = b'import numpy as np\ndef dynamics(t,x,u):\n if t > .02:\n  while True: pass\n return np.array([x[1],u])\n'
        payload = {'controller_type': 'P', 'params': {'Kp': 1}}
        with patch('backend.runner.TIMEOUT_SECONDS', 1):
            with self.assertRaises(HTTPException) as error:
                execute(source, payload)
        self.assertEqual(error.exception.status_code, 408)
        valid = Path('case_studies/BallBeam.py').read_bytes()
        self.assertEqual(execute(valid)['num_states'], 2)
