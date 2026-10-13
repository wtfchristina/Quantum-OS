# RelativisticQ-PNT — retained sensor/localization subsystem

**New:** simulated magnetic maps, a 2D particle map matcher, and a reproducible localization benchmark driven by the actual v0.1 ODMR simulator and field fitter.

This is a synthetic research prototype. It estimates position locally from a fixed, known NV-axis magnetic magnitude map and noisy displacement measurements. It does not implement a real IMU mechanization, arbitrary sensor orientation, global localization, GNSS, hardware control, or integration with the gravity-aided package in the v0.2 particle-matching demo. The current release adds a separate gravity-filter bridge described in README.md.

## Quick start

Extract the ZIP. Open `localization_output/report.html` to see the pre-generated localization demo and benchmark. In a terminal in this folder, with Python 3.10+:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python examples/localization_demo.py
python -m unittest discover -s tests -v
```

To rerun all eight benchmark cases:

```bash
python examples/localization_demo.py --benchmark
```

The retained sensor-only demo runs with `python examples/demo.py`. CSV fitting and the physics assumptions are documented in `SENSOR_PIPELINE.md`.

## Data path

Synthetic field at true position → Poisson photon counts in a two-dip ODMR spectrum → resonance fit → axial field magnitude and standard error → map likelihood → particle position estimate and covariance.

Both the baseline and magnetic-aided tracker receive the same known initial position and the same corrupted displacement increments. Only the magnetic-aided tracker receives field estimates. The matcher accepts no true trajectory or true field as an input; the scenario generator uses truth only to create sensor measurements and score errors. Its initial particle cloud has 18 m standard deviation per coordinate around the starting fix. This is **local tracking**, not position discovery anywhere on a map.

## What's included

- `rq_sensing/navigation.py`: map interpolation, NPZ map import/export, particle prediction, Gaussian map likelihood, ESS-triggered systematic resampling, boundary and measurement gates.
- `rq_sensing/scenarios.py`: fictional scalar magnetic environment, trajectory, biased/noisy motion increments.
- `examples/localization_demo.py`: 60 raw ODMR scans along a route, sensing-to-localization pipeline, dead-reckoning comparison and eight benchmark cases.
- `tests/`: sensor and navigation tests.
- `localization_output/`: plots, HTML report, benchmark JSON, map grid, raw ODMR scans, track CSV/JSON and build environment/configuration.
- `VALIDATION.md`: measured results and their limits.

## API

```python
from rq_sensing import SimulatedNVSensor, estimate_field
from rq_sensing.navigation import ParticleMapMatcher, MagneticMap

magnetic_map = MagneticMap.load('localization_output/magnetic_map.npz')
matcher = ParticleMapMatcher(magnetic_map, initial_position_m=[120, 200], seed=1)
sensor = SimulatedNVSensor(seed=7)
field = estimate_field(sensor.acquire(65))
position = matcher.step(displacement_m=[3.0, 0.5], field_estimate=field)
print(position.to_dict())
```

This API snippet shows wiring only; the illustrative 65 µT must match the field at the actual position in a real use. Map arrays are `[y, x]`, local position is `[x, y]` in meters, magnetic magnitude is µT. NPZ maps contain `x_m`, `y_m`, `axial_magnitude_ut`. The matching map must represent the same fixed-axis magnitude as the sensor: a total-field map is not interchangeable. Missing or rejected measurements can be supplied as `None` or a rejected `FieldEstimate`.

`PositionEstimate` includes the posterior mean/covariance, whether the measurement was used, effective sample size before resampling, prior valid map mass, innovation and flags. A posterior mean can lie between modes; covariance does not prove that the correct mode is retained.

## Measurement and motion assumptions

The demonstration is **stop and measure**: 401 frequency points at 0.05 seconds per point require 20.05 seconds per stationary scan, excluding overhead. Motion increments represent travel between scan locations, and timestamps count scan budgets; transfer/travel time is not simulated. The field is fixed during each scan. This prototype cannot claim continuous vehicle tracking at that acquisition rate.

The fictional environment and 5 m map grid share one analytic field model. The sensor samples the continuous formula; the matcher interpolates its gridded map. A configurable 0.65 µT likelihood floor models independent map error phenomenologically, but no separate correlated survey error is injected. This favorable shared-model benchmark is not measured-map validation.

Motion measurements use per-step bias `[+0.65, -0.40]` m plus 0.35 m Gaussian noise per coordinate. The baseline integrates these increments. The particle matcher adds 1.5 m process spread per coordinate per step and does not estimate bias explicitly. These are displacement-level inertial surrogates, not an accelerometer/gyroscope INS. The baseline starts at the exact supplied fix; magnetic tracking samples an initial cloud around it. Results depend on map gradients, initial cloud, route, noise and tuning.

The scalar measurement leaves instantaneous position ambiguity along equal-field contours. Motion history and the starting region can reduce that ambiguity, but there is no unique-position or convergence guarantee. Orientation uncertainty, changing altitude, magnetic distortion and map age are excluded. The NV model retains v0.1's strain, sign and temperature-proxy limitations.

## Integrity and uncertainty

Measurement likelihood combines fitted field variance, a minimum measurement-noise floor and configured map variance. Gates skip corrections for sensor rejection, invalid estimates, low map support, a flat predicted map or a large innovation. Map samples outside the grid return NaN; particles are neither clamped nor reset. If most particles leave the map, prediction continues with `insufficient_map_support` and no magnetic update. Boundary warnings can accompany an otherwise usable update.

These gates are heuristics, not certified integrity protection. A consistent wrong map or an in-range disturbance can still be accepted. Particle covariance and sample spread are conditional on the model and finite cloud; multimodal ambiguity, particle loss and unmodeled errors can make them overconfident. No spoofing-detection or navigation-safety claim is made.

## Benchmark cases

Five nominal seeds `[17, 3, 11, 29, 47]` run 60 scans each. Seed 17 additionally runs:

- Dropouts: no magnetic updates during epochs 20–29.
- Interference: corrupted photon-count windows at epochs 20–24, tested through the ODMR fit gates.
- Flat map: constant 60 µT field, where magnetic localization should provide no correction.

All seeds and cases are retained in `benchmark.json`, including failures and regressions. No percentage improvement is promised outside these fixtures. Flat-map behavior illustrates that sensing alone cannot locate a vehicle without informative spatial structure.

Primary method references: Doucet and Johansen, *A Tutorial on Particle Filtering and Smoothing*, https://www.stats.ox.ac.uk/~doucet/doucet_johansen_tutorialPF.pdf ; SciPy `RegularGridInterpolator`, https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RegularGridInterpolator.html . Sensor references are in `SENSOR_PIPELINE.md`. No third-party source code was incorporated.

## Next milestone

v0.3 added a separate direct-measurement bridge to the gravity FusionEKF. v0.4 adds exported-data ingestion, described in IMPORT_WORKFLOW.md. Representative measured ODMR scans and surveyed fixed-axis maps are needed before hardware or navigation performance claims.

No redistribution license is granted here; dependency licenses remain separate.
