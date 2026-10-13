from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class IMUConfig:
    accel_noise_std: float = 0.03       # m/s^2 per sample
    bias_rw_std: float = 0.0008         # m/s^2 / sqrt(s)
    initial_bias_std: float = 0.015      # m/s^2


class IMUSimulator:
    def __init__(self, cfg: IMUConfig, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng
        self.bias = rng.normal(0.0, cfg.initial_bias_std, size=2)

    def sample(self, true_accel: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
        self.bias = self.bias + self.rng.normal(0.0, self.cfg.bias_rw_std * np.sqrt(dt), size=2)
        noise = self.rng.normal(0.0, self.cfg.accel_noise_std, size=2)
        meas = true_accel + self.bias + noise
        return meas, self.bias.copy()
