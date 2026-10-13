# Exported-data contract — v0.4.0

RelativisticQ-PNT • by Christina Holt

The full runnable example is `import_inputs/manifest.json`. Replace its CSVs and declarations to process exported data. Keep original instrument exports separately; the files here must first conform to this explicit contract. No arbitrary vendor CSV format is guessed.

## Scan CSV and metadata

Scan files have the exact header `frequency,counts`. At least 40 strictly increasing frequency points and nonnegative integer photon counts are required. Frequency units are explicitly `Hz`, `MHz` or `GHz`. Normalized fluorescence, background-subtracted values and unequal per-point dwell times are incompatible with the current Poisson-count estimator.

The manifest schema is `relativisticq-pnt.import.v1`. Common fields are:

| Field | Meaning |
| --- | --- |
| `frame` | Exactly `local_xy`; acceleration and map positions share this frame |
| `coordinate_system_id` | Identifier for one externally defined local coordinate frame |
| `axis_local_xyz` | Known fixed unit NV-axis vector in that frame |
| `timebase_id` | Identifier for one synchronized relative-time origin |
| `timebase_description` | Description of that origin and synchronization |
| `magnetic_map` | Grid source, observable, units, error and provenance |
| `scans` | Ordered nonoverlapping acquisition records |

Each scan record supplies `csv`, integer nonnegative `sequence`, `frequency_units`, `counts_kind: raw_photon_counts`, `equal_dwell_confirmed: true`, positive `dwell_s`, nonnegative `scan_start_s`, `scan_end_s`, `stationary_confirmed: true`, and a nonempty `stationarity_source`.

Duration must cover at least sample count × dwell; any extra acquisition overhead belongs inside the interval. Completion timestamps become packet timestamps. Scans must be ordered, nonoverlapping and from the same declared source/channel. Stationarity includes fixed position and fixed orientation for the entire scan; this is an external assertion, not a detector implemented here. The adapter records that assertion without proving it.

The `provenance` object requires `origin` (`synthetic` or `measured`), `source_id` and `description`. These are declarations. A SHA-256 digest records which bytes were used; it cannot prove sensor origin or survey independence. CSV paths must remain beneath the manifest folder; path traversal and escaping symlinks are rejected.

## Calibration and uncertainty

Every scan has a `calibration` object with:

| Field | Unit / use |
| --- | --- |
| `calibration_id` | Nonempty record identifier |
| `strain_mhz` | Nonnegative fixed strain splitting used in inversion |
| `strain_std_mhz` | Supplied nonnegative strain standard uncertainty |
| `half_splitting_std_mhz` | Supplied standard uncertainty in the frequency half-splitting |
| `systematic_std_ut` | Supplied nonnegative field-error floor |

All numeric fields are finite. Zero calibration uncertainty is an explicit caller assumption, not an inferred calibration certificate. For accepted fits, let `h` be fitted half splitting, `E` supplied strain, `r = sqrt(h²-E²)` and `γ = 0.02802495 MHz/µT`. The adapter combines:

```
σ_B² = σ_fit² + [E/(γ r) × σ_E]² + [h/(γ r) × σ_h]² + σ_systematic²
```

These are first-order terms assumed independent. `σ_h` is a calibration/reference contribution additional to photon fit error; do not enter the same fit uncertainty again. Common-mode center-frequency drift is not a splitting error and is not corrected by this field formula. The supplied systematic floor does not account for all unmodeled physics. Strong nonlinear strain uncertainty, correlated errors, drift, transverse fields or incompatible line shapes require independent characterization; do not interpret this number as validated coverage.

If the combined standard uncertainty exceeds `max(1 µT, 25% of magnitude)`, the scan is rejected with `high_calibration_uncertainty`; it emits no magnetic packet. Other estimator rejection flags are retained. Invalid input contracts or unusable zero-count baselines terminate the conversion with an input error rather than silently inventing an estimate.

Fusion subsequently combines this sensor variance (with a 100 nT minimum) with the map error declared in the manifest. Calibration is not applied again there.

## Reference magnetic map

Grid CSV header is exactly `x,y,value`. Row order may vary, but every pair in a complete rectangular x/y grid must appear exactly once. Each axis needs at least two points. Duplicates, holes, negative magnitude values and nonfinite entries are rejected. No scattered-point triangulation, extrapolation or missing-cell filling is performed.

The `magnetic_map` object requires `csv`, `position_units` (`m` or `km`), `field_units` (`nT`, `uT` or `T`), `observable: fixed_axis_magnitude`, `axis_local_xyz`, positive `error_std` in the same field units, `independence_statement`, and a `provenance` object. The map inherits the common coordinate-system identifier. `uT` is the JSON spelling of µT.

It must represent the magnitude along the sensor's known NV axis, not an arbitrary total-field or signed-anomaly map. Opposite signs of the same unit axis are compatible with a magnitude observable; other axes are rejected. Any projection from a geographic survey or field-vector data must be performed and documented separately. Actual survey uncertainty, interpolation error and correlation need independent evaluation; the scalar `error_std` is a likelihood assumption, not an independence test.

## Motion stream and initialization

Replay takes a separate JSONL stream and initialization JSON. Both must declare the same `timebase_id` and `coordinate_system_id` as the manifest. Initialization also supplies finite six-state `state`, symmetric positive-semidefinite `covariance` and `timestamp_s`; no ground truth is required. An externally supplied initial fix is still an assumption.

Every motion packet uses `frame: local_xy`, nonnegative strictly increasing integer sequence within its sensor channel, finite timestamp and exact payload keys. Packets are already in nondecreasing acquisition order. `metadata` repeats the two common identifiers.

| Sensor | Payload | Metadata / timing |
| --- | --- | --- |
| `imu` | `ax_mps2`, `ay_mps2` | `units: m/s^2`; strictly increasing prediction time |
| `stationary_velocity` | `vx_mps`, `vy_mps`, positive `noise_std_mps` | `units: m/s`, `stationarity_source: trusted_stop_signal`; same timestamp as current IMU epoch |
| `gravity` | `value`, positive `noise_std` | Legacy `observable: synthetic_scalar_gravity`, `units: toy_units`; same timestamp as current IMU epoch and explicit toy map |

Scan completion must match an IMU prediction timestamp exactly. The adapter does not silently shift, interpolate or backdate observations. Align source timebases and resample into filter epochs explicitly before replay. Scan starts must not precede initialization. Ties are processed in the existing order: motion prediction and optional stationary/gravity updates, then magnetic update. Imported magnetic packets are generated from the scan records; do not place extra magnetic packets in the motion stream.

Without `--toy-gravity-map`, only IMU and trusted stationary-velocity packets are accepted. Physical gravimeter units such as mGal are rejected; they need a separately implemented physical observable and compatible map. The toy-gravity option is for the retained simulation, not for surveyed gravity ingestion.

## Outputs and exit codes

`validate` checks the file/data contract and does not fit spectra. `convert` writes `estimates.json`, accepted `quantum_magnetic.jsonl`, internal `magnetic_map.npz` and `audit.json`. `replay` adds merged `sensor_inputs.jsonl`, `navigation_states.jsonl` and per-observation `status.json`. Fit acceptance and fusion usage are separate decisions: boundaries, flat gradients and innovation gates may prevent use of an accepted field estimate.

Exit 0 means contract validation or a completed conversion/replay with at least one accepted fit. Exit 2 means an input/contract error. Exit 3 means valid processing completed with no accepted fits; rejection records are still written. A 0 exit does not imply every scan was accepted or every observation used by fusion.

Outputs record source hashes, user-declared origins, calibration terms, map uncertainty and false hardware/navigation-validation flags. The bundled repeat check tests deterministic software replay, not physical accuracy.
