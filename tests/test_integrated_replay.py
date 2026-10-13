import unittest
import numpy as np
from rq_sensing.integrated_simulation import run_integrated,IntegratedConfig
from rq_sensing.replay_fusion import replay

class IntegratedReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result,cls.mmap,cls.gmap,cls.scans=run_integrated(IntegratedConfig(waypoints=3))
    def test_sensor_only_replay_matches_fused_state(self):
        result=self.result
        states,_=replay(result['input_packets'],self.mmap,self.gmap,result['initialization'])
        expected=result['final_states']['fused']['values']
        np.testing.assert_allclose(list(states[-1].values.values()),list(expected.values()),rtol=1e-12,atol=1e-10)
        self.assertTrue(all('truth' not in p for p in result['input_packets']))
    def test_acquisition_stays_stationary(self):
        for epoch,scan in enumerate(self.scans):
            records=[r for r in self.result['records'] if r['epoch']==epoch and r['phase']=='stationary']
            truth=np.array([r['truth'] for r in records])
            np.testing.assert_allclose(truth[:,2:],0,atol=1e-10)
            self.assertLess(np.max(np.linalg.norm(truth[:,:2]-truth[-1,:2],axis=1)),1e-8)
            self.assertGreaterEqual(len(records)*.5,len(scan.counts)*scan.dwell_s)
    def test_flat_field_disables_magnetic_aiding(self):
        r,_,_,_=run_integrated(IntegratedConfig(waypoints=2,scenario='flat_magnetic'))
        self.assertEqual(r['metrics']['magnetic']['magnetic_updates'],0)
        self.assertAlmostEqual(r['metrics']['fused']['rmse_m'],r['metrics']['gravity']['rmse_m'])
        self.assertAlmostEqual(r['metrics']['magnetic']['rmse_m'],r['metrics']['ins']['rmse_m'])
    def test_duplicate_replay_rejected(self):
        p=self.result['input_packets'][0]
        with self.assertRaises(ValueError):replay([p,p],self.mmap,self.gmap,self.result['initialization'])
    def test_wrong_frame_rejected(self):
        p={**self.result['input_packets'][0],'frame':'body_xyz'}
        with self.assertRaises(ValueError):replay([p],self.mmap,self.gmap,self.result['initialization'])
if __name__=='__main__':unittest.main()
