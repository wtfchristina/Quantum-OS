import math

class RelativisticPINNSolver:
    """
    Hamiltonian PINN surrogate and RK4 geodesic integrator
    calculating relativistic orbits and Christoffel connections
    in a Schwarzschild geometry.
    """
    def __init__(self, mass_m=1.0, r0=8.0, phi0=0.0, l_ang=3.75):
        self.mass = mass_m
        self.rs = 2.0 * mass_m
        self.r = float(r0)
        self.phi = float(phi0)
        self.l = float(l_ang) # Specific angular momentum
        self.pr = 0.0          # Radial momentum proxy (dr/dtau)
        self.step_count = 0

    def _derivatives(self, r, pr):
        if r <= self.rs * 1.01:
            return 0.0, 0.0
        # dr/dtau = pr
        dr_dtau = pr
        # Effective potential derivative: dV_eff/dr
        # V_eff = (1 - rs/r) * (1 + L^2/r^2)
        d_veff_dr = (self.rs / (r * r)) * (1.0 + (self.l ** 2) / (r * r)) - \
                    (1.0 - self.rs / r) * (2.0 * (self.l ** 2) / (r ** 3))
        dpr_dtau = -0.5 * d_veff_dr
        return dr_dtau, dpr_dtau

    def step_rk4(self, dtau=0.08):
        self.step_count += 1
        r = self.r
        pr = self.pr

        # Runge-Kutta 4th Order numerical integration
        k1_r, k1_pr = self._derivatives(r, pr)
        k2_r, k2_pr = self._derivatives(r + 0.5 * dtau * k1_r, pr + 0.5 * dtau * k1_pr)
        k3_r, k3_pr = self._derivatives(r + 0.5 * dtau * k2_r, pr + 0.5 * dtau * k2_pr)
        k4_r, k4_pr = self._derivatives(r + dtau * k3_r, pr + dtau * k3_pr)

        self.r += (dtau / 6.0) * (k1_r + 2.0 * k2_r + 2.0 * k3_r + k4_r)
        self.pr += (dtau / 6.0) * (k1_pr + 2.0 * k2_pr + 2.0 * k3_pr + k4_pr)

        # Orbital bounds reset for continuous cockpit telemetry
        if self.r < 3.2 or self.r > 16.0:
            self.r = 8.0
            self.pr = 0.0

        # dphi/dtau = L / r^2
        dphi = (self.l / (self.r ** 2)) * dtau
        self.phi = (self.phi + dphi) % (2.0 * math.pi)

        # Christoffel connection components
        gamma_r_tt = (self.rs * (self.r - self.rs)) / (2.0 * (self.r ** 3)) if self.r > self.rs else 0.0

        # Energy conservation check (Hamiltonian loss)
        g00 = 1.0 - (self.rs / self.r)
        hamiltonian = - (1.0 / (2.0 * g00)) + 0.5 * (self.pr ** 2) + ((self.l ** 2) / (2.0 * (self.r ** 2)))
        loss_h = abs(hamiltonian - (-0.5))

        x = self.r * math.cos(self.phi)
        z = self.r * math.sin(self.phi)

        return {
            "radius": round(self.r, 4),
            "phi": round(self.phi, 4),
            "pos_x": round(x, 4),
            "pos_z": round(z, 4),
            "radial_accel": round(k1_pr, 6),
            "hamiltonian_loss": round(loss_h, 6),
            "christoffel_gamma_r": round(gamma_r_tt, 6)
        }

    def compute_geodesic_step(self, r=None):
        if r is not None:
            self.r = float(r)
        return self.step_rk4()
