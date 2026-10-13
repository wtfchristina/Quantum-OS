# RelativisticQ (v0.3): Quantum-Aided Inertial Navigation Pipeline

[![CI](https://img.shields.io/badge/tests-32%20passing-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/status-simulation--first%20v0.3-blue.svg)]()
[![Domain](https://img.shields.io/badge/domain-GPS--denied%20%2F%20contested%20PNT-black.svg)]()

RelativisticQ is an open-source, simulation-first software pipeline that connects **nitrogen-vacancy (NV) diamond center magnetometry** and **gravity anomaly field aiding** directly to an integrated inertial navigation filter.

The engine models the complete signal chain—from raw optical resonance spectra down to full state vector estimation ($\mathbf{p}, \mathbf{v}, \mathbf{b}_a$) under GPS-denied and contested operating environments.

---

## Benchmark Performance (v0.3)

Across 5 nominal Monte Carlo simulation runs evaluating stop-and-measure trajectories, fusing gravity gradients and NV-magnetic field observations delivered a **~66% reduction in position RMSE** compared to standalone inertial estimation with identical stationary zero-velocity updates.

| Configuration Mode | Mean Position RMSE | Velocity RMSE | Filter State |
| :--- | :--- | :--- | :--- |
| **Inertial Only (Baseline + ZUPT)** | 9.59 m | Nominal | Stable |
| **Coupled Gravity + NV-Magnetic Aiding** | **3.27 m** | **Reduced** | **Converged** |
| *Open-Loop (No Stationary Aiding)* | *Diverged* | *Unbounded* | *Edge Failure Documented* |

> **Engineering Disclaimer:** These benchmarks represent algorithmic simulations using synthetic geophysical maps and stop-and-measure trajectories. They do not constitute empirical hardware accuracy claims.

---

## Architectural Signal Flow


### Core Features

- **Spectra to State Vector:** Processes raw synthetic photon counts, fits Lorentzian/Gaussian ODMR resonances, extracts directional magnetic field vectors, and injects measurements into state matrices.
- **Multi-Sensor Fusion:** Jointly estimates position, velocity, and accelerometer sensor bias while compensating for localized field anomalies.
- **Deterministic Replay:** Sensor-only replay utility that bit-accurately reproduces live fused filter states from archived telemetry runs.
- **Honest Edge Characterization:** Includes documented divergence failure cases to analyze filter stability limits when external aiding or zero-velocity constraints are omitted.
- **Verified Codebase:** 32 comprehensive unit and integration tests covering math kernels, resonance fit routines, and covariance propagation.

---

## Quickstart & Deterministic Replay

### Prerequisites

Ensure you have a modern Python environment (>= 3.10) with standard scientific computing libraries installed:

```bash
git clone [https://github.com/wtfchristina/relativistic-qpnt.git](https://github.com/wtfchristina/relativistic-qpnt.git)
cd relativistic-qpnt
pip install -r requirements.txt
