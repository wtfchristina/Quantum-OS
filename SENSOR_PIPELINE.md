# RelativisticQ-PNT — retained sensor/localization subsystem

A runnable, simulation-first NV-center magnetometer signal-processing prototype.

**Sensor subsystem status:** synthetic-data research prototype. No physical sensor is included or controlled. This release estimates **|B parallel to one NV axis|**, not total field magnitude, signed field, a 3D field vector or position. This document describes the retained sensor subsystem; see LOCALIZATION_PIPELINE.md for v0.2 map matching, and IMPORT_WORKFLOW.md for v0.4 data ingestion.

## Start in five minutes

Install Python 3.10 or newer. Extract the ZIP, open a terminal in this folder:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python examples/demo.py
python -m unittest discover -s tests -v
```

Open `demo_output/report.html` in a browser. A pre-generated report is already included, so you can view the demo before installing anything. The demo creates plots, raw photon counts, per-scan estimates and numerical metrics.

## What it does

1. Generates two continuous-wave ODMR fluorescence dips for an axial NV model.
2. Applies a temperature-dependent center shift, calibrated strain splitting, linewidth, baseline slope and seeded Poisson photon noise.
3. Fits the dip pair using weighted nonlinear least squares with multiple initial guesses, including smoothed dip candidates.
4. Recovers axial field magnitude from the fitted splitting and calibrated strain.
5. Returns local uncertainty and integrity flags; rejected scans return `null` for field and uncertainty.
6. Exports CSV input, JSON results, PNG plots and an HTML report.

The default demo uses 40 successive scans with a 50–80 µT axial field and a 4 K temperature ramp. Each 401-point scan has 0.05 s dwell per point: **20.05 seconds per scan**, ignoring hardware overhead. Field and temperature are assumed constant during a scan. The field trace is a sensing demonstration, not a vehicle trajectory. Fit latency is separate from acquisition time.

## Process your own exported scan

CSV must contain `frequency_mhz,counts` in its header, at least 40 rows, increasing frequency, and raw nonnegative photon counts acquired with equal dwell time at every point. No background subtraction or normalized fluorescence is supported by this count-noise model.

```bash
python -m rq_sensing.cli demo_output/sample_spectrum.csv --dwell-s 0.05 --strain-mhz 0.15 --output my_estimate.json
```

After installation, `rq-sensing` invokes the same command. Exit codes: 0 accepted, 2 invalid input, 3 rejected fit. A successful fit is not proof that an arbitrary real spectrum satisfies the physics model. Real sensor characterization is required.

Python API:

```python
from rq_sensing import SimulatedNVSensor, estimate_field
sensor = SimulatedNVSensor(seed=7)
scan = sensor.acquire(field_ut=65, temperature_k=295)
result = estimate_field(scan, strain_mhz=sensor.config.strain_mhz)
print(result.to_dict())
```

`SensorSource` is a protocol for a future acquisition adapter. `Spectrum` accepts exported scans now; there is no implemented instrument driver. Every input and output frequency is MHz; field is µT; linewidth is FWHM; dwell and timestamps are seconds.

## Physics and assumptions

For an axial field, the simplified ground-state model is

```
D(T) = 2870 MHz - 0.0742 MHz/K * (T - 293.15 K)
f_minus, f_plus = D(T) ± sqrt((gamma * B_parallel)^2 + E^2)
gamma = 0.02802495 MHz/µT
|B_parallel| = sqrt(half_splitting^2 - E^2) / gamma
```

The spectrum is a sloping fluorescence baseline multiplied by two phenomenological Lorentzian dips. Strain E is fixed by supplied calibration. B and E cannot be independently identified from one splitting measurement. Opposite axial signs give identical spectra in this model. The midpoint-derived temperature is only a **proxy** conditional on known D at the reference temperature: other common-mode frequency shifts are indistinguishable from temperature.

The simulator restricts temperature to 280–330 K and |axial field| to 1000 µT, and requires coverage of both resonances. The default scan covers only a narrower field range. These are prototype guardrails, not validated instrument operating specifications. Strain temperature dependence, transverse-field mixing, four NV orientations, hyperfine lines, microwave/laser dynamics, dip-strength changes due to state mixing, instrument response, correlated technical noise and frequency calibration errors are omitted. Dip strengths are phenomenological even when strain is nonzero.

Uncertainty uses the fitted Jacobian and a Poisson-weighted residual covariance, inflated when reduced chi-square exceeds one. It excludes strain calibration uncertainty, frequency reference uncertainty and model bias. Near zero field, unresolved dip overlap and the strain floor invalidate this inversion. Quality gates are heuristic: low contrast, unresolved/undersampled lines, scan-edge fits, excessive residuals, singular fitting, high uncertainty and model-range checks. They do not constitute a certified integrity monitor or a spoofing detector.

## Validation and reproducibility

Tests cover analytic splitting, sign ambiguity, noiseless inversion with strain, temperature drift, seeded repeatability, malformed inputs and rejection of flat, unresolved and mismatched spectra. See `VALIDATION.md` for this build's observed results. Simulation and estimator share a forward model; synthetic accuracy establishes software consistency, not physical accuracy. Dependencies are bounded in `pyproject.toml`; exact versions used here are recorded in `localization_output/environment.json`. Other versions within those bounds have not been tested.

Primary technical references (no third-party source code incorporated):

- Rondin et al., *Magnetometry with nitrogen-vacancy defects in diamond*, https://arxiv.org/abs/1311.5214
- Acosta et al., *Temperature dependence of the nitrogen-vacancy magnetic resonance in diamond*, https://arxiv.org/abs/0911.3938 ; associated erratum https://doi.org/10.1103/PhysRevLett.106.209901
- NIST, *Nitrogen-Vacancy (NV) Center Magnetometry*, https://www.nist.gov/noac/technology/magnetic-and-electric-fields/nv-center-magnetometry

## Next versions

- v0.2: simulated magnetic maps and localization with explicit axis/orientation assumptions.
- v0.3: integrate with the gravity-aided navigation stack after reviewing its interfaces and benchmarks.
- Hardware milestone: import representative measured ODMR scans, characterize systematics, then implement an instrument-specific adapter.

The current release embeds selected original gravity modules and integrates them through a wrapper; see THIRD_PARTY.md. No third-party redistribution license is granted by this package; licensing terms can be selected separately. NumPy, SciPy and Matplotlib retain their own licenses.
