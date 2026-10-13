import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse,json,time,platform
import numpy as np
import scipy,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rq_sensing.integrated_simulation import IntegratedConfig,run_integrated

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--benchmark',action='store_true');parser.add_argument('--no-stationary-aiding',action='store_true');args=parser.parse_args()
    out=Path('integrated_output')/('without_stationary_aiding' if args.no_stationary_aiding else '.');out.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    result,mmap,gmap,scans=run_integrated(IntegratedConfig(stationary_aiding=not args.no_stationary_aiding));r=result['records']
    summary={k:result[k] for k in ['config','metrics','duration_s','scope']}
    (out/'metrics.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    (out/'track.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    (out/'nv_packets.jsonl').write_text('\n'.join(json.dumps(p,allow_nan=False) for p in result['nv_packets'])+'\n')
    (out/'sensor_inputs.jsonl').write_text('\n'.join(json.dumps(p,allow_nan=False) for p in result['input_packets'])+'\n')
    (out/'fusion_initialization.json').write_text(json.dumps(result['initialization'],indent=2))
    (out/'gravity_map.json').write_text(json.dumps([a.__dict__ for a in gmap.anomalies],indent=2))
    from rq_sensing.replay_fusion import replay
    states,statuses=replay(result['input_packets'],mmap,gmap,result['initialization'])
    expected=result['final_states']['fused']['values']
    np.testing.assert_allclose(list(states[-1].values.values()),list(expected.values()),rtol=1e-12,atol=1e-10)
    (out/'replay_validation.json').write_text(json.dumps({'matched_fused_final_state':True,'input_packets':len(result['input_packets']),'navigation_states':len(states)},indent=2))
    mmap.save(out/'magnetic_map.npz')
    np.savez(out/'odmr_scans.npz',frequency_mhz=scans[0].frequency_mhz,counts=np.array([s.counts for s in scans]),timestamp_s=np.array([s.timestamp_s for s in scans]),dwell_s=.05)
    modes=['ins','gravity','magnetic','fused'];truth=np.array([x['truth'][:2] for x in r]); times=np.array([x['time_s'] for x in r])
    tracks={m:np.array([x[m][:2] for x in r]) for m in modes}
    np.savetxt(out/'track.csv',np.column_stack([times,truth,*tracks.values()]),delimiter=',',header='time_s,true_x_m,true_y_m,'+','.join(f'{m}_x_m,{m}_y_m' for m in modes),comments='')
    fig,axes=plt.subplots(2,2,figsize=(12,9))
    ax=axes[0,0];ax.pcolormesh(mmap.x_m,mmap.y_m,mmap.axial_magnitude_ut,shading='auto',cmap='viridis');ax.plot(truth[:,0],truth[:,1],color='white',label='Truth')
    for m in ['gravity','magnetic','fused']:ax.plot(tracks[m][:,0],tracks[m][:,1],label=('IMU + stationary' if m=='ins' and not args.no_stationary_aiding else m))
    ax.set(xlabel='Local x (m)',ylabel='Local y (m)',title='Aided trajectories on fictional magnetic map');ax.legend();ax.set_aspect('equal')
    ax=axes[0,1]
    for m in modes:ax.semilogy(times/60,np.maximum(np.linalg.norm(tracks[m]-truth,axis=1),.01),label=('IMU + stationary' if m=='ins' and not args.no_stationary_aiding else m))
    ax.set(xlabel='Elapsed time (min)',ylabel='Position error (m, log scale)',title='Four-mode comparison');ax.legend()
    ax=axes[1,0];epochs=result['sensor_estimates'];ax.plot([e['true_field_ut'] for e in epochs],label='True field');ax.plot([e['axial_magnitude_ut'] for e in epochs],'.',label='ODMR fit');ax.legend()
    ax.set(xlabel='Stationary scan epoch',ylabel='Axial magnitude (µT)',title='20.05-second acquisitions at rest')
    ax=axes[1,1];names=['gravity','magnetic','fused'];ax.bar(names,[result['metrics'][m]['rmse_m'] for m in names]);ax.set(ylabel='Position RMSE (m)',title='Nominal aiding modes')
    fig.suptitle('RelativisticQ-PNT v0.3 • GRAVITY + NV MAGNETIC + PLANAR IMU (SIMULATION)');fig.tight_layout();fig.savefig(out/'integration.png',dpi=160);plt.close(fig)
    benchmark=[summary]
    if args.benchmark:
        for seed in [3,11,29,47]:
            x,_,_,_=run_integrated(IntegratedConfig(seed=seed,stationary_aiding=not args.no_stationary_aiding));benchmark.append({k:x[k] for k in ['config','metrics','duration_s','scope']})
        for case in ['dropouts','interference','flat_magnetic']:
            x,_,_,_=run_integrated(IntegratedConfig(scenario=case,stationary_aiding=not args.no_stationary_aiding));benchmark.append({k:x[k] for k in ['config','metrics','duration_s','scope']})
    (out/'benchmark.json').write_text(json.dumps(benchmark,indent=2,allow_nan=False))
    table='<table><tr><th>Case</th><th>Seed</th>'+''.join('<th>'+('IMU + stationary' if m=='ins' and not args.no_stationary_aiding else m)+' RMSE (m)</th>' for m in modes)+'</tr>'
    for x in benchmark:table+='<tr><td>'+x['config']['scenario']+'</td><td>'+str(x['config']['seed'])+'</td>'+''.join(f"<td>{x['metrics'][m]['rmse_m']:.2f}</td>" for m in modes)+'</tr>'
    table+='</table>'
    note='Trusted stationary signal provides zero-velocity observations equally to all modes.' if not args.no_stationary_aiding else 'Stationary velocity aiding is disabled; local filter divergence is possible.'
    diagnostics=''
    diagnostic_path=out/'no_stationary_aiding_benchmark.json'
    if diagnostic_path.exists():
        old=json.loads(diagnostic_path.read_text());diagnostics='<h2>Diagnostic: stationary aiding disabled</h2><p>Retained initial campaign. Several local-filter runs diverged. No recovery or guaranteed global localization is implemented.</p><table><tr><th>Case</th><th>Seed</th><th>Fused RMSE (m)</th></tr>'+''.join(f"<tr><td>{a['config']['scenario']}</td><td>{a['config']['seed']}</td><td>{a['metrics']['fused']['rmse_m']:.2f}</td></tr>" for a in old)+'</table>'
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Quantum Sensing v0.3</title><style>body{max-width:1150px;margin:40px auto;font:18px system-ui;background:#0c1627;color:#eef5ff}img{width:100%}pre{white-space:pre-wrap}td,th{padding:10px;text-align:right}td:first-child,th:first-child{text-align:left}table{width:100%;border-collapse:collapse}tr{border-bottom:1px solid #394555}</style><h1>Quantum Sensing v0.3</h1><p>NV sensing connected to the existing gravity v0.7 FusionEKF. Synthetic stop-and-measure route; known fixed sensor axis; '+note+' No hardware performance claim.</p><img src="integration.png" alt="Integrated four-mode navigation comparison"><h2>All benchmark results</h2>'+table+'<h2>Nominal run</h2><pre>'+json.dumps(summary,indent=2)+'</pre>'+diagnostics)
    (out/'environment.json').write_text(json.dumps({'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'platform':platform.platform(),'runtime_s':time.perf_counter()-start},indent=2))
    print(json.dumps(benchmark,indent=2),flush=True)
if __name__=='__main__':main()
