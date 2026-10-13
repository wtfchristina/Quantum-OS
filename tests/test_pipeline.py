import unittest
import numpy as np
from rq_sensing import SensorConfig,Spectrum,SimulatedNVSensor,estimate_field,resonances
from rq_sensing.core import GAMMA_MHZ_PER_UT,lineshape
class PipelineTests(unittest.TestCase):
    def test_analytic_and_sign_ambiguity(self):
        lo,hi=resonances(80,strain_mhz=0)
        self.assertAlmostEqual((hi-lo)/2,GAMMA_MHZ_PER_UT*80)
        self.assertEqual(resonances(80),resonances(-80))
    def test_noiseless_strain_and_temperature(self):
        f=np.linspace(2863,2877,401); lo,hi=resonances(55,298,.3)
        y=lineshape(f,(lo+hi)/2,(hi-lo)/2,.35,.06,.08,1e5,.02)
        fit=estimate_field(Spectrum(f,y,.05),.3)
        self.assertTrue(fit.accepted,fit.flags)
        self.assertAlmostEqual(fit.axial_magnitude_ut,55,places=5)
        self.assertAlmostEqual(fit.temperature_proxy_k,298,places=5)
    def test_noisy_temperature_drift(self):
        sensor=SimulatedNVSensor(seed=42)
        for b,t in [(35,281),(60,293.15),(110,310),(80,329)]:
            fit=estimate_field(sensor.acquire(b,t))
            self.assertTrue(fit.accepted,fit.flags)
            self.assertLess(abs(fit.axial_magnitude_ut-b),1)
            self.assertGreater(fit.field_std_ut,0)
    def test_reproducibility(self):
        np.testing.assert_array_equal(SimulatedNVSensor(seed=9).acquire(60).counts,SimulatedNVSensor(seed=9).acquire(60).counts)
    def test_flat_rejected(self):
        fit=estimate_field(Spectrum(np.linspace(2863,2877,401),np.full(401,1e5),.05))
        self.assertFalse(fit.accepted); self.assertIsNone(fit.axial_magnitude_ut)
    def test_unresolved_rejected(self):
        fit=estimate_field(SimulatedNVSensor(SensorConfig(strain_mhz=0),seed=2).acquire(0),0)
        self.assertFalse(fit.accepted); self.assertIsNone(fit.axial_magnitude_ut)
    def test_mismatch_rejected(self):
        scan=SimulatedNVSensor(seed=4).acquire(65); scan.counts[100:150]*=.8
        fit=estimate_field(scan); self.assertFalse(fit.accepted); self.assertIn('model_mismatch',fit.flags)
    def test_bad_inputs(self):
        for y in [np.full(50,-1),np.full(50,np.nan)]:
            with self.assertRaises(ValueError): Spectrum(np.arange(50),y,.1)
        with self.assertRaises(ValueError): Spectrum(np.arange(50)[::-1],np.ones(50),.1)
        with self.assertRaises(ValueError): SensorConfig(dwell_s=0)
        with self.assertRaises(ValueError): SimulatedNVSensor().acquire(500)
        with self.assertRaises(ValueError): resonances(20,350)
        with self.assertRaises(ValueError): estimate_field(SimulatedNVSensor().acquire(60),-1)
if __name__=='__main__': unittest.main()
