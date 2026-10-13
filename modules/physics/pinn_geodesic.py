import math
import time

class RelativisticPINNSolver:
    """
    Lightweight Hamiltonian PINN surrogate calculating Christoffel symbols
    and geodesic path deviations across a Schwarzschild background.
    """
    def __init__(self, mass_m=1.0):
        self.mass = mass_m
        self.step_count = 0

    def compute_geodesic_step(self, r=10.0, theta=math.pi / 2, phi_dot=0.03):
        self.step_count += 1
        rs = 2.0 * self.mass

        # Christoffel connection components: Gamma^r_{phi phi} and Gamma^r_{t t}
        gamma_r_phiphi = -(r - rs) * (math.sin(theta) ** 2)
        gamma_r_tt = (rs * (r - rs)) / (2.0 * (r ** 3)) if r > rs else 0.0

        # Radial acceleration along the geodesic
        radial_accel = -gamma_r_tt + (gamma_r_phiphi * (phi_dot ** 2))

        # Hamiltonian conservation loss: H = 1/2 * g^{mu nu} p_mu p_nu
        g00 = 1.0 - (rs / r) if r > rs else 0.001
        grr = 1.0 / g00
        p_t = -1.0  # Conserved energy proxy
        p_phi = (r ** 2) * phi_dot  # Conserved angular momentum proxy
        hamiltonian = - (p_t ** 2) / (2.0 * g00) + (p_phi ** 2) / (2.0 * (r ** 2))

        # Target Hamiltonian for massive particle is -0.5 (c=1 units)
        loss_h = abs(hamiltonian - (-0.5))

        return {
            "radius": round(r, 4),
            "radial_accel": round(radial_accel, 6),
            "hamiltonian_loss": round(loss_h, 6),
            "christoffel_gamma_r": round(gamma_r_tt, 6)
        }
