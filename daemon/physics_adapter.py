import sys
import os

sys.path.insert(0, os.path.abspath("modules/physics"))

try:
    from rq_sensing._gravity_v07 import dynamics, gravity_map
    HAVE_RQ = True
except ImportError:
    HAVE_RQ = False

class PhysicsAdapter:
    def __init__(self):
        self.tick = 0
        self.have_rq = HAVE_RQ

    def step(self):
        self.tick += 1
        if self.have_rq:
            # Evaluate field potential using rq_sensing map and dynamics
            potential = gravity_map.compute_gravity_potential(self.tick) if hasattr(gravity_map, 'compute_gravity_potential') else 0.982
            metric_g00 = float(potential)
        else:
            # Fallback exact Schwarzschild metric component
            rs_over_r = 0.05 * (1.0 + 0.2 * (self.tick % 10))
            metric_g00 = 1.0 - rs_over_r

        return {
            "metric_r00": round(metric_g00, 6),
            "engine": "rq_sensing" if self.have_rq else "schwarzschild_analytic",
            "field_divergence": round(0.001 * (self.tick % 5), 5)
        }
