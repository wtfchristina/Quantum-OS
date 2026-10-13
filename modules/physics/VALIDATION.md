# v0.4 build validation — 2026-10-06

RelativisticQ-PNT • by Christina Holt

**67 unit/integration tests passed**: 32 retained tests plus 35 new ingestion/replay checks. The run log is `test_results.txt`.

New checks cover spatial/field/frequency unit conversion; scrambled grid order; axis/sign compatibility; map duplicates, holes and invalid magnitudes; source origin declarations/hashes; raw-count requirements; acquisition duration and overlap; sequence/type validation and malformed initialization; stationarity declarations; invalid calibration uncertainty; path traversal; rejected fits; unit/frame/timebase contracts; physical-gravity rejection; magnetic-only replay; and deterministic imported replay.

The complete synthetic import demo processed three CSV scans: **3 accepted fits, 3 magnetic updates used**. Two runs produced identical final state and covariance; `import_output/reproducibility.json` records the check. The source files are simulated counts and a fictional shared-model map, explicitly labeled synthetic. Calibration terms and map error are fixture assumptions. There was no independent sensor/map accuracy assessment.

The v0.4 wheel built and installed into an isolated target directory. Its installed import CLI validated the contract and replayed the fixture. The installed final state/covariance matched the source demo exactly. Package version, command metadata and embedded license were checked. All five selected original gravity module hashes still match `GRAVITY_SOURCE.json`.

The report figure was visually inspected and all local report links resolve. Dependency/runtime versions are recorded in `import_output/environment.json`. Byte-identical results across other dependency versions/platforms have not been established.

The historical v0.3 navigation campaign and its limitations are preserved in `docs/V03_VALIDATION.md` and `integrated_output/`. They were not rerun as a new v0.4 accuracy campaign. No measured scans, independent surveyed map, instrument driver, physical gravity observable, attitude estimator or certified integrity capability was supplied or validated here.
