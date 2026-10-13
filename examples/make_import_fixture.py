"""Create openly labeled exported-data fixtures from the retained v0.3 simulation."""
from pathlib import Path
import json
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rq_sensing.navigation import MagneticMap


def main():
    root = Path(__file__).resolve().parents[1]
    old = root / 'integrated_output'
    dest = root / 'import_inputs'
    dest.mkdir(exist_ok=True)
    mmap = MagneticMap.load(old / 'magnetic_map.npz')
    x, y = np.meshgrid(mmap.x_m, mmap.y_m)
    np.savetxt(dest / 'reference_map.csv', np.column_stack((x.ravel(), y.ravel(), mmap.axial_magnitude_ut.ravel() * 1000)),
               delimiter=',', header='x,y,value', comments='', fmt='%.12g')
    manifest = {'schema': 'relativisticq-pnt.import.v1', 'frame': 'local_xy',
                'coordinate_system_id': 'v03-fictional-local-map', 'timebase_id': 'v03-nominal-simulation',
                'timebase_description': 'Relative seconds since simulation initialization; not wall clock.',
                'axis_local_xyz': [0, 0, 1],
                'magnetic_map': {'csv': 'reference_map.csv', 'observable': 'fixed_axis_magnitude',
                                 'axis_local_xyz': [0, 0, 1], 'position_units': 'm', 'field_units': 'nT',
                                 'error_std': 650,
                                 'independence_statement': 'NOT independent: sampled from the same synthetic environment used for scans.',
                                 'provenance': {'origin': 'synthetic', 'source_id': 'v03-nominal-map',
                                                'description': 'Fictional fixed-axis grid exported from the retained simulation.'}},
                'scans': []}
    with np.load(old / 'odmr_scans.npz') as z:
        for i in range(3):
            csv_name = f'scan_{i:03d}.csv'
            np.savetxt(dest / csv_name, np.column_stack((z['frequency_mhz'] / 1000, z['counts'][i])),
                       delimiter=',', header='frequency,counts', comments='', fmt=['%.12g', '%d'])
            end = float(z['timestamp_s'][i])
            manifest['scans'].append({'csv': csv_name, 'sequence': i, 'frequency_units': 'GHz',
                'counts_kind': 'raw_photon_counts', 'equal_dwell_confirmed': True, 'dwell_s': float(z['dwell_s']),
                'scan_start_s': end - 20.05, 'scan_end_s': end, 'stationary_confirmed': True,
                'stationarity_source': 'simulation truth asserts fixed position during acquisition',
                'calibration': {'calibration_id': 'synthetic-model-v1', 'strain_mhz': .15,
                    'strain_std_mhz': .01, 'half_splitting_std_mhz': .001, 'systematic_std_ut': .02},
                'provenance': {'origin': 'synthetic', 'source_id': f'v03-simulated-scan-{i}',
                    'description': 'Poisson photon-count simulation; not measured instrument data.'}})
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    cutoff = manifest['scans'][-1]['scan_end_s']
    packets = []
    for line in (old / 'sensor_inputs.jsonl').read_text().splitlines():
        p = json.loads(line)
        if p['timestamp_s'] <= cutoff and p['sensor'] != 'quantum_magnetic':
            p['metadata'].update({key: manifest[key] for key in ('timebase_id', 'coordinate_system_id')})
            if p['sensor'] == 'imu': p['metadata']['units'] = 'm/s^2'
            if p['sensor'] == 'stationary_velocity': p['metadata']['units'] = 'm/s'
            packets.append(p)
    (dest / 'motion.jsonl').write_text(''.join(json.dumps(p) + '\n' for p in packets))
    init = json.loads((old / 'fusion_initialization.json').read_text())
    init.update({key: manifest[key] for key in ('timebase_id', 'coordinate_system_id')})
    (dest / 'initialization.json').write_text(json.dumps(init, indent=2))
    (dest / 'toy_gravity_map.json').write_bytes((old / 'gravity_map.json').read_bytes())
    print('Wrote three synthetic exported scans, fictional map and truth-free motion stream.')


if __name__ == '__main__': main()
