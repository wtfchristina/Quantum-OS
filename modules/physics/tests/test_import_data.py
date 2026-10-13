"""Contract, units, failure handling and end-to-end imported replay checks."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
from rq_sensing.import_data import load_dataset, write_conversion, sha256
from rq_sensing.import_cli import prepare_motion, run_imported, main

ROOT = Path(__file__).resolve().parents[1]


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'inputs'
        shutil.copytree(ROOT / 'import_inputs', self.path)
        self.manifest = json.loads((self.path / 'manifest.json').read_text())

    def save(self):
        (self.path / 'manifest.json').write_text(json.dumps(self.manifest))
        return self.path / 'manifest.json'

    def load(self):
        return load_dataset(self.save())

    def rejects(self):
        with self.assertRaises(ValueError): self.load()

    def test_units_and_source_hashes(self):
        d = self.load()
        self.assertAlmostEqual(d.scans[0].spectrum.frequency_mhz[0], 2863.)
        self.assertEqual(d.map_metadata['error_std_ut'], .65)
        self.assertEqual(d.scans[0].metadata['csv_sha256'], sha256(self.path / 'scan_000.csv'))
        self.assertEqual(d.map_metadata['origin'], 'synthetic')
        old = np.load(ROOT / 'integrated_output/magnetic_map.npz')
        np.testing.assert_allclose(d.magnetic_map.axial_magnitude_ut, old['axial_magnitude_ut'], atol=1e-9)

    def test_map_coordinate_conversion_and_order(self):
        p = self.path / 'reference_map.csv'
        a = np.loadtxt(p, delimiter=',', skiprows=1)
        a[:, :2] /= 1000
        np.savetxt(p, a[::-1], delimiter=',', header='x,y,value', comments='')
        self.manifest['magnetic_map']['position_units'] = 'km'
        d = self.load()
        old = np.load(ROOT / 'integrated_output/magnetic_map.npz')
        np.testing.assert_allclose(d.magnetic_map.x_m, old['x_m'])
        np.testing.assert_allclose(d.magnetic_map.axial_magnitude_ut, old['axial_magnitude_ut'], atol=1e-9)

    def test_wrong_axis(self):
        self.manifest['magnetic_map']['axis_local_xyz'] = [1, 0, 0]
        self.rejects()

    def test_opposite_axis_same_magnitude(self):
        self.manifest['magnetic_map']['axis_local_xyz'] = [0, 0, -1]
        self.assertEqual(len(self.load().scans), 3)

    def test_nonunit_axis(self):
        self.manifest['axis_local_xyz'] = [0, 0, 2]
        self.rejects()

    def test_total_field_map(self):
        self.manifest['magnetic_map']['observable'] = 'total_field'
        self.rejects()

    def test_missing_independence_statement(self):
        del self.manifest['magnetic_map']['independence_statement']
        self.rejects()

    def test_measured_origin_remains_declared(self):
        self.manifest['scans'][0]['provenance']['origin'] = 'measured'
        self.assertTrue(self.load().scans[0].metadata['origin_is_user_declared'])

    def test_invalid_origin(self):
        self.manifest['scans'][0]['provenance']['origin'] = 'unknown'
        self.rejects()

    def test_unsupported_units(self):
        self.manifest['scans'][0]['frequency_units'] = 'kHz'
        self.rejects()

    def test_incomplete_grid(self):
        p = self.path / 'reference_map.csv'
        rows = p.read_text().splitlines()
        p.write_text('\n'.join(rows[:-1]))
        self.rejects()

    def test_duplicate_coordinate(self):
        p = self.path / 'reference_map.csv'
        rows = p.read_text().splitlines()
        rows[-1] = rows[-2]
        p.write_text('\n'.join(rows))
        self.rejects()

    def test_negative_map_value(self):
        p = self.path / 'reference_map.csv'
        rows = p.read_text().splitlines()
        x, y, _ = rows[1].split(',')
        rows[1] = f'{x},{y},-1'
        p.write_text('\n'.join(rows))
        self.rejects()

    def test_raw_counts_contract(self):
        self.manifest['scans'][0]['counts_kind'] = 'normalized_fluorescence'
        self.rejects()

    def test_fractional_counts(self):
        p = self.path / 'scan_000.csv'
        rows = p.read_text().splitlines()
        rows[1] = rows[1].split(',')[0] + ',3.5'
        p.write_text('\n'.join(rows))
        self.rejects()

    def test_stationarity_requires_true_boolean(self):
        for val in (False, 'true', 1):
            self.manifest['scans'][0]['stationary_confirmed'] = val
            self.rejects()

    def test_too_short_scan(self):
        self.manifest['scans'][0]['scan_start_s'] = self.manifest['scans'][0]['scan_end_s'] - 1
        self.rejects()

    def test_overlapping_scans(self):
        self.manifest['scans'][1]['scan_start_s'] = 0
        self.rejects()

    def test_duplicate_sequence(self):
        self.manifest['scans'][1]['sequence'] = 0
        self.rejects()

    def test_boolean_sequence(self):
        self.manifest['scans'][0]['sequence'] = True
        self.rejects()

    def test_nonfinite_and_negative_calibration(self):
        self.manifest['scans'][0]['calibration']['strain_std_mhz'] = -1
        self.rejects()
        self.manifest['scans'][0]['calibration']['strain_std_mhz'] = float('nan')
        self.rejects()

    def test_path_traversal(self):
        self.manifest['scans'][0]['csv'] = '../outside.csv'
        self.rejects()

    def test_calibration_inflates_uncertainty(self):
        d = self.load()
        e, p, terms = d.scans[0].fit()
        self.assertTrue(e.accepted)
        self.assertGreater(e.field_std_ut, terms['fit_std_ut'])
        self.assertAlmostEqual(e.field_std_ut, np.linalg.norm(list(terms.values())))
        self.assertAlmostEqual(p.values['field_std_nt'], e.field_std_ut * 1000)
        self.assertEqual(p.metadata['calibration_id'], 'synthetic-model-v1')
        self.assertAlmostEqual(p.metadata['scan_start_s'], d.scans[0].start_s)

    def test_large_calibration_uncertainty_rejects(self):
        self.manifest['scans'][0]['calibration']['systematic_std_ut'] = 100
        e, p, _ = self.load().scans[0].fit()
        self.assertFalse(e.accepted)
        self.assertIsNone(p)
        self.assertIn('high_calibration_uncertainty', e.flags)

    def test_flat_scan_retains_rejection_without_packet(self):
        p = self.path / 'scan_000.csv'
        a = np.loadtxt(p, delimiter=',', skiprows=1)
        a[:, 1] = 100000
        np.savetxt(p, a, delimiter=',', header='frequency,counts', comments='')
        e, p, _ = self.load().scans[0].fit()
        self.assertFalse(e.accepted)
        self.assertIsNone(p)

    def test_conversion_audit(self):
        output = Path(self.temp.name) / 'convert'
        estimates, packets, audit = write_conversion(self.load(), output)
        self.assertEqual(len(packets), 3)
        self.assertFalse(audit['hardware_accuracy_validated'])
        self.assertFalse(audit['map_independence_verified'])
        self.assertTrue(audit['provenance_is_user_declared'])
        self.assertEqual(len((output / 'quantum_magnetic.jsonl').read_text().splitlines()), 3)

    def motion(self):
        return self.path / 'motion.jsonl', self.path / 'initialization.json', self.path / 'toy_gravity_map.json'

    def test_truth_free_replay_is_repeatable(self):
        d = self.load()
        motion, init, gravity = self.motion()
        first = run_imported(d, motion, init, Path(self.temp.name) / 'first', gravity)
        second = run_imported(d, motion, init, Path(self.temp.name) / 'second', gravity)
        self.assertEqual(first['final_state'], second['final_state'])
        self.assertEqual(first['magnetic_updates_used'], 3)
        self.assertFalse(first['navigation_accuracy_measured'])
        self.assertNotIn('truth', motion.read_text())

    def test_timebase_mismatch(self):
        motion, init, gravity = self.motion()
        x = json.loads(init.read_text()); x['timebase_id'] = 'different'
        init.write_text(json.dumps(x))
        with self.assertRaises(ValueError): prepare_motion(self.load(), motion, init, gravity)

    def test_initialization_not_object(self):
        motion, init, gravity = self.motion()
        init.write_text("[]")
        with self.assertRaises(ValueError): prepare_motion(self.load(), motion, init, gravity)

    def test_motion_duplicate_rejected_before_fit(self):
        motion, init, gravity = self.motion()
        rows = motion.read_text().splitlines(); rows.insert(1, rows[0]); motion.write_text('\n'.join(rows))
        with self.assertRaises(ValueError): prepare_motion(self.load(), motion, init, gravity)

    def test_scan_end_requires_imu_epoch(self):
        self.manifest['scans'][0]['scan_end_s'] += .1
        motion, init, gravity = self.motion()
        with self.assertRaises(ValueError): prepare_motion(self.load(), motion, init, gravity)

    def test_physical_gravity_not_silently_accepted(self):
        motion, init, gravity = self.motion()
        rows = [json.loads(line) for line in motion.read_text().splitlines()]
        next(p for p in rows if p['sensor'] == 'gravity')['metadata']['units'] = 'mGal'
        motion.write_text('\n'.join(json.dumps(p) for p in rows))
        with self.assertRaises(ValueError): prepare_motion(self.load(), motion, init, gravity)

    def test_toy_gravity_needs_explicit_map(self):
        motion, init, _ = self.motion()
        with self.assertRaises(ValueError): prepare_motion(self.load(), motion, init)

    def test_magnetic_only_replay(self):
        motion, init, _ = self.motion()
        rows = [json.loads(line) for line in motion.read_text().splitlines()]
        motion.write_text('\n'.join(json.dumps(p) for p in rows if p['sensor'] != 'gravity'))
        audit = run_imported(self.load(), motion, init, Path(self.temp.name) / 'magnetic')
        self.assertEqual(audit['magnetic_updates_used'], 3)
        self.assertIsNone(audit['toy_gravity_map_sha256'])

    def test_wrong_motion_units(self):
        motion, init, gravity = self.motion()
        rows = [json.loads(line) for line in motion.read_text().splitlines()]
        rows[0]['metadata']['units'] = 'g'
        motion.write_text('\n'.join(json.dumps(p) for p in rows))
        with self.assertRaises(ValueError): prepare_motion(self.load(), motion, init, gravity)


if __name__ == '__main__': unittest.main()
