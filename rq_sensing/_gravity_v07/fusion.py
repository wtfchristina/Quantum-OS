from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import numpy as np


class ScalarField(Protocol):
    def value(self, x: float, y: float): ...
    def gradient(self, x: float, y: float) -> np.ndarray: ...


@dataclass(frozen=True)
class FieldObservation:
    name: str
    field: ScalarField
    value: float
    noise_std: float


class FusionEKF:
    """Planar INS EKF with pluggable scalar environmental observations.

    State: [x, y, vx, vy, bax, bay]
    """
    def __init__(self, x0, P0, accel_noise_std=0.03, bias_rw_std=8e-4):
        self.x = np.asarray(x0, dtype=float).copy()
        self.P = np.asarray(P0, dtype=float).copy()
        self.accel_noise_std = float(accel_noise_std)
        self.bias_rw_std = float(bias_rw_std)
        self.last_innovations: dict[str, float] = {}

    def predict(self, imu_accel: np.ndarray, dt: float):
        x, y, vx, vy, bax, bay = self.x
        ax, ay = imu_accel[0]-bax, imu_accel[1]-bay
        self.x = np.array([x+vx*dt+0.5*ax*dt*dt, y+vy*dt+0.5*ay*dt*dt,
                           vx+ax*dt, vy+ay*dt, bax, bay], dtype=float)
        F = np.eye(6)
        F[0,2]=dt; F[1,3]=dt
        F[0,4]=-0.5*dt*dt; F[1,5]=-0.5*dt*dt
        F[2,4]=-dt; F[3,5]=-dt
        G = np.zeros((6,4))
        G[0,0]=0.5*dt*dt; G[1,1]=0.5*dt*dt
        G[2,0]=dt; G[3,1]=dt
        G[4,2]=np.sqrt(dt); G[5,3]=np.sqrt(dt)
        q = np.diag([self.accel_noise_std**2, self.accel_noise_std**2,
                     self.bias_rw_std**2, self.bias_rw_std**2])
        self.P = F @ self.P @ F.T + G @ q @ G.T

    def update(self, obs: FieldObservation, innovation_gate_sigma: float | None = 5.0) -> bool:
        px, py = float(self.x[0]), float(self.x[1])
        h = float(obs.field.value(px, py))
        grad = np.asarray(obs.field.gradient(px, py), dtype=float)
        H = np.zeros((1,6)); H[0,0:2] = grad
        R = np.array([[float(obs.noise_std)**2]])
        innovation = float(obs.value - h)
        S = float((H @ self.P @ H.T + R)[0,0])
        if innovation_gate_sigma is not None and abs(innovation) > innovation_gate_sigma*np.sqrt(max(S,1e-18)):
            self.last_innovations[obs.name] = innovation
            return False
        K = self.P @ H.T / S
        self.x = self.x + K[:,0]*innovation
        I = np.eye(6)
        KH = K @ H
        self.P = (I-KH) @ self.P @ (I-KH).T + K @ R @ K.T
        self.last_innovations[obs.name] = innovation
        return True
