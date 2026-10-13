"""NV sensing adapter for the byte-preserved gravity v0.7 FusionEKF API."""
from dataclasses import dataclass,asdict
import numpy as np
from ._gravity_v07.fusion import FusionEKF,FieldObservation
from ._gravity_v07.packets import SensorPacket

class AxialMapNT:
    """Map must represent the same fixed-axis magnitude as the sensor."""
    def __init__(self,magnetic_map): self.map=magnetic_map
    def value(self,x,y): return float(self.map.sample([[x,y]])[0])*1000.
    def gradient(self,x,y):
        # Central difference; no extrapolation near/outside grid boundaries.
        h=1.
        vals=self.map.sample([[x+h,y],[x-h,y],[x,y+h],[x,y-h]])*1000.
        return np.array([(vals[0]-vals[1])/(2*h),(vals[2]-vals[3])/(2*h)])

def nv_packet(estimate,sequence,scan_duration_s=20.05):
    if not isinstance(sequence,int) or sequence<0 or not np.isfinite(scan_duration_s) or scan_duration_s<=0:
        raise ValueError('Invalid sequence or scan duration')
    if not estimate.accepted: return None
    vals=[estimate.axial_magnitude_ut,estimate.field_std_ut,estimate.timestamp_s]
    if any(v is None for v in vals) or not np.all(np.isfinite(vals)) or vals[0]<0 or vals[1]<=0:
        raise ValueError('Invalid accepted field estimate')
    return SensorPacket('quantum_magnetic',float(estimate.timestamp_s),sequence,
        {'axial_magnitude_nt':float(vals[0]*1000),'field_std_nt':float(vals[1]*1000),'scan_duration_s':float(scan_duration_s)},
        frame='local_xy',metadata={'observable':'fixed_axis_magnitude','units':'nT','timestamp_reference':'scan_end',
        'scan_start_s':float(estimate.timestamp_s-scan_duration_s),'stationary_scan_required':True,'sensor_model':'axial_nv_cw_odmr'})

@dataclass
class UpdateStatus:
    used: bool
    flags: list[str]
    innovation: float | None = None
    def to_dict(self):return asdict(self)

class QuantumGravityFusion:
    """Local six-state EKF, not a full strapdown INS or attitude estimator."""
    def __init__(self,initial_state,P0,magnetic_map,gravity_map,initial_timestamp_s=0.,
                 map_std_nt=650.,minimum_field_std_nt=100.,gate_sigma=5.,max_age_s=.25):
        state=np.asarray(initial_state,dtype=float); cov=np.asarray(P0,dtype=float)
        if state.shape!=(6,) or cov.shape!=(6,6) or not np.all(np.isfinite(state)) or not np.all(np.isfinite(cov)):
            raise ValueError('State/covariance shapes must be 6 and 6x6, finite')
        if not np.allclose(cov,cov.T) or np.min(np.linalg.eigvalsh(cov))<0: raise ValueError('Covariance must be symmetric PSD')
        v=np.array([initial_timestamp_s,map_std_nt,minimum_field_std_nt,gate_sigma,max_age_s])
        if not np.all(np.isfinite(v)) or min(map_std_nt,minimum_field_std_nt,gate_sigma,max_age_s)<=0:
            raise ValueError('Invalid integration configuration')
        self.ekf=FusionEKF(state,cov); self.magnetic_map=AxialMapNT(magnetic_map); self.gravity_map=gravity_map
        self.time=float(initial_timestamp_s); self.map_std_nt=map_std_nt; self.minimum_field_std_nt=minimum_field_std_nt
        self.gate_sigma=gate_sigma; self.max_age_s=max_age_s; self.last_sequence=-1
    def predict(self,acceleration_mps2,timestamp_s):
        a=np.asarray(acceleration_mps2,dtype=float); t=float(timestamp_s)
        if a.shape!=(2,) or not np.all(np.isfinite(a)) or not np.isfinite(t) or t<=self.time:
            raise ValueError('Prediction requires finite 2D acceleration and strictly increasing time')
        self.ekf.predict(a,t-self.time); self.time=t
    def _update(self,name,field,value,std):
        if not np.all(np.isfinite([value,std])) or std<=0: return UpdateStatus(False,['invalid_measurement'])
        x,y=self.ekf.x[:2]; pred=float(field.value(x,y)); grad=np.asarray(field.gradient(x,y))
        if grad.shape!=(2,) or not np.isfinite(pred) or not np.all(np.isfinite(grad)):
            return UpdateStatus(False,['map_unavailable'])
        if np.linalg.norm(grad)<1e-8:return UpdateStatus(False,['uninformative_map'])
        used=self.ekf.update(FieldObservation(name,field,float(value),float(std)),self.gate_sigma)
        return UpdateStatus(bool(used),[] if used else ['innovation_gate'],float(value-pred))
    def update_gravity(self,value,noise_std,timestamp_s):
        t=float(timestamp_s)
        if not np.isfinite(t) or t>self.time+1e-9 or self.time-t>self.max_age_s:return UpdateStatus(False,['timestamp_mismatch'])
        # Caller owns gravity observation identity; no gravity replay channel here.
        return self._update('gravity',self.gravity_map,value,noise_std)
    def update_nv_packet(self,packet):
        if packet.sensor!='quantum_magnetic' or packet.frame!='local_xy' or packet.metadata.get('observable')!='fixed_axis_magnitude' or packet.metadata.get('units')!='nT' or packet.metadata.get('timestamp_reference')!='scan_end':
            return UpdateStatus(False,['incompatible_contract'])
        if not isinstance(packet.sequence,int) or packet.sequence<0:return UpdateStatus(False,['invalid_sequence'])
        if packet.sequence<=self.last_sequence:return UpdateStatus(False,['duplicate_or_out_of_order'])
        if not np.isfinite(packet.timestamp_s) or packet.timestamp_s>self.time+1e-9 or self.time-packet.timestamp_s>self.max_age_s:
            return UpdateStatus(False,['timestamp_mismatch'])
        try:
            z=float(packet.values['axial_magnitude_nt']); std=float(packet.values['field_std_nt']); duration=float(packet.values['scan_duration_s'])
        except (KeyError,TypeError,ValueError):return UpdateStatus(False,['invalid_measurement'])
        if not np.all(np.isfinite([z,std,duration])) or z<0 or std<=0 or duration<=0:
            return UpdateStatus(False,['invalid_measurement'])
        self.last_sequence=packet.sequence
        sigma=float(np.hypot(max(std,self.minimum_field_std_nt),self.map_std_nt))
        return self._update('quantum_magnetic',self.magnetic_map,z,sigma)
    def update_stationary_velocity(self,velocity_mps,noise_std_mps):
        """Optional external stop signal + noisy zero-velocity observation.

        Stationarity is supplied by the caller, not detected by this class.
        """
        z=np.asarray(velocity_mps,dtype=float)
        if z.shape!=(2,) or not np.all(np.isfinite(z)) or not np.isfinite(noise_std_mps) or noise_std_mps<=0:
            raise ValueError('Invalid stationary velocity observation')
        H=np.zeros((2,6)); H[:,2:4]=np.eye(2)
        R=np.eye(2)*noise_std_mps**2
        innovation=z-H@self.ekf.x
        S=H@self.ekf.P@H.T+R
        K=np.linalg.solve(S,(self.ekf.P@H.T).T).T
        self.ekf.x+=K@innovation
        A=np.eye(6)-K@H
        self.ekf.P=A@self.ekf.P@A.T+K@R@K.T
        return UpdateStatus(True,[])
    def state_packet(self,sequence):
        return SensorPacket('navigation_state',self.time,sequence,
            dict(zip(['x_m','y_m','vx_mps','vy_mps','bax_mps2','bay_mps2'],map(float,self.ekf.x))),
            metadata={'state_order':['x','y','vx','vy','bax','bay'],'covariance':self.ekf.P.tolist(),'fusion_source':'gravity_nav_0.7_FusionEKF'})
