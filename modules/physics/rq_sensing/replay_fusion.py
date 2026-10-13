"""Replay sensor-only JSONL through the integrated filter; no truth required."""
import argparse,json
from pathlib import Path
import numpy as np
from .fusion_bridge import QuantumGravityFusion
from .navigation import MagneticMap
from ._gravity_v07.packets import SensorPacket
from ._gravity_v07.gravity_map import SyntheticGravityMap,GaussianAnomaly

def replay(packets,magnetic_map,gravity_map,initialization, *, map_std_nt=650.):
    engine=QuantumGravityFusion(initialization['state'],initialization['covariance'],magnetic_map,gravity_map,
                                initial_timestamp_s=initialization['timestamp_s'],map_std_nt=map_std_nt)
    states=[];statuses=[];last_sequence={}
    for number,data in enumerate(packets):
        packet=SensorPacket.from_dict(data)
        if not np.isfinite(packet.timestamp_s) or packet.sequence<0 or packet.sequence<=last_sequence.get(packet.sensor,-1):
            raise ValueError(f'Packet {number}: invalid time/sequence')
        if packet.frame!='local_xy':raise ValueError(f'Packet {number}: incompatible frame')
        values=packet.values
        if not all(np.isfinite(v) for v in values.values()):raise ValueError(f'Packet {number}: nonfinite payload')
        last_sequence[packet.sensor]=packet.sequence
        status=None
        if packet.sensor=='imu':engine.predict([values['ax_mps2'],values['ay_mps2']],packet.timestamp_s)
        elif packet.sensor=='stationary_velocity':
            if packet.metadata.get('stationarity_source')!='trusted_stop_signal' or abs(packet.timestamp_s-engine.time)>1e-9:
                raise ValueError(f'Packet {number}: invalid stationary observation contract')
            status=engine.update_stationary_velocity([values['vx_mps'],values['vy_mps']],values['noise_std_mps'])
        elif packet.sensor=='gravity':
            if packet.metadata.get('observable')!='synthetic_scalar_gravity' or packet.metadata.get('units')!='toy_units':
                raise ValueError(f'Packet {number}: incompatible gravity observable')
            status=engine.update_gravity(values['value'],values['noise_std'],packet.timestamp_s)
        elif packet.sensor=='quantum_magnetic':status=engine.update_nv_packet(packet)
        else:raise ValueError(f'Packet {number}: unsupported sensor {packet.sensor}')
        states.append(engine.state_packet(number))
        if status is not None:statuses.append({'packet_index':number,'sensor':packet.sensor,**status.to_dict()})
    return states,statuses

def main():
    p=argparse.ArgumentParser(description='Replay local synthetic gravity + NV sensor packets')
    p.add_argument('inputs',type=Path);p.add_argument('--magnetic-map',type=Path,required=True)
    p.add_argument('--gravity-map',type=Path,required=True);p.add_argument('--initialization',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('replayed_states.jsonl'));args=p.parse_args()
    try:
        packets=[json.loads(line) for line in args.inputs.read_text().splitlines() if line.strip()]
        if not packets:raise ValueError('Empty replay input')
        mmap=MagneticMap.load(args.magnetic_map)
        gmap=SyntheticGravityMap([GaussianAnomaly(**a) for a in json.loads(args.gravity_map.read_text())])
        states,statuses=replay(packets,mmap,gmap,json.loads(args.initialization.read_text()))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text('\n'.join(s.to_json() for s in states)+'\n')
        args.output.with_suffix('.status.json').write_text(json.dumps(statuses,indent=2,allow_nan=False))
        print(f'Replayed {len(packets)} sensor packets; wrote {len(states)} state snapshots')
    except (ValueError,KeyError,OSError,TypeError) as exc:p.exit(2,f'Replay input error: {exc}\n')
if __name__=='__main__':main()
