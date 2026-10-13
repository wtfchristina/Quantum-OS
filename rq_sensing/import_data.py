"""Auditable exported-data adapter. It does not control or certify an instrument."""
from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import json
import math
import numpy as np
from .core import Spectrum, estimate_field, GAMMA_MHZ_PER_UT
from .navigation import MagneticMap
from .fusion_bridge import nv_packet

SCHEMA = 'relativisticq-pnt.import.v1'
FREQUENCY_SCALE = {'Hz': 1e-6, 'MHz': 1., 'GHz': 1000.}
FIELD_SCALE = {'nT': .001, 'uT': 1., 'T': 1e6}
POSITION_SCALE = {'m': 1., 'km': 1000.}


def number(value, name, minimum=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    value = float(value)
    if not math.isfinite(value) or (minimum is not None and value < minimum) or (positive and value <= 0):
        raise ValueError(f'{name} has an invalid range')
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value


def unit(value, scales, name):
    if not isinstance(value, str) or value not in scales:
        raise ValueError(f'{name} must be one of {list(scales)}')
    return scales[value]


def axis(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('axis_local_xyz must contain three components')
    result = np.array([number(v, 'axis component') for v in value])
    if not np.isclose(np.linalg.norm(result), 1., rtol=0, atol=1e-6):
        raise ValueError('axis_local_xyz must be a unit vector')
    return result


def provenance(meta):
    if not isinstance(meta, dict):
        raise ValueError('provenance must be an object')
    if meta.get('origin') not in ('synthetic', 'measured'):
        raise ValueError('origin must explicitly be synthetic or measured')
    return {k: text(meta.get(k), k) for k in ('origin', 'source_id', 'description')}


def source_path(base, value):
    path = Path(text(value, 'csv path'))
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('CSV paths must be relative and remain within the manifest folder')
    path = (base / path).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError('CSV path escapes manifest folder')
    if not path.is_file():
        raise ValueError(f'CSV file does not exist: {value}')
    return path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path, columns):
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != list(columns):
            raise ValueError(f'{path.name}: expected exact CSV header {",".join(columns)}')
        rows = []
        for i, row in enumerate(reader, 2):
            if None in row or any(row[c] is None for c in columns):
                raise ValueError(f'{path.name}:{i}: wrong number of columns')
            try:
                values = [float(row[c]) for c in columns]
            except (ValueError, TypeError) as exc:
                raise ValueError(f'{path.name}:{i}: nonnumeric CSV value') from exc
            if not all(math.isfinite(v) for v in values):
                raise ValueError(f'{path.name}:{i}: nonfinite CSV value')
            rows.append(values)
    if not rows:
        raise ValueError(f'{path.name}: empty CSV')
    return np.asarray(rows)


@dataclass
class ImportedScan:
    spectrum: Spectrum
    sequence: int
    strain_mhz: float
    strain_std_mhz: float
    splitting_std_mhz: float
    systematic_std_ut: float
    start_s: float
    metadata: dict

    def fit(self):
        estimate = estimate_field(self.spectrum, self.strain_mhz)
        packet = None
        uncertainty = None
        if estimate.accepted:
            # First-order independent calibration terms; common-mode frequency
            # shifts are not splitting errors. This is not full model uncertainty.
            root = GAMMA_MHZ_PER_UT * estimate.axial_magnitude_ut
            strain_term = self.strain_mhz / (GAMMA_MHZ_PER_UT * root) * self.strain_std_mhz
            split_term = estimate.half_splitting_mhz / (GAMMA_MHZ_PER_UT * root) * self.splitting_std_mhz
            uncertainty = {'fit_std_ut': estimate.field_std_ut,
                           'strain_std_ut': float(strain_term),
                           'half_splitting_calibration_std_ut': float(split_term),
                           'systematic_floor_std_ut': self.systematic_std_ut}
            estimate.field_std_ut = float(np.linalg.norm(list(uncertainty.values())))
            if estimate.field_std_ut > max(1., .25 * estimate.axial_magnitude_ut):
                estimate.accepted = False
                estimate.flags.append('high_calibration_uncertainty')
                estimate.axial_magnitude_ut = estimate.field_std_ut = None
            else:
                packet = nv_packet(estimate, self.sequence, estimate.timestamp_s - self.start_s)
                packet.metadata.update(self.metadata)
                packet.metadata['scan_start_s'] = self.start_s
                packet.metadata['uncertainty_components_ut'] = uncertainty
        return estimate, packet, uncertainty


@dataclass
class ImportDataset:
    manifest_path: Path
    manifest: dict
    magnetic_map: MagneticMap
    map_metadata: dict
    scans: list[ImportedScan]

    def convert(self):
        estimates, packets = [], []
        for scan in self.scans:
            result, packet, uncertainty = scan.fit()
            estimates.append({'sequence': scan.sequence, 'source': scan.metadata,
                              'estimate': result.to_dict(), 'uncertainty_components_ut': uncertainty})
            if packet is not None:
                packets.append(packet)
        audit = {'schema': SCHEMA, 'project': 'RelativisticQ-PNT', 'author': 'Christina Holt',
                 'manifest_sha256': sha256(self.manifest_path),
                 'timebase_id': self.manifest['timebase_id'],
                 'coordinate_system_id': self.manifest['coordinate_system_id'],
                 'map': self.map_metadata, 'scans_total': len(estimates),
                 'scans_accepted': len(packets), 'scans_rejected': len(estimates) - len(packets),
                 'provenance_is_user_declared': True, 'hardware_accuracy_validated': False,
                 'map_independence_verified': False,
                 'uncertainty_assumption': 'Independent first-order calibration terms; map error applied separately in fusion.'}
        return estimates, packets, audit


def load_dataset(manifest_path):
    path = Path(manifest_path)
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA:
        raise ValueError(f'Manifest schema must be {SCHEMA}')
    if manifest.get('frame') != 'local_xy':
        raise ValueError('Only local_xy maps are supported; geographic coordinates must be projected externally')
    timebase = text(manifest.get('timebase_id'), 'timebase_id')
    coordinate = text(manifest.get('coordinate_system_id'), 'coordinate_system_id')
    description = text(manifest.get('timebase_description'), 'timebase_description')
    sensor_axis = axis(manifest.get('axis_local_xyz'))
    m = manifest.get('magnetic_map')
    if not isinstance(m, dict) or m.get('observable') != 'fixed_axis_magnitude':
        raise ValueError('Map must describe fixed_axis_magnitude, not total or signed field')
    if not np.isclose(abs(np.dot(sensor_axis, axis(m.get('axis_local_xyz')))), 1., rtol=0, atol=1e-6):
        raise ValueError('Sensor and magnetic map axes do not match')
    mp = provenance(m.get('provenance'))
    mp['independence_statement'] = text(m.get('independence_statement'), 'independence_statement')
    field_scale = unit(m.get('field_units'), FIELD_SCALE, 'map field_units')
    position_scale = unit(m.get('position_units'), POSITION_SCALE, 'position_units')
    map_std_ut = number(number(m.get('error_std'), 'map error_std', positive=True) * field_scale,
                        'converted map error_std', positive=True)
    map_path = source_path(path.parent, m.get('csv'))
    data = read_csv(map_path, ('x', 'y', 'value'))
    data[:, :2] *= position_scale
    data[:, 2] *= field_scale
    xs, ys = np.unique(data[:, 0]), np.unique(data[:, 1])
    if len(data) != len(xs) * len(ys):
        raise ValueError('Map must contain a complete rectangular grid')
    grid = np.full((len(ys), len(xs)), np.nan)
    for x, y, v in data:
        i, j = np.searchsorted(ys, y), np.searchsorted(xs, x)
        if np.isfinite(grid[i, j]):
            raise ValueError('Duplicate map coordinate')
        grid[i, j] = v
    mmap = MagneticMap(xs, ys, grid)
    mp.update({'csv': m['csv'], 'csv_sha256': sha256(map_path),
               'axis_local_xyz': sensor_axis.tolist(), 'observable': 'fixed_axis_magnitude',
               'error_std_ut': map_std_ut, 'frame': 'local_xy',
               'coordinate_system_id': coordinate})
    rows = manifest.get('scans')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Manifest must list at least one scan')
    scans = []
    previous_sequence, previous_end = -1, -math.inf
    for s in rows:
        if not isinstance(s, dict):
            raise ValueError('Each scan must be an object')
        seq = s.get('sequence')
        if isinstance(seq, bool) or not isinstance(seq, int) or seq <= previous_sequence:
            raise ValueError('Scan sequences must be nonnegative and strictly increasing')
        start = number(s.get('scan_start_s'), 'scan_start_s', minimum=0)
        end = number(s.get('scan_end_s'), 'scan_end_s', minimum=0)
        dwell = number(s.get('dwell_s'), 'dwell_s', positive=True)
        if start < previous_end or end <= start:
            raise ValueError('Scans must have increasing, nonoverlapping acquisition intervals')
        if s.get('stationary_confirmed') is not True:
            raise ValueError('Stationary scan confirmation is required')
        stationary_source = text(s.get('stationarity_source'), 'stationarity_source')
        if s.get('counts_kind') != 'raw_photon_counts' or s.get('equal_dwell_confirmed') is not True:
            raise ValueError('Only equal-dwell raw photon counts are supported')
        frequency_scale = unit(s.get('frequency_units'), FREQUENCY_SCALE, 'frequency_units')
        source = source_path(path.parent, s.get('csv'))
        points = read_csv(source, ('frequency', 'counts'))
        if np.any(points[:, 1] < 0) or np.any(points[:, 1] != np.floor(points[:, 1])):
            raise ValueError('Raw photon counts must be nonnegative integers')
        if end - start + 1e-8 < len(points) * dwell:
            raise ValueError('Acquisition interval is shorter than point count times dwell')
        spectrum = Spectrum(points[:, 0] * frequency_scale, points[:, 1], dwell, end)
        cal = s.get('calibration')
        if not isinstance(cal, dict):
            raise ValueError('Calibration record is required')
        calibration_id = text(cal.get('calibration_id'), 'calibration_id')
        strain = number(cal.get('strain_mhz'), 'strain_mhz', minimum=0)
        strain_std = number(cal.get('strain_std_mhz'), 'strain_std_mhz', minimum=0)
        split_std = number(cal.get('half_splitting_std_mhz'), 'half_splitting_std_mhz', minimum=0)
        floor = number(cal.get('systematic_std_ut'), 'systematic_std_ut', minimum=0)
        meta = provenance(s.get('provenance'))
        meta.update({'csv': s['csv'], 'csv_sha256': sha256(source),
                     'calibration_id': calibration_id, 'calibration': dict(cal),
                     'timebase_id': timebase, 'timebase_description': description,
                     'coordinate_system_id': coordinate, 'axis_local_xyz': sensor_axis.tolist(),
                     'stationarity_source': stationary_source, 'stationary_confirmed': True,
                     'origin_is_user_declared': True, 'sample_count': len(points), 'dwell_s': dwell,
                     'adapter': 'exported_csv_v1'})
        scans.append(ImportedScan(spectrum, seq, strain, strain_std, split_std, floor, start, meta))
        previous_sequence, previous_end = seq, end
    return ImportDataset(path, manifest, mmap, mp, scans)


def write_conversion(dataset, output):
    estimates, packets, audit = dataset.convert()
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    (target / 'estimates.json').write_text(json.dumps(estimates, indent=2, allow_nan=False))
    (target / 'quantum_magnetic.jsonl').write_text(''.join(p.to_json() + '\n' for p in packets))
    (target / 'audit.json').write_text(json.dumps(audit, indent=2, allow_nan=False))
    dataset.magnetic_map.save(target / 'magnetic_map.npz')
    return estimates, packets, audit
