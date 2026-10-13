import unittest
from types import SimpleNamespace
import tempfile
from pathlib import Path
import numpy as np
from rq_sensing.navigation import MagneticMap,MatcherConfig,ParticleMapMatcher

def measurement(value,std=.1,accepted=True):
    return SimpleNamespace(accepted=accepted,axial_magnitude_ut=value,field_std_ut=std)

def ramp(flat=False):
    x=np.linspace(0,500,101); y=np.linspace(0,500,101); xx,yy=np.meshgrid(x,y)
    return MagneticMap(x,y,np.full_like(xx,60.) if flat else 40+.2*xx)

class NavigationTests(unittest.TestCase):
    def test_interpolation_and_roundtrip(self):
        m=ramp(); np.testing.assert_allclose(m.sample([[101,208],[202,111]]),[60.2,80.4])
        self.assertTrue(np.isnan(m.sample([[501,200]])[0]))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'map.npz'; m.save(p); n=MagneticMap.load(p)
            np.testing.assert_array_equal(n.axial_magnitude_ut,m.axial_magnitude_ut)
    def test_flat_map_does_not_update(self):
        p=ParticleMapMatcher(ramp(True),[200,200],seed=2)
        r=p.step([0,0],measurement(60))
        self.assertFalse(r.measurement_used); self.assertIn('uninformative_map',r.flags)
        np.testing.assert_allclose(p.weights,1/len(p.weights))
    def test_rejected_and_missing_sensor(self):
        p=ParticleMapMatcher(ramp(),[200,200],seed=3)
        for f in [None,measurement(80,accepted=False)]:
            r=p.step([2,0],f); self.assertFalse(r.measurement_used)
            self.assertIn('sensor_unavailable',r.flags)
    def test_extreme_outlier_rejected(self):
        p=ParticleMapMatcher(ramp(),[200,200],seed=4)
        r=p.step([0,0],measurement(500)); self.assertFalse(r.measurement_used)
        self.assertIn('magnetic_outlier',r.flags)
    def test_outside_map_no_clamp_or_reset(self):
        p=ParticleMapMatcher(ramp(),[200,200],seed=4)
        r=p.step([2000,0],measurement(80)); self.assertFalse(r.measurement_used)
        self.assertIn('insufficient_map_support',r.flags); self.assertGreater(r.position_m[0],2000)
    def test_constrained_axis_improves_unconstrained_axis_remains(self):
        p=ParticleMapMatcher(ramp(),[220,200],seed=5)
        r=p.step([0,0],measurement(80))
        self.assertTrue(r.measurement_used)
        self.assertLess(abs(r.position_m[0]-200),3)
        self.assertGreater(r.covariance_m2[1][1],100)
    def test_seeded_reproducibility(self):
        a=ParticleMapMatcher(ramp(),[200,200],seed=6); b=ParticleMapMatcher(ramp(),[200,200],seed=6)
        for _ in range(3):
            ra=a.step([2,0],measurement(80)); rb=b.step([2,0],measurement(80))
            self.assertEqual(ra.to_dict(),rb.to_dict())
    def test_validation(self):
        with self.assertRaises(ValueError): MagneticMap([0,0],[0,1],np.ones((2,2)))
        with self.assertRaises(ValueError): MatcherConfig(particles=0)
        with self.assertRaises(ValueError): MatcherConfig(map_std_ut=0)
        p=ParticleMapMatcher(ramp(),[200,200])
        with self.assertRaises(ValueError): p.step([np.nan,0])
        r=p.step([0,0],measurement(80,std=np.nan)); self.assertFalse(r.measurement_used)
        self.assertIn('invalid_field_estimate',r.flags)
if __name__=='__main__': unittest.main()
