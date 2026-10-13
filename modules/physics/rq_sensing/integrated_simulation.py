"""Raw ODMR + gravity + body-aligned planar IMU stop/go benchmark."""
from dataclasses import dataclass,asdict
import numpy as np
from .core import SimulatedNVSensor,estimate_field
from ._gravity_v07.packets import SensorPacket
from .scenarios import make_map,trajectory,environment_field
from .fusion_bridge import QuantumGravityFusion,nv_packet
from ._gravity_v07.dynamics import propagate_truth
from ._gravity_v07.imu import IMUSimulator,IMUConfig
from ._gravity_v07.gravity_map import SyntheticGravityMap,GaussianAnomaly

@dataclass(frozen=True)
class IntegratedConfig:
    seed: int = 17
    waypoints: int = 40
    scenario: str = 'nominal'
    dt_s: float = .5
    stationary_s: float = 21.
    transit_s: float = 10.
    gravity_std: float = 2.
    stationary_aiding: bool = True
    stationary_velocity_std_mps: float = .03

    def __post_init__(self):
        if self.scenario not in ['nominal','dropouts','interference','flat_magnetic']:raise ValueError('Invalid scenario')
        if not isinstance(self.waypoints,int) or self.waypoints<2:raise ValueError('Need at least two waypoints')
        vals=np.array([self.dt_s,self.stationary_s,self.transit_s,self.gravity_std,self.stationary_velocity_std_mps])
        if not np.all(np.isfinite(vals)) or np.any(vals<=0) or self.stationary_s<20.05:
            raise ValueError('Invalid cadence or gravity noise')
        if not np.isclose(self.transit_s/(2*self.dt_s),round(self.transit_s/(2*self.dt_s))) or not np.isclose(self.stationary_s/self.dt_s,round(self.stationary_s/self.dt_s)):
            raise ValueError('Cadences must align with discrete time; transit needs even steps')

def gravity_environment():
    return SyntheticGravityMap([
        GaussianAnomaly(170,170,85,70,45),GaussianAnomaly(270,300,-70,70,55),
        GaussianAnomaly(410,200,95,60,65),GaussianAnomaly(550,320,-55,65,50)])

def run_integrated(cfg=None):
    cfg=cfg or IntegratedConfig(); points=trajectory(cfg.waypoints)
    mmap=make_map(flat=cfg.scenario=='flat_magnetic'); gmap=gravity_environment()
    streams=np.random.SeedSequence(cfg.seed).spawn(4)
    imu=IMUSimulator(IMUConfig(),np.random.default_rng(streams[0])); grng=np.random.default_rng(streams[1])
    vrng=np.random.default_rng(streams[3])
    sensor=SimulatedNVSensor(seed=int(streams[2].generate_state(1)[0]))
    state=np.array([*points[0],0.,0.]); ins=state.copy()
    initial=np.array([*state,0.,0.]); P0=np.diag([18.**2,18.**2,.1**2,.1**2,.03**2,.03**2])
    modes=['ins','gravity','magnetic','fused']
    filters={mode:QuantumGravityFusion(initial,P0,mmap,gmap) for mode in modes}
    t=0.; input_packets=[]; records=[]; scans=[]; packets=[]; estimates=[]; updates={m:[] for m in filters}
    def propagate(a_true,phase,epoch):
        nonlocal state,ins,t
        t+=cfg.dt_s; state=propagate_truth(state,a_true,cfg.dt_s)
        a_meas,_=imu.sample(a_true,cfg.dt_s); ins=propagate_truth(ins,a_meas,cfg.dt_s)
        input_packets.append(SensorPacket('imu',t,len(records),{'ax_mps2':float(a_meas[0]),'ay_mps2':float(a_meas[1])}).to_dict())
        for f in filters.values():f.predict(a_meas,t)
        record={'time_s':t,'phase':phase,'epoch':epoch,'truth':state.tolist(),'imu_accel':a_meas.tolist(),'ins':ins.tolist()}
        record['uncompensated_dead_reckoning']=ins.tolist()
        record.update({mode:f.ekf.x.tolist() for mode,f in filters.items()});records.append(record)
    for k,xy in enumerate(points):
        if k:
            accel=(xy-points[k-1])/(cfg.transit_s/2)**2
            for _ in range(round(cfg.transit_s/(2*cfg.dt_s))):propagate(accel,'transit',k)
            for _ in range(round(cfg.transit_s/(2*cfg.dt_s))):propagate(-accel,'transit',k)
        for _ in range(round(cfg.stationary_s/cfg.dt_s)):propagate(np.zeros(2),'stationary',k)
        assert np.linalg.norm(state[:2]-xy)<1e-7 and np.linalg.norm(state[2:])<1e-9
        b=60. if cfg.scenario=='flat_magnetic' else float(environment_field(*state[:2]))
        scan=sensor.acquire(b,293.15+3*k/(cfg.waypoints-1),timestamp_s=t)
        # Scan completion time is t; truth stayed still for all 20.05 s acquisition.
        if cfg.scenario=='interference' and 12<=k<17:scan.counts[100:150]*=.75
        fit=estimate_field(scan); packet=nv_packet(fit,k)
        if cfg.scenario=='dropouts' and 12<=k<20:packet=None
        z_g=float(gmap.value(*state[:2])+grng.normal(0,cfg.gravity_std))
        if packet is not None:packets.append(packet.to_dict())
        velocity_measurement=vrng.normal(0,cfg.stationary_velocity_std_mps,2)
        if cfg.stationary_aiding:
            input_packets.append(SensorPacket('stationary_velocity',t,k,{'vx_mps':float(velocity_measurement[0]),'vy_mps':float(velocity_measurement[1]),'noise_std_mps':cfg.stationary_velocity_std_mps},metadata={'stationarity_source':'trusted_stop_signal'}).to_dict())
        input_packets.append(SensorPacket('gravity',t,k,{'value':z_g,'noise_std':cfg.gravity_std},metadata={'observable':'synthetic_scalar_gravity','units':'toy_units'}).to_dict())
        if packet is not None:input_packets.append(packet.to_dict())
        for mode,f in filters.items():
            if cfg.stationary_aiding:f.update_stationary_velocity(velocity_measurement,cfg.stationary_velocity_std_mps)
            g=f.update_gravity(z_g,cfg.gravity_std,t) if mode in ['gravity','fused'] else None
            m=f.update_nv_packet(packet) if packet is not None and mode in ['magnetic','fused'] else None
            updates[mode].append({'epoch':k,'time_s':t,'gravity':None if g is None else g.to_dict(),'magnetic':None if m is None else m.to_dict()})
            records[-1][mode]=f.ekf.x.tolist()
        scans.append(scan);estimates.append({'epoch':k,'true_field_ut':b,'gravity_value_toy_units':z_g,'packet_available':packet is not None,**fit.to_dict()})
    truth=np.array([r['truth'][:2] for r in records]);metrics={}
    for mode in modes:
        p=np.array([r[mode][:2] for r in records]);err=np.linalg.norm(p-truth,axis=1)
        metrics[mode]={'rmse_m':float(np.sqrt(np.mean(err**2))),'final_error_m':float(err[-1]),'max_error_m':float(err.max()),
            'gravity_updates':sum(bool(u['gravity'] and u['gravity']['used']) for u in updates.get(mode,[])),
            'magnetic_updates':sum(bool(u['magnetic'] and u['magnetic']['used']) for u in updates.get(mode,[]))}
    return {'config':asdict(cfg),'metrics':metrics,'duration_s':t,'scope':'Synthetic stationary ODMR scans, fixed known axis, local planar acceleration model',
            'records':records,'sensor_estimates':estimates,'update_trace':updates,'nv_packets':packets,'input_packets':input_packets,'initialization':{'state':initial.tolist(),'covariance':P0.tolist(),'timestamp_s':0.},'final_states':{mode:f.state_packet(cfg.waypoints).to_dict() for mode,f in filters.items()}},mmap,gmap,scans
