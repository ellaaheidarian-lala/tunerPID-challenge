from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Controller = Literal['P', 'PI', 'PD', 'PID', 'FSF']
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
        if int(self.max_time / self.dt) + 1 > 30000:
            raise ValueError('At most 30000 simulation points are allowed')
        return self


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    controller_type: Controller = 'PID'
    params: dict[str, float]
    system_config: SystemConfig = Field(default_factory=SystemConfig)
    fixed_initial_state: list[float] | None = None


class UploadResponse(BaseModel):
    system_id: str
    name: str
    num_states: int


class GainRange(BaseModel):
    min: float
    max: float


class Metrics(BaseModel):
    mse: float | None
    rmse: float | None
    settling_time: float | None
    overshoot: float | None
    stable: bool
    ss_error: float | None
    control_effort: float | None
    rise_time: float | None
    zero_crossings: int


class SimulationResponse(BaseModel):
    success: bool
    time_points: list[float]
    trajectory: list[float]
    control_signals: list[float]
    metrics: Metrics
    target: float
