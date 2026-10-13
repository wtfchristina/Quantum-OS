"""Local 2D particle map matching for a fixed, known NV axis."""
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.special import logsumexp

@dataclass
class MagneticMap:
    x_m: np.ndarray
    y_m: np.ndarray
    axial_magnitude_ut: np.ndarray  # [y,x]
    def __post_init__(self):
        self.x_m=np.asarray(self.x_m,dtype=float); self.y_m=np.asarray(self.y_m,dtype=float)
        self.axial_magnitude_ut=np.asarray(self.axial_magnitude_ut,dtype=float)
        if self.x_m.ndim!=1 or self.y_m.ndim!=1 or min(len(self.x_m),len(self.y_m))<2:
            raise ValueError('Map axes must be one-dimensional with at least two points')
        if np.any(np.diff(self.x_m)<=0) or np.any(np.diff(self.y_m)<=0): raise ValueError('Map axes must increase')
        if self.axial_magnitude_ut.shape!=(len(self.y_m),len(self.x_m)): raise ValueError('Map shape must be [y,x]')
        if not all(np.all(np.isfinite(x)) for x in [self.x_m,self.y_m,self.axial_magnitude_ut]) or np.any(self.axial_magnitude_ut<0):
            raise ValueError('Map must be finite and magnitudes nonnegative')
        self._interpolator=RegularGridInterpolator((self.y_m,self.x_m),self.axial_magnitude_ut,bounds_error=False,fill_value=np.nan)
    def sample(self, xy_m):
        xy=np.asarray(xy_m,dtype=float)
        if xy.ndim<1 or xy.shape[-1]!=2 or not np.all(np.isfinite(xy)): raise ValueError('Positions must be finite (...,2)')
        return self._interpolator(xy[...,::-1])
    def save(self,path):
        np.savez(path,x_m=self.x_m,y_m=self.y_m,axial_magnitude_ut=self.axial_magnitude_ut)
    @classmethod
    def load(cls,path):
        with np.load(path,allow_pickle=False) as z: return cls(z['x_m'],z['y_m'],z['axial_magnitude_ut'])

@dataclass(frozen=True)
class MatcherConfig:
    particles: int = 2500
    initial_std_m: float = 18.
    motion_std_m: float = 1.5  # per step, each coordinate
    map_std_ut: float = .65
    minimum_measurement_std_ut: float = .1
    gate_sigma: float = 5.
    resample_fraction: float = .5
    minimum_map_spread_ut: float = .03
    def __post_init__(self):
        if not isinstance(self.particles,int) or self.particles<100: raise ValueError('At least 100 particles required')
        v=np.array([self.initial_std_m,self.motion_std_m,self.map_std_ut,self.minimum_measurement_std_ut,self.gate_sigma,self.minimum_map_spread_ut])
        if not np.all(np.isfinite(v)) or np.any(v<=0) or not 0<self.resample_fraction<=1:
            raise ValueError('Invalid matcher configuration')

@dataclass
class PositionEstimate:
    position_m: list
    covariance_m2: list
    measurement_used: bool
    flags: list
    effective_sample_size: float
    valid_map_mass: float
    innovation_ut: float | None
    def to_dict(self): return asdict(self)

class ParticleMapMatcher:
    def __init__(self,magnetic_map,initial_position_m,config=None,seed=1):
        self.map=magnetic_map; self.config=config or MatcherConfig(); self.rng=np.random.default_rng(seed)
        initial=np.asarray(initial_position_m,dtype=float)
        if initial.shape!=(2,) or not np.all(np.isfinite(initial)): raise ValueError('Initial position must have two finite coordinates')
        self.particles=initial+self.rng.normal(0,self.config.initial_std_m,(self.config.particles,2))
        self.weights=np.full(self.config.particles,1/self.config.particles)
    def _summary(self,used,flags,valid_mass,innovation):
        mean=np.average(self.particles,axis=0,weights=self.weights); d=self.particles-mean
        cov=(d*self.weights[:,None]).T@d
        return PositionEstimate(mean.tolist(),cov.tolist(),used,flags,float(1/np.sum(self.weights**2)),float(valid_mass),innovation)
    def step(self,displacement_m,field_estimate=None):
        delta=np.asarray(displacement_m,dtype=float)
        if delta.shape!=(2,) or not np.all(np.isfinite(delta)): raise ValueError('Displacement must have two finite coordinates')
        self.particles+=delta+self.rng.normal(0,self.config.motion_std_m,self.particles.shape)
        predicted=self.map.sample(self.particles); valid=np.isfinite(predicted)
        mass=float(self.weights[valid].sum()); flags=[]; innovation=None; used=False
        if mass<.95: flags.append('map_boundary')
        # Never clamp particles, extrapolate the map, or silently reinitialize.
        if mass<.5: flags.append('insufficient_map_support')
        elif field_estimate is None or not field_estimate.accepted: flags.append('sensor_unavailable')
        elif field_estimate.axial_magnitude_ut is None or field_estimate.field_std_ut is None or not np.isfinite(field_estimate.axial_magnitude_ut) or not np.isfinite(field_estimate.field_std_ut) or field_estimate.field_std_ut<=0:
            flags.append('invalid_field_estimate')
        else:
            w=self.weights[valid]/mass; mean=float(w@predicted[valid])
            variance=float(w@((predicted[valid]-mean)**2))
            innovation=float(field_estimate.axial_magnitude_ut-mean)
            noise_var=max(field_estimate.field_std_ut,self.config.minimum_measurement_std_ut)**2+self.config.map_std_ut**2
            if np.sqrt(variance)<self.config.minimum_map_spread_ut: flags.append('uninformative_map')
            elif abs(innovation)>self.config.gate_sigma*np.sqrt(variance+noise_var): flags.append('magnetic_outlier')
            else:
                logw=np.full(len(self.weights),-np.inf)
                logw[valid]=np.log(np.maximum(self.weights[valid],1e-300))-.5*(predicted[valid]-field_estimate.axial_magnitude_ut)**2/noise_var
                self.weights=np.exp(logw-logsumexp(logw)); used=True
        summary=self._summary(used,flags,mass,innovation)
        if used and summary.effective_sample_size<self.config.resample_fraction*len(self.weights):
            u=(self.rng.random()+np.arange(len(self.weights)))/len(self.weights)
            cumulative=np.cumsum(self.weights); cumulative[-1]=1.
            indices=np.searchsorted(cumulative,u)
            self.particles=self.particles[indices].copy(); self.weights.fill(1/len(self.weights))
        return summary
