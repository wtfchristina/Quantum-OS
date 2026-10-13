from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class GaussianAnomaly:
    x: float
    y: float
    amplitude: float
    sigma_x: float
    sigma_y: float


class SyntheticGravityMap:
    """Smooth synthetic gravity-gradient reference field.

    The scalar observable is a weighted sum of 2D Gaussian anomalies. This is
    intentionally simplified: it provides a differentiable spatial field for
    testing map matching and observability without implying flight-grade
    geophysics.
    """

    def __init__(self, anomalies: list[GaussianAnomaly] | None = None):
        if anomalies is None:
            anomalies = [
                GaussianAnomaly(8_000, 3_000, 85.0, 4_500, 3_500),
                GaussianAnomaly(22_000, -4_000, -70.0, 5_500, 4_000),
                GaussianAnomaly(35_000, 5_000, 95.0, 6_000, 5_000),
                GaussianAnomaly(47_000, -2_000, -55.0, 4_500, 3_000),
                GaussianAnomaly(29_000, 11_000, 45.0, 7_000, 4_500),
            ]
        self.anomalies = anomalies

    def value(self, x: np.ndarray | float, y: np.ndarray | float) -> np.ndarray:
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        out = np.zeros(np.broadcast(x_arr, y_arr).shape, dtype=float)
        for a in self.anomalies:
            dx = (x_arr - a.x) / a.sigma_x
            dy = (y_arr - a.y) / a.sigma_y
            out = out + a.amplitude * np.exp(-0.5 * (dx * dx + dy * dy))
        return out

    def gradient(self, x: float, y: float) -> np.ndarray:
        gx = 0.0
        gy = 0.0
        for a in self.anomalies:
            dx = x - a.x
            dy = y - a.y
            e = np.exp(-0.5 * ((dx / a.sigma_x) ** 2 + (dy / a.sigma_y) ** 2))
            term = a.amplitude * e
            gx += term * (-dx / (a.sigma_x**2))
            gy += term * (-dy / (a.sigma_y**2))
        return np.array([gx, gy], dtype=float)

    def grid(self, xlim=(0.0, 55_000.0), ylim=(-15_000.0, 15_000.0), nx=240, ny=140):
        xs = np.linspace(*xlim, nx)
        ys = np.linspace(*ylim, ny)
        xx, yy = np.meshgrid(xs, ys)
        zz = self.value(xx, yy)
        return xx, yy, zz
