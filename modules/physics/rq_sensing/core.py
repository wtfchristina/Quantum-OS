"""Axial CW-ODMR simulation and estimation. Frequencies in MHz, fields in uT."""
from dataclasses import dataclass, asdict
from typing import Protocol
import numpy as np
from scipy.optimize import least_squares
from scipy.signal import find_peaks, savgol_filter

D0_MHZ = 2870.0
GAMMA_MHZ_PER_UT = 0.02802495
TEMP_MHZ_PER_K = -0.0742

@dataclass(frozen=True)
class SensorConfig:
    linewidth_mhz: float = 0.35  # FWHM
    contrast: float = 0.06  # per transition
    photon_rate_per_s: float = 2e6
    dwell_s: float = 0.05  # per frequency point
    strain_mhz: float = 0.15
    baseline_slope: float = 0.01  # fractional change across scan

    def __post_init__(self):
        vals = np.array(list(asdict(self).values()))
        if not np.all(np.isfinite(vals)):
            raise ValueError('Configuration must be finite')
        if min(self.linewidth_mhz, self.photon_rate_per_s, self.dwell_s) <= 0:
            raise ValueError('Linewidth, photon rate and dwell must be positive')
        if not 0 < self.contrast < 0.4 or self.strain_mhz < 0 or abs(self.baseline_slope) >= 0.5:
            raise ValueError('Invalid contrast, strain or baseline slope')

@dataclass
class Spectrum:
    frequency_mhz: np.ndarray
    counts: np.ndarray
    dwell_s: float
    timestamp_s: float = 0.0

    def __post_init__(self):
        self.frequency_mhz = np.asarray(self.frequency_mhz, dtype=float)
        self.counts = np.asarray(self.counts, dtype=float)
        f, y = self.frequency_mhz, self.counts
        if f.ndim != 1 or y.shape != f.shape or len(f) < 40:
            raise ValueError('Spectrum needs at least 40 paired 1D samples')
        if not np.all(np.isfinite(f)) or not np.all(np.isfinite(y)) or np.any(y < 0):
            raise ValueError('Frequencies/counts must be finite; counts nonnegative')
        if np.any(np.diff(f) <= 0) or not np.isfinite(self.dwell_s) or self.dwell_s <= 0:
            raise ValueError('Frequencies must increase and dwell must be positive')
        if not np.isfinite(self.timestamp_s):
            raise ValueError('Timestamp must be finite')

class SensorSource(Protocol):
    def acquire(self, field_ut: float, temperature_k: float = 293.15,
                timestamp_s: float = 0.0) -> Spectrum: ...

def resonances(field_ut, temperature_k=293.15, strain_mhz=0.15):
    if not np.all(np.isfinite([field_ut, temperature_k, strain_mhz])) or strain_mhz < 0:
        raise ValueError('Invalid field, temperature or strain')
    if not 280 <= temperature_k <= 330 or abs(field_ut) > 1000:
        raise ValueError('v0.1 model supports 280–330 K and |axial B| <= 1000 uT')
    center = D0_MHZ + TEMP_MHZ_PER_K * (temperature_k - 293.15)
    half = np.hypot(GAMMA_MHZ_PER_UT * field_ut, strain_mhz)
    return center - half, center + half

def lineshape(f, center, half, width, c1, c2, baseline, slope):
    x = (f - (f[0] + f[-1])/2) / np.ptp(f)
    lorentz = lambda pos: 1 / (1 + (2 * (f - pos) / width)**2)
    return baseline * (1 + slope*x) * (1 - c1*lorentz(center-half) - c2*lorentz(center+half))

class SimulatedNVSensor:
    def __init__(self, config=None, seed=7, frequency_mhz=None):
        self.config = config or SensorConfig()
        self.rng = np.random.default_rng(seed)
        self.frequency_mhz = np.linspace(2863, 2877, 401) if frequency_mhz is None else np.asarray(frequency_mhz)
        Spectrum(self.frequency_mhz, np.ones_like(self.frequency_mhz), self.config.dwell_s)

    def acquire(self, field_ut, temperature_k=293.15, timestamp_s=0.0):
        cfg = self.config
        low, high = resonances(field_ut, temperature_k, cfg.strain_mhz)
        if low - cfg.linewidth_mhz < self.frequency_mhz[0] or high + cfg.linewidth_mhz > self.frequency_mhz[-1]:
            raise ValueError('Scan does not cover both resonances and linewidth margin')
        mean = lineshape(self.frequency_mhz, (low+high)/2, (high-low)/2,
                         cfg.linewidth_mhz, cfg.contrast, cfg.contrast,
                         cfg.photon_rate_per_s*cfg.dwell_s, cfg.baseline_slope)
        return Spectrum(self.frequency_mhz, self.rng.poisson(mean), cfg.dwell_s, timestamp_s)

@dataclass
class FieldEstimate:
    accepted: bool
    flags: list[str]
    axial_magnitude_ut: float | None
    field_std_ut: float | None
    center_mhz: float
    half_splitting_mhz: float
    linewidth_mhz: float
    contrast_low: float
    contrast_high: float
    reduced_chi_square: float
    temperature_proxy_k: float
    fit_parameters: list[float]
    timestamp_s: float

    def to_dict(self):
        return asdict(self)

def estimate_field(spectrum, strain_mhz=0.15):
    """Fit counts with Poisson-weighted least squares and multi-start search.

    Strain is supplied by calibration, not identified from a single spectrum.
    Standard error is a local linearized approximation, conditional on that strain.
    """
    if not np.isfinite(strain_mhz) or strain_mhz < 0:
        raise ValueError('Strain must be finite and nonnegative')
    f, y = spectrum.frequency_mhz, spectrum.counts
    scale = float(np.median(y))
    if scale <= 0:
        raise ValueError('Spectrum has no usable baseline')
    z = y/scale
    sigma = np.sqrt(np.maximum(y, 1))/scale
    span = np.ptp(f)
    step = float(np.median(np.diff(f)))
    # [center, half splitting, FWHM, low contrast, high contrast, baseline, slope]
    bounds = ([f[0], 0, step, 0, 0, 0.5, -0.5],
              [f[-1], span/2, span/3, 0.4, 0.4, 1.5, 0.5])
    residual = lambda p: (lineshape(f, *p)-z)/sigma
    trials = []
    smooth = savgol_filter(z, 9, 2)
    peaks, _ = find_peaks(-smooth, distance=5, prominence=.005)
    if len(peaks) >= 2:
        ranked = peaks[np.argsort(smooth[peaks])[:4]]
        for i in range(len(ranked)):
            for j in range(i+1, len(ranked)):
                low, high = sorted(f[ranked[[i,j]]])
                trials.append(least_squares(residual, [(low+high)/2, (high-low)/2,
                    max(step*2, span/35), .05, .05, 1., 0.],
                    bounds=bounds, x_scale='jac', max_nfev=500))
    for center in [(f[0]+f[-1])/2, float(f[np.argmin(y)])]:
        for half in [0.12*span, 0.3*span, 0.025*span]:
            p = [center, half, max(step*2, span/35), .05, .05, 1., 0.]
            trials.append(least_squares(residual, p, bounds=bounds, x_scale='jac', max_nfev=500))
    result = min(trials, key=lambda r: np.dot(r.fun, r.fun))
    p = result.x
    center, half, width, c1, c2, base, slope = p
    chi = float(np.dot(result.fun, result.fun)/(len(f)-len(p)))
    covariance = np.linalg.pinv(result.jac.T @ result.jac) * max(1., chi)
    flags = []
    if not result.success: flags.append('fit_failed')
    if np.linalg.matrix_rank(result.jac) < len(p): flags.append('singular_fit')
    if chi > 2.5: flags.append('model_mismatch')
    if 2*half < 1.5*width: flags.append('unresolved_resonances')
    if center-half-2*width < f[0] or center+half+2*width > f[-1]: flags.append('scan_edge')
    if width < 2*step: flags.append('undersampled_linewidth')
    for i in [3, 4]:
        if p[i] < .003 or p[i]/max(np.sqrt(covariance[i, i]), 1e-12) < 5:
            flags.append('low_contrast'); break
    if half <= strain_mhz: flags.append('below_strain_floor')
    field = error = None
    if half > strain_mhz:
        root = np.sqrt(half*half-strain_mhz*strain_mhz)
        candidate = root/GAMMA_MHZ_PER_UT
        uncertainty = half/root/GAMMA_MHZ_PER_UT*np.sqrt(covariance[1,1])
        if uncertainty > max(1., .25*candidate): flags.append('high_uncertainty')
        if candidate > 1000: flags.append('outside_model_range')
        if not flags: field, error = float(candidate), float(uncertainty)
    temp = 293.15 + (center-D0_MHZ)/TEMP_MHZ_PER_K
    if not 280 <= temp <= 330:
        flags.append('outside_temperature_range'); field = error = None
    return FieldEstimate(not flags, flags, field, error, float(center), float(half),
                         float(width), float(c1), float(c2), chi, float(temp),
                         [float(v) for v in p], spectrum.timestamp_s)
