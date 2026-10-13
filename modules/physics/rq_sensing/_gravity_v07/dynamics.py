from __future__ import annotations

import numpy as np


def propagate_truth(state: np.ndarray, accel_cmd: np.ndarray, dt: float) -> np.ndarray:
    """Simple planar truth model [x, y, vx, vy]."""
    x, y, vx, vy = state
    ax, ay = accel_cmd
    return np.array([
        x + vx * dt + 0.5 * ax * dt * dt,
        y + vy * dt + 0.5 * ay * dt * dt,
        vx + ax * dt,
        vy + ay * dt,
    ], dtype=float)


def nominal_acceleration(t: float) -> np.ndarray:
    """Smooth lateral maneuvers that keep the route informative."""
    ax = 0.08 * np.sin(2.0 * np.pi * t / 180.0)
    ay = 0.16 * np.sin(2.0 * np.pi * t / 120.0) + 0.05 * np.sin(2.0 * np.pi * t / 47.0)
    return np.array([ax, ay], dtype=float)
