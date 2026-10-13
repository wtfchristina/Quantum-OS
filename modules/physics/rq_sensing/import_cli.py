"""Import exported fixed-axis ODMR scans and reference maps, then replay."""
import argparse
import json
from pathlib import Path
import numpy as np
from .import_data import load_dataset, write_conversion, number, sha256
from .replay_fusion import replay
from ._gravity_v07.gravity_map import SyntheticGravityMap, GaussianAnomaly


class NoGravityMap:
    def value(self, x, y):
        return 0.

    def gradient(self, x, y):
        return np.zeros(2)


def prepare_motion(dataset, motion_path, initialization_path, gravity_path=None):
    init = json.loads(Path(initialization_path).read_text())
    if not isinstance(init, dict):
        raise ValueError('Initialization must be a JSON object')
    for key in ('timebase_id', 'coordinate_system_id'):
        if init.get(key) != dataset.manifest[key]:
            raise ValueError(f'Initialization {key} differs from manifest')
    number(init.get('timestamp_s'), 'initialization timestamp_s', minimum=0)
    for scan in dataset.scans:
        if scan.start_s < init['timestamp_s']:
            raise ValueError('Scan begins before initialization')
    motion = [json.loads(line) for line in Path(motion_path).read_text().splitlines() if line.strip()]
    if not motion:
        raise ValueError('Empty motion stream')
    last_time = init['timestamp_s']
    last_imu = init['timestamp_s']
    last_sequences = {}
    allowed = {'imu': ('ax_mps2', 'ay_mps2'),
               'stationary_velocity': ('vx_mps', 'vy_mps', 'noise_std_mps'),
               'gravity': ('value', 'noise_std')}
    for p in motion:
        if not isinstance(p, dict) or p.get('sensor') not in allowed:
            raise ValueError('Motion stream accepts IMU, stationary velocity and optional toy gravity only')
        name = p['sensor']
        t = number(p.get('timestamp_s'), 'packet timestamp_s', minimum=0)
        seq = p.get('sequence')
        if isinstance(seq, bool) or not isinstance(seq, int) or seq <= last_sequences.get(name, -1):
            raise ValueError('Motion sequence must be nonnegative and increase within each sensor')
        if t < last_time:
            raise ValueError('Motion stream is out of acquisition order')
        if p.get('frame') != 'local_xy':
            raise ValueError('Motion frame must be local_xy')
        meta = p.get('metadata')
        if not isinstance(meta, dict):
            raise ValueError('Motion metadata must be an object')
        for key in ('timebase_id', 'coordinate_system_id'):
            if meta.get(key) != dataset.manifest[key]:
                raise ValueError(f'Motion {key} differs from manifest')
        values = p.get('values')
        if not isinstance(values, dict) or set(values) != set(allowed[name]):
            raise ValueError(f'Invalid {name} payload')
        for key, value in values.items():
            number(value, key, positive=key.startswith('noise_std'))
        if name == 'imu':
            if meta.get('units') != 'm/s^2' or t <= last_imu:
                raise ValueError('IMU requires m/s^2 and strictly increasing time')
            last_imu = t
        elif name == 'stationary_velocity':
            if meta.get('units') != 'm/s' or meta.get('stationarity_source') != 'trusted_stop_signal' or t != last_imu:
                raise ValueError('Stationary velocity needs trusted_stop_signal, m/s, and matching IMU time')
        else:
            if gravity_path is None or meta.get('observable') != 'synthetic_scalar_gravity' or meta.get('units') != 'toy_units':
                raise ValueError('Gravity import supports only explicit legacy toy data with --toy-gravity-map')
            if t != last_imu:
                raise ValueError('Gravity timestamp must match IMU time')
        last_time, last_sequences[name] = t, seq
    if not any(p['sensor'] == 'imu' for p in motion):
        raise ValueError('At least one IMU prediction is required')
    imu_times = np.array([p['timestamp_s'] for p in motion if p['sensor'] == 'imu'])
    for scan in dataset.scans:
        # No implicit interpolation or time shift: scan completion is a filter epoch.
        if not np.any(imu_times == scan.spectrum.timestamp_s):
            raise ValueError('Scan end must match an IMU prediction epoch; resample explicitly')
    gmap = NoGravityMap()
    if gravity_path is not None:
        gmap = SyntheticGravityMap([GaussianAnomaly(**a) for a in json.loads(Path(gravity_path).read_text())])
    return motion, init, gmap


def run_imported(dataset, motion_path, initialization_path, output, gravity_path=None):
    motion, init, gmap = prepare_motion(dataset, motion_path, initialization_path, gravity_path)
    estimates, packets, audit = dataset.convert()
    merged = motion + [p.to_dict() for p in packets]
    # Stable ties: IMU prediction, stationary/gravity updates, then magnetic.
    merged.sort(key=lambda p: p['timestamp_s'])
    states, statuses = replay(merged, dataset.magnetic_map, gmap, init,
                             map_std_nt=dataset.map_metadata['error_std_ut'] * 1000.)
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    for name, data in [('estimates.json', estimates), ('status.json', statuses)]:
        (target / name).write_text(json.dumps(data, indent=2, allow_nan=False))
    (target / 'quantum_magnetic.jsonl').write_text(''.join(p.to_json() + '\n' for p in packets))
    (target / 'sensor_inputs.jsonl').write_text(''.join(json.dumps(p, allow_nan=False) + '\n' for p in merged))
    (target / 'navigation_states.jsonl').write_text(''.join(s.to_json() + '\n' for s in states))
    dataset.magnetic_map.save(target / 'magnetic_map.npz')
    audit.update({'motion_stream_sha256': sha256(motion_path),
                  'initialization_sha256': sha256(initialization_path),
                  'toy_gravity_map_sha256': sha256(gravity_path) if gravity_path else None,
                  'state_snapshots': len(states),
                  'magnetic_updates_used': sum(s['used'] for s in statuses if s['sensor'] == 'quantum_magnetic'),
                  'final_state': states[-1].to_dict(), 'navigation_accuracy_measured': False})
    (target / 'audit.json').write_text(json.dumps(audit, indent=2, allow_nan=False))
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description='RelativisticQ-PNT exported-data workflow by Christina Holt')
    subs = parser.add_subparsers(dest='command', required=True)
    for command in ('validate', 'convert', 'replay'):
        sub = subs.add_parser(command)
        sub.add_argument('manifest', type=Path)
        if command != 'validate':
            sub.add_argument('--output', type=Path, required=True)
        if command == 'replay':
            sub.add_argument('--motion-stream', type=Path, required=True)
            sub.add_argument('--initialization', type=Path, required=True)
            sub.add_argument('--toy-gravity-map', type=Path)
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.manifest)
        if args.command == 'validate':
            result = {'valid': True, 'scans': len(dataset.scans),
                      'map_shape': list(dataset.magnetic_map.axial_magnitude_ut.shape),
                      'note': 'Contract validation only; spectra have not been fitted.'}
        elif args.command == 'convert':
            _, _, result = write_conversion(dataset, args.output)
        else:
            result = run_imported(dataset, args.motion_stream, args.initialization,
                                  args.output, args.toy_gravity_map)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 3 if result.get('scans_accepted') == 0 else 0
    except (ValueError, KeyError, OSError, TypeError, IndexError) as exc:
        parser.exit(2, f'Import error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
