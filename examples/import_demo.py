"""Run the bundled synthetic CSV import/replay without ground-truth input."""
from pathlib import Path
import html
import json
import sys
import tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rq_sensing.import_data import load_dataset
from rq_sensing.import_cli import run_imported


def main():
    root = Path(__file__).resolve().parents[1]
    inputs, output = root / 'import_inputs', root / 'import_output'
    data = load_dataset(inputs / 'manifest.json')
    audit = run_imported(data, inputs / 'motion.jsonl', inputs / 'initialization.json', output,
                         inputs / 'toy_gravity_map.json')
    with tempfile.TemporaryDirectory() as tmp:
        again = run_imported(data, inputs / 'motion.jsonl', inputs / 'initialization.json', tmp,
                             inputs / 'toy_gravity_map.json')
    error = float(np.max(np.abs(np.asarray(audit['final_state']['metadata']['covariance']) -
                               np.asarray(again['final_state']['metadata']['covariance']))))
    assert audit['final_state']['values'] == again['final_state']['values'] and error == 0.
    verification = {'repeat_final_state_identical': True, 'repeat_covariance_max_difference': error,
                    'fixture_origin': 'synthetic', 'measured_accuracy_validated': False}
    (output / 'reproducibility.json').write_text(json.dumps(verification, indent=2))
    estimates = json.loads((output / 'estimates.json').read_text())
    rows = []
    accepted = [r['estimate'] for r in estimates if r['estimate']['accepted']]
    fig, ax = plt.subplots(figsize=(9, 4), layout='constrained')
    ax.errorbar([r['timestamp_s'] for r in accepted], [r['axial_magnitude_ut'] for r in accepted],
                yerr=[r['field_std_ut'] for r in accepted], marker='o', capsize=5)
    ax.set(xlabel='Scan completion time (s)', ylabel='Fixed-axis magnitude (µT)',
           title='Synthetic exported CSV scans • reported 1σ uncertainty')
    ax.grid(alpha=.25)
    fig.savefig(output / 'imported_scans.png', dpi=150)
    plt.close(fig)
    for r in estimates:
        e = r['estimate']
        field = f"{e['axial_magnitude_ut']:.4f}" if e['accepted'] else 'Rejected'
        sigma = f"{e['field_std_ut']:.4f}" if e['accepted'] else '—'
        rows.append(f"<tr><td>{r['sequence']}</td><td>{field}</td><td>{sigma}</td><td>{html.escape(', '.join(e['flags']) or 'Accepted')}</td></tr>")
    report = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RelativisticQ-PNT v0.4</title>
<style>body{{background:#081424;color:#d9e6f0;font:17px system-ui;max-width:1000px;margin:45px auto;padding:0 22px;line-height:1.6}}h1,h2{{color:#4bd4e5}}a{{color:#6ee2eb}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #304558;text-align:left}}img{{width:100%;border-radius:12px}}.card{{padding:24px;background:#112638;border-radius:12px}}code{{overflow-wrap:anywhere}}</style>
<h1>RelativisticQ-PNT v0.4.0</h1><p>by Christina Holt</p><h2>Exported-data import &amp; replay</h2>
<div class="card"><strong>Synthetic fixture, not measured hardware data.</strong><p>Three raw-count CSV scans and a fictional magnetic grid passed the import contract. The map and scans share the same synthetic environment; this does not test independent-survey errors. Toy gravity aiding and trusted stationary corrections are retained from v0.3.</p></div>
<p>{audit['scans_accepted']} / {audit['scans_total']} scans accepted · {audit['magnetic_updates_used']} magnetic updates used · {audit['state_snapshots']} state snapshots · repeat final state and covariance identical.</p>
<img src="imported_scans.png" alt="Three simulated scan estimates with supplied calibration uncertainty">
<table><tr><th>Scan</th><th>Magnitude (µT)</th><th>Reported std (µT)</th><th>Fit flags</th></tr>{''.join(rows)}</table>
<h2>What changed</h2><p>Explicit unit conversion, acquisition timing, fixed-axis compatibility, calibration terms, rectangular-map validation and SHA-256 provenance. Exported magnetic measurements feed the existing local six-state filter once each.</p>
<h2>Inspect the evidence</h2><p><a href="audit.json">Import audit</a> · <a href="estimates.json">Fit estimates</a> · <a href="status.json">Update decisions</a> · <a href="navigation_states.jsonl">State snapshots</a> · <a href="reproducibility.json">Repeat check</a> · <a href="../import_inputs/manifest.json">Input manifest</a></p>
<h2>Next with measured data</h2><p>Supply equal-dwell raw photon counts, independently surveyed fixed-axis magnitude maps and explicit calibration/timing records. Origins, stationarity and map independence are user declarations. The adapter does not verify them. A fit acceptance does not validate hardware accuracy, systematic errors, attitude or navigation integrity.</p></html>'''
    (output / 'report.html').write_text(report)
    print(json.dumps({'output': str(output), **verification, 'scans_accepted': audit['scans_accepted'],
                      'magnetic_updates_used': audit['magnetic_updates_used']}, indent=2))


if __name__ == '__main__': main()
