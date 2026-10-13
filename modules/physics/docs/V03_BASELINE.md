# RelativisticQ-PNT — retained v0.3.0 baseline

**New:** the NV-center sensing pipeline now feeds the six-state `FusionEKF` from the existing gravity-aided-navigation v0.7.0 package. Gravity and magnetic observations update one position/velocity/accelerometer-bias state. A sensor-only JSONL replay reproduces the fused result without a true trajectory.

This is a synthetic local-navigation prototype. The default benchmark uses stationary ODMR scans, a known fixed sensor axis, fictional maps and a trusted external stop signal. All comparison modes receive the same noisy zero-velocity observations at stops. Hardware performance and global localization are unvalidated.

## View and run

Open `integrated_output/report.html` to see the pre-generated integrated demo and all eight benchmark cases. Extract the ZIP and open a terminal in this folder with Python 3.10+:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python examples/integrated_demo.py
python -m unittest discover -s tests -v
```

Run the full five-seed campaign plus dropout, interference and flat-map cases:

```bash
python examples/integrated_demo.py --benchmark
```

Disable stationary aiding to inspect the failure-prone local-filter regime; outputs go to a separate folder:

```bash
python examples/integrated_demo.py --benchmark --no-stationary-aiding
```

The initial campaign without stationary aiding is retained in `integrated_output/no_stationary_aiding_benchmark.json` and summarized in the report. Several runs diverged, including a nominal seed where fusion was worse than inertial-only integration. Stationary aiding supplies additional information; its benefits must not be attributed to quantum sensing alone.

## What's integrated

The upstream `FusionEKF`, `FieldObservation`, planar propagation, IMU simulator, synthetic gravity map and `SensorPacket` modules are bundled byte-for-byte under `rq_sensing._gravity_v07`. Source hashes are in `GRAVITY_SOURCE.json`; original MIT terms are preserved. This standalone package does not change the original gravity release or replace its installed namespace. See `THIRD_PARTY.md`.

The wrapper in `rq_sensing/fusion_bridge.py`:

- Converts fitted axial magnitude and standard error from µT to nT.
- Adapts the fixed-axis magnetic magnitude grid to the upstream scalar-field value/gradient API.
- Combines fitted variance, a 100 nT minimum sensor-error floor and a 650 nT map-error floor.
- Checks magnetic packet frame, units, observable, completion timestamp, sequence and numeric payload.
- Skips rejected, stale, future, repeated, out-of-order, out-of-map and grossly inconsistent magnetic measurements.
- Adds an optional noisy zero-velocity update when a trusted external stationary signal is supplied.
- Exports position, velocity, bias and six-state covariance in the existing packet container.

The filter state is `[x_m, y_m, vx_mps, vy_mps, bax_mps2, bay_mps2]`. The integration updates the filter with raw fitted field estimates. It does **not** also feed the v0.2 particle-matcher position estimate, which would reuse the same measurement. The particle matcher remains available as a separate tool.

## Replay the included sensor stream

```bash
python -m rq_sensing.replay_fusion integrated_output/sensor_inputs.jsonl --magnetic-map integrated_output/magnetic_map.npz --gravity-map integrated_output/gravity_map.json --initialization integrated_output/fusion_initialization.json --output replayed_states.jsonl
```

Replay imports IMU, trusted stationary-velocity, synthetic-gravity and quantum-magnetic packets in acquisition order. It emits navigation-state JSONL and a separate status JSON. Initial position/covariance and both maps are supplied independently. The stream contains no ground-truth positions. The demo verifies its replayed final fused state against the live simulation.

This extends the generic upstream packet container with a new `quantum_magnetic` sensor type. It does not implement an upstream network gateway, ROS2 driver or hardware adapter for that type. The new replay tool is the supported consumer here.

## Benchmark and cadence

Default: 40 waypoints, a 0.5 s planar IMU timestep, 10 s transfers and 21 s pauses, totaling 1,230 s. Each transfer accelerates for five seconds and decelerates for five seconds, ending at rest. Each pause permits a 401-point ODMR scan at 0.05 s dwell (20.05 s) plus 0.95 s overhead. Magnetic and gravity updates occur at the end of the pause. The simulator asserts that truth remains stationary during scans; no moving-sensor snapshot shortcut is used.

A trusted simulated stop signal permits a zero-velocity observation with 0.03 m/s Gaussian noise per coordinate at each pause end. It is an external assumption, not an implemented stationary detector. The same observed velocity is supplied to every mode:

| Mode key | Comparison meaning |
| --- | --- |
| `ins` | Planar IMU propagation with bias estimation and stationary velocity aiding; no field-map updates |
| `gravity` | Same baseline plus synthetic scalar gravity |
| `magnetic` | Same baseline plus fitted NV-axis magnetic magnitude |
| `fused` | Same baseline plus both scalar fields |

Every mode starts at the same exact supplied position and zero velocity. Its initial covariance represents an assumed 18 m position standard deviation, 0.1 m/s velocity standard deviation and 0.03 m/s² bias standard deviation. Independent deterministic streams generate IMU errors, gravity noise, photon counts and stationary velocity noise. All modes within a case share these realizations. `uncompensated_dead_reckoning` is also retained in the track but is not the default baseline reported as `ins`.

The source gravity IMU model uses 0.03 m/s² per-sample acceleration noise, 0.0008 m/s²/√s bias random walk and 0.015 m/s² initial bias standard deviation. It models acceleration in the local map frame. There is no attitude/gyro estimation, strapdown mechanization, Earth rotation, altitude or GNSS.

Gravity observations come from the upstream Gaussian-anomaly class with small-scale fictional anomaly parameters saved in `gravity_map.json`. Units are explicitly **toy scalar gravity units**, not calibrated gravimeter or gravity-gradient hardware units. The magnetic environment is the v0.2 fixed-axis scalar field, sampled continuously by the simulator and interpolated from a 5 m grid by the filter. The map floor is a likelihood assumption; independent correlated survey errors are not simulated.

## Results and limits

See `VALIDATION.md` for every run, including regressions. RMSE is computed over all 0.5 s propagation epochs, including transfers, pauses and scan-end corrections. End-of-scan updates improve only the current epoch; past history is not smoothed. A nominal run with small final error can still have larger route-wide errors.

An EKF is a local approximation. Nonlinear maps, ambiguous contours, weak gradients, wrong orientation and long aiding gaps can cause it to lose the true position. Boundary and innovation gates do not implement global relocalization or guaranteed integrity. Covariance is conditional on the model and can be overconfident. Replay does not perform out-of-sequence smoothing; stale observations are skipped and malformed or duplicate replay streams fail explicitly. Gravity replay units currently support this synthetic scalar fixture only.

NV sign ambiguity, fixed-strain assumptions, temperature-proxy limitations and photon-noise uncertainty are unchanged; see `SENSOR_PIPELINE.md`. Temperature is held constant during each scan and changes between scans. The scalar magnetic map must match the sensor's known axis magnitude; the original gravity package's signed anomaly map or an arbitrary total-field map cannot be substituted without an explicit background/orientation model. This release supplies no instrument driver, surveyed-map ingestion workflow or calibration detector.

## Retained tools

- Sensor-only demo: `python examples/demo.py` → `demo_output/report.html`.
- Particle localization demo: `python examples/localization_demo.py` → `localization_output/report.html`.
- Raw-count CSV fitting: `python -m rq_sensing.cli demo_output/sample_spectrum.csv --dwell-s 0.05 --output estimate.json`.
- Sensor and v0.2 particle-matching documentation: `SENSOR_PIPELINE.md`, `LOCALIZATION_PIPELINE.md`.

## Technical references and next work

The reviewed gravity package is the implementation source. Kalman covariance methodology: NASA, *Navigation Filter Best Practices*, https://ntrs.nasa.gov/api/citations/20250002787/downloads/20250002787.pdf . Stationary-update context: https://ntrs.nasa.gov/api/citations/19860002190/downloads/19860002190.pdf . NV sensor references are retained in SENSOR_PIPELINE.md. References explain the methods; they do not validate this software.

Next milestone: ingest representative measured ODMR scans and independently surveyed maps, characterize calibration/systematics, and add a documented sensor-specific hardware adapter. Broader initial-position, map-error and dropout campaigns should precede real navigation claims.

No redistribution license is selected for new sensing/integration code. The embedded original gravity modules retain their MIT license.
