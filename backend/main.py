from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class SimulationRequest(BaseModel):
    controller_type: str
    kp: float
    ki: float
    kd: float
@app.post("/simulate")
def run_simulation(req: SimulationRequest):
    dt = 0.1
    steps = 100
    time_points = [i * dt for i in range(steps)]
    trajectory = []
    control_signals = []
    target = 1.0
    val = 0.0
    integral = 0.0
    prev_error = target - val
    for i in range(steps):
        error = target - val
        integral += error * dt
        derivative = (error - prev_error) / dt if i > 0 else 0.0
        u = req.kp * error + req.ki * integral + req.kd * derivative
        control_signals.append(u)
        val += u * dt * 0.5 + (target - val) * 0.1
        trajectory.append(val)
        prev_error = error
    return {
        "time_points": time_points,
        "trajectory": trajectory,
        "target": target,
        "control_signals": control_signals
    }
