# v0.4.0 — 2026-10-06

RelativisticQ-PNT • by Christina Holt

- Added manifest-based exported ODMR CSV batch ingestion with explicit frequency units, raw-count/equal-dwell requirements and acquisition interval checks.
- Added complete rectangular fixed-axis magnetic-map CSV ingestion with spatial/field conversion, axis compatibility and explicit map-error assumptions.
- Preserved declared measured/synthetic origins, calibration identifiers and SHA-256 source provenance.
- Added first-order supplied calibration/systematic uncertainty terms and rejection for excessive combined uncertainty.
- Added validated imported-data replay with explicit timebase/frame identifiers, source initialization and auditable update decisions.
- Added CLI validate/convert/replay commands, examples, synthetic fixtures and an offline HTML report with deterministic repeat check.
- Retained existing distribution/namespace/CLI compatibility and byte-preserved selected gravity source modules.
- Applied RelativisticQ-PNT display branding and Christina Holt author metadata.

The fixture is synthetic and the map is not independent of the scan simulator. This release adds no live driver, physical gravimeter import or new navigation-accuracy claim. Existing v0.3 benchmark outputs remain historical evidence.

# v0.3.0 — 2026-10-06

- Connected fitted NV magnetic measurements to the existing gravity v0.7 FusionEKF and packet schema through a new adapter.
- Added explicit µT → nT conversion, fixed-axis grid gradients, uncertainty floors and sequence/time/unit checks.
- Bundled five original gravity source modules with hashes and MIT license under a private namespace.
- Added stop/go planar IMU simulation, scalar gravity measurements and physically stationary ODMR acquisitions.
- Added optional trusted-stop zero-velocity updates, provided equally to every comparison mode.
- Added sensor-only JSONL replay, initialized independently of truth, verified against the live final fused state.
- Added eight integrated campaign cases, exported raw scans/maps/packets/states and HTML/PNG reports.
- Retained the initial no-stationary-aiding campaign, including divergence and regression cases.
- Expanded verification from 16 to 32 unit/integration tests; retained standalone sensor and particle-localization tools.

The default benchmark now uses an acceleration/bias-state filter and trusted stationary observations. Its metrics are not directly comparable with v0.2's displacement-level particle-matching benchmark.
