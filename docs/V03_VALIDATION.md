# Build validation — 2026-10-06

32 unittest tests passed. Tests cover the retained NV and particle-matching pipelines plus unit conversion, packet identity/time checks, exact equivalence to the embedded FusionEKF update, covariance PSD, stationary-velocity updates, stationary acquisition, and sensor-only replay. The original selected gravity modules passed byte-hash verification.

All values below are route-wide position RMSE in meters. Every default comparison mode receives the same trusted simulated stop signal and noisy zero-velocity observations. All modes use the same IMU, gravity, photons and velocity-noise streams.

| Case | Seed | IMU + stationary | Gravity | Magnetic | Fused |
| --- | ---: | ---: | ---: | ---: | ---: |
| nominal | 17 | 4.84 | 4.94 | 4.63 | 3.75 |
| nominal | 3 | 10.01 | 4.42 | 5.30 | 2.97 |
| nominal | 11 | 12.06 | 6.94 | 4.08 | 3.33 |
| nominal | 29 | 7.05 | 6.41 | 4.55 | 3.10 |
| nominal | 47 | 13.98 | 5.45 | 5.64 | 3.20 |
| dropouts | 17 | 4.84 | 4.94 | 5.71 | 3.97 |
| interference | 17 | 4.84 | 4.94 | 5.16 | 3.81 |
| flat_magnetic | 17 | 4.84 | 4.94 | 4.84 | 4.94 |

Mean of five nominal per-run RMSE values: **9.59 m baseline vs 3.27 m fused**, a 65.9% reduction in this synthetic campaign. This is not pooled RMSE, a guarantee or a hardware accuracy claim. Fused mode improves over the baseline in all five nominal seeds. Gravity-only slightly regresses against baseline on seed 17; all results are retained.

The default seed 17 fused terminal error is 0.264 m, but its route-wide RMSE is 3.751 m and its maximum error is 11.938 m. Small terminal error must not be described as route-wide accuracy.

Five deliberate corrupted ODMR scans result in 35 of 40 magnetic updates in the interference case. Eight scheduled dropouts remove magnetic packets at epochs 12–19. Flat-map magnetic gradients give zero magnetic updates and reproduce the corresponding nonmagnetic modes.

A full nominal sensor-only replay matches the live final fused state to numerical tolerance (rtol 1e-12, atol 1e-10). The sensor stream contains acceleration, gravity, stationary velocity and NV fields, but no true trajectory. Inputs, initialized state/covariance and both maps are supplied separately. The retained sensor and particle-localization examples also run successfully.

## Retained diagnostic without stationary aiding

`integrated_output/no_stationary_aiding_benchmark.json` preserves the initial campaign. With 31-second aiding intervals, accelerometer bias and local-map ambiguity caused several filters to diverge; seed 47 fused RMSE was 11,636.64 m, worse than its 10,340.81 m inertial baseline. The default release adds a known-stop observation equally to all modes rather than removing those failed seeds. The default performance therefore depends on this additional information. This release has no global recovery algorithm and is not suitable for claims of assured continuous-motion navigation.

## Scope

Fictional shared-model maps, synthetic planar acceleration, fixed known axis, known initial position and trusted stationarity; no hardware, measured map, orientation uncertainty, real gravity units, atmosphere/Earth dynamics or calibrated integrity/coverage evaluation. The default benchmark is physically stationary during each 20.05-second scan and permits 0.95 seconds overhead. Sensor/map noise floors are modeling assumptions. Exact environment is in integrated_output/environment.json; source provenance is in GRAVITY_SOURCE.json.

The v0.3 wheel built and installed into an isolated target directory. Installed imports, short simulation/replay and the embedded MIT license were checked. The CLI replay of all 2,580 nominal sensor packets matches the final fused state by named state component. Report images exist; the integrated figure was visually inspected.
