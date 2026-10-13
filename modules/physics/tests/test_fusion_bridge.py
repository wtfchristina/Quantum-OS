import unittest,json,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from rq_sensing.fusion_bridge import QuantumGravityFusion,AxialMapNT,nv_packet
from rq_sensing.navigation import MagneticMap
from rq_sensing._gravity_v07.fusion import FusionEKF,FieldObservation
from rq_sensing._gravity_v07.packets import SensorPacket
from rq_sensing.integrated_simulation import IntegratedConfig

class LinearGravity:
    def value(self,x,y):return .3*x+.2*y
    def gradient(self,x,y):return np.array([.3,.2])

def field_est(value=60,t=1.,std=.2,accepted=True):
    return SimpleNamespace(accepted=accepted,axial_magnitude_ut=value,field_std_ut=std,timestamp_s=t)

def map_fixture():
    x=np.linspace(0,500,101);y=x.copy();xx,yy=np.meshgrid(x,y)
    return MagneticMap(x,y,50+.05*xx+.02*yy)

def engine():return QuantumGravityFusion([200,200,0,0,0,0],np.diag([100,100,1,1,.001,.001]),map_fixture(),LinearGravity())

class FusionBridgeTests(unittest.TestCase):
    def test_nt_conversion_packet_roundtrip(self):
        p=nv_packet(field_est(64,21.),4)
        self.assertEqual(p.values['axial_magnitude_nt'],64000)
        self.assertEqual(p.values['field_std_nt'],200)
        self.assertEqual(SensorPacket.from_json(p.to_json()).to_dict(),p.to_dict())
        self.assertIsNone(nv_packet(field_est(accepted=False),0))
    def test_map_value_and_gradient_unit_conversion(self):
        m=AxialMapNT(map_fixture())
        self.assertAlmostEqual(m.value(200,200),64000)
        np.testing.assert_allclose(m.gradient(200,200),[50,20])
    def test_exact_upstream_update_equivalence(self):
        f=engine();f.predict([.01,-.02],1.)
        reference=FusionEKF(f.ekf.x.copy(),f.ekf.P.copy())
        p=nv_packet(field_est(64.1),0)
        used=reference.update(FieldObservation('quantum_magnetic',f.magnetic_map,64100,np.hypot(200,650)),5.)
        result=f.update_nv_packet(p)
        self.assertEqual(result.used,used)
        np.testing.assert_allclose(f.ekf.x,reference.x)
        np.testing.assert_allclose(f.ekf.P,reference.P)
    def test_duplicate_rejected_without_state_change(self):
        f=engine();f.predict([0,0],1.);p=nv_packet(field_est(64),0)
        self.assertTrue(f.update_nv_packet(p).used)
        state=f.ekf.x.copy();cov=f.ekf.P.copy()
        self.assertFalse(f.update_nv_packet(p).used)
        np.testing.assert_array_equal(f.ekf.x,state);np.testing.assert_array_equal(f.ekf.P,cov)
    def test_stale_future_and_wrong_contract(self):
        f=engine();f.predict([0,0],1.)
        for t in [0,2]:
            r=f.update_nv_packet(nv_packet(field_est(t=t),0));self.assertIn('timestamp_mismatch',r.flags)
        p=nv_packet(field_est(),0);p.metadata['units']='uT'
        self.assertIn('incompatible_contract',f.update_nv_packet(p).flags)
    def test_gate_and_unavailable_map(self):
        f=engine();f.predict([0,0],1.)
        self.assertIn('innovation_gate',f.update_nv_packet(nv_packet(field_est(300),0)).flags)
        f.ekf.x[0]=1000
        self.assertIn('map_unavailable',f.update_nv_packet(nv_packet(field_est(64),1)).flags)
    def test_gravity_update_and_covariance_psd(self):
        f=engine();f.predict([0,0],1.)
        self.assertTrue(f.update_gravity(101,2,1).used)
        np.testing.assert_allclose(f.ekf.P,f.ekf.P.T,atol=1e-12)
        self.assertGreaterEqual(np.linalg.eigvalsh(f.ekf.P).min(),-1e-10)
        self.assertFalse(f.update_gravity(100,2,0).used)
        self.assertEqual(len(f.state_packet(1).metadata['covariance']),6)
    def test_stationary_velocity_update(self):
        f=engine();f.predict([.1,.2],1.)
        before=np.trace(f.ekf.P[2:4,2:4])
        f.update_stationary_velocity([0,0],.03)
        self.assertLess(np.linalg.norm(f.ekf.x[2:4]),.01)
        self.assertLess(np.trace(f.ekf.P[2:4,2:4]),before)
        self.assertGreaterEqual(np.linalg.eigvalsh(f.ekf.P).min(),-1e-10)
        with self.assertRaises(ValueError):f.update_stationary_velocity([0,0],0)
    def test_future_gravity_rejected(self):
        f=engine();f.predict([0,0],1.)
        self.assertIn('timestamp_mismatch',f.update_gravity(100,2,1.1).flags)
    def test_invalid_configuration_and_predict(self):
        with self.assertRaises(ValueError): IntegratedConfig(stationary_s=10)
        with self.assertRaises(ValueError): IntegratedConfig(transit_s=10.1)
        with self.assertRaises(ValueError): IntegratedConfig(scenario='unknown')
        f=engine()
        with self.assertRaises(ValueError): f.predict([0,0],0)
        with self.assertRaises(ValueError): f.predict([np.nan,0],1)
        with self.assertRaises(ValueError): nv_packet(field_est(std=0),0)
    def test_embedded_source_hashes(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'GRAVITY_SOURCE.json').read_text())
        for name,expected in manifest['modules_sha256'].items():
            self.assertEqual(hashlib.sha256((root/'rq_sensing/_gravity_v07'/name).read_bytes()).hexdigest(),expected)
if __name__=='__main__':unittest.main()
