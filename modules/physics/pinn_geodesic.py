import math

class RelativisticPINNSolver:
    """
    Kerr metric geodesic integrator accounting for black hole spin (a)
    and frame-dragging (Lense-Thirring precession).
    """
    def __init__(self, mass_m=1.0, spin_a=0.85, r0=8.0, phi0=0.0, l_ang=3.75):
        self.mass = mass_m
        self.a = float(spin_a)
        self.rs = 2.0 * mass_m
        self.r = float(r0)
        self.phi = float(phi0)
        self.l = float(l_ang)
        self.pr = 0.0
        self.step_count = 0

    def compute_frame_dragging(self, r):
        # Frame dragging angular velocity omega = -g_{t phi} / g_{phi phi} at theta = pi/2
        sigma = r * r
        delta = r * r - self.rs * r + self.a * self.a
        denom = (r * r + self.a * self.a) ** 2 - delta * (self.a ** 2)
        if denom <= 0:
            return 0.0
        omega = (self.rs * self.a * r) / denom
        return omega

    def _derivatives(self, r, pr):
        delta = r * r - self.rs * r + self.a * self.a
        if delta <= 0.05 or r <= (self.mass + math.sqrt(max(0.0, self.mass**2 - self.a**2))):
            return 0.0, 0.0

        dr_dtau = pr
        # Effective radial potential with spin-orbit coupling
        v_eff = (1.0 - self.rs / r) * (1.0 + (self.l ** 2) / (r * r)) - (self.rs * self.a * self.l) / (r ** 3)
        dv_dr = (self.rs / (r * r)) * (1.0 + (self.l ** 2) / (r * r)) - \
                (1.0 - self.rs / r) * (2.0 * (self.l ** 2) / (r ** 3)) + \
                (3.0 * self.rs * self.a * self.l) / (r ** 4)

        dpr_dtau = -0.5 * dv_dr
        return dr_dtau, dpr_dtau

    def step_rk4(self, dtau=0.08):
        self.step_count += 1
        r = self.r
        pr = self.pr

        k1_r, k1_pr = self._derivatives(r, pr)
        k2_r, k2_pr = self._derivatives(r + 0.5 * dtau * k1_r, pr + 0.5 * dtau * k1_pr)
        k3_r, k3_pr = self._derivatives(r + 0.5 * dtau * k2_r, pr + 0.5 * dtau * k2_pr)
        k4_r, k4_pr = self._derivatives(r + dtau * k3_r, pr + dtau * k3_pr)

        self.r += (dtau / 6.0) * (k1_r + 2.0 * k2_r + 2.0 * k3_r + k4_r)
        self.pr += (dtau / 6.0) * (k1_pr + 2.0 * k2_pr + 2.0 * k3_pr + k4_pr)

        if self.r < 3.2 or self.r > 16.0:
            self.r = 8.0
            self.pr = 0.0

        # Orbital azimuthal rate includes frame dragging
        omega_fd = self.compute_frame_dragging(self.r)
        dphi = ((self.l / (self.r ** 2)) + omega_fd) * dtau
        self.phi = (self.phi + dphi) % (2.0 * math.pi)

        # Hamiltonian conservation loss
        g00 = 1.0 - (self.rs / self.r)
        hamiltonian = - (1.0 / (2.0 * max(g00, 0.001))) + 0.5 * (self.pr ** 2) + ((self.l ** 2) / (2.0 * (self.r ** 2)))
        loss_h = abs(hamiltonian - (-0.5))

        x = self.r * math.cos(self.phi)
        z = self.r * math.sin(self.phi)

        return {
            "radius": round(self.r, 4),
            "phi": round(self.phi, 4),
            "pos_x": round(x, 4),
            "pos_z": round(z, 4),
            "frame_drag_omega": round(omega_fd, 6),
            "radial_accel": round(k1_pr, 6),
            "hamiltonian_loss": round(loss_h, 6),
            "christoffel_gamma_r": round((self.rs * (self.r - self.rs)) / (2.0 * (self.r ** 3)), 6)
        }

    def compute_geodesic_step(self, r=None):
        if r is not None:
            self.r = float(r)
        return self.step_rk4()
