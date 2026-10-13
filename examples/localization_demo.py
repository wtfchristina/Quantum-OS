import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse,json,time,platform
import numpy as np
import scipy,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rq_sensing import SimulatedNVSensor,estimate_field,SensorConfig
from rq_sensing.navigation import ParticleMapMatcher,MatcherConfig
from rq_sensing.scenarios import make_map,trajectory,displacement_stream,environment_field

def run_case(seed=17,scenario='nominal',steps=60):
    truth=trajectory(steps); magnetic_map=make_map(flat=scenario=='flat_map'); delta=displacement_stream(truth,seed)
    matcher=ParticleMapMatcher(magnetic_map,truth[0].copy(),seed=seed+1000)
    sensor=SimulatedNVSensor(seed=seed+2000)
    baseline=truth[0]+np.cumsum(delta,axis=0)
    rows=[]; aided=[]; used=[]; traces=[]; spectra=[]; latency=[]
    for k,xy in enumerate(truth):
        # Stop-and-measure scans: motion between scan epochs, static during acquisition.
        b=60. if scenario=='flat_map' else float(environment_field(*xy))
        scan=sensor.acquire(b,293.15+3*k/(steps-1),k*20.05)
        if scenario=='dropouts' and 20<=k<30:
            field=None
        else:
            if scenario=='interference' and 20<=k<25: scan.counts[100:150]*=.75
            field=estimate_field(scan)
        start=time.perf_counter(); pos=matcher.step(delta[k],field); latency.append(time.perf_counter()-start)
        aided.append(pos.position_m); used.append(pos.measurement_used)
        rows.append({'step':k,'truth_m':xy.tolist(),'dead_reckoning_m':baseline[k].tolist(),'sensor':None if field is None else field.to_dict(),**pos.to_dict()})
        traces.append([b,np.nan if field is None or not field.accepted else field.axial_magnitude_ut]); spectra.append(scan)
    aided=np.array(aided); base_error=np.linalg.norm(baseline-truth,axis=1); aided_error=np.linalg.norm(aided-truth,axis=1)
    metrics={'seed':seed,'scenario':scenario,'steps':steps,'dead_reckoning_rmse_m':float(np.sqrt(np.mean(base_error**2))),
       'magnetic_aided_rmse_m':float(np.sqrt(np.mean(aided_error**2))),'dead_reckoning_final_error_m':float(base_error[-1]),
       'magnetic_aided_final_error_m':float(aided_error[-1]),'measurement_updates':int(sum(used)),
       'median_match_latency_ms':float(np.median(latency)*1000),'scope':'Synthetic fixed-axis, stop-and-measure local tracking; displacement-level inertial surrogate'}
    return metrics,rows,magnetic_map,truth,baseline,aided,np.array(traces),spectra

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--benchmark',action='store_true'); args=parser.parse_args()
    out=Path('localization_output'); out.mkdir(exist_ok=True)
    metrics,rows,m,truth,base,aided,traces,scans=run_case()
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)); (out/'track.json').write_text(json.dumps(rows,indent=2,allow_nan=False))
    m.save(out/'magnetic_map.npz')
    np.savetxt(out/'track.csv',np.column_stack([np.arange(len(truth)),truth,base,aided]),delimiter=',',header='step,true_x_m,true_y_m,dead_x_m,dead_y_m,aided_x_m,aided_y_m',comments='')
    np.savez(out/'odmr_scans.npz',frequency_mhz=scans[0].frequency_mhz,counts=np.array([s.counts for s in scans]),dwell_s=.05)
    fig,axes=plt.subplots(2,2,figsize=(12,9))
    ax=axes[0,0]; im=ax.pcolormesh(m.x_m,m.y_m,m.axial_magnitude_ut,shading='auto',cmap='viridis'); fig.colorbar(im,ax=ax,label='Axial magnitude (µT)')
    for v,label in [(truth,'Truth'),(base,'Dead reckoning'),(aided,'Magnetic aided')]: ax.plot(v[:,0],v[:,1],label=label)
    ax.set(xlabel='Local x (m)',ylabel='Local y (m)',title='Fictional map and trajectories'); ax.legend(); ax.set_aspect('equal')
    ax=axes[0,1]
    for v,label in [(base,'Dead reckoning'),(aided,'Magnetic aided')]: ax.plot(np.linalg.norm(v-truth,axis=1),label=label)
    ax.set(xlabel='Scan epoch',ylabel='Position error (m)',title='Synthetic position error'); ax.legend()
    ax=axes[1,0]; ax.plot(traces[:,0],label='True field'); ax.plot(traces[:,1],'.',label='ODMR estimate'); ax.legend()
    ax.set(xlabel='Scan epoch',ylabel='Axial magnitude (µT)',title='Raw spectra → field → map likelihood')
    ax=axes[1,1]; cov=np.array([r['covariance_m2'] for r in rows]); ax.plot(np.sqrt(np.trace(cov,axis1=1,axis2=2)))
    ax.set(xlabel='Scan epoch',ylabel='Posterior RMS spread (m)',title='Particle spread (not guaranteed accuracy)')
    fig.suptitle('RelativisticQ-PNT v0.2 • SIMULATED MAGNETIC LOCALIZATION'); fig.tight_layout(); fig.savefig(out/'localization.png',dpi=160); plt.close(fig)
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>RelativisticQ-PNT v0.2</title><style>body{max-width:1150px;margin:40px auto;font:18px system-ui;background:#0c1627;color:#eef5ff}img{width:100%}pre{white-space:pre-wrap}</style><h1>Quantum Sensing v0.2</h1><p>Simulated fixed-axis local tracking. Known starting fix; stationary ODMR scans; fictional map; no hardware or gravity-stack integration.</p><img src="localization.png" alt="Map and simulated localization benchmark"><pre>'+json.dumps(metrics,indent=2)+'</pre>')
    (out/'environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'matcher_config':MatcherConfig().__dict__,'sensor_config':SensorConfig().__dict__},indent=2))
    print(json.dumps(metrics,indent=2))
    if args.benchmark:
        results=[metrics]
        for seed in [3,11,29,47]: results.append(run_case(seed)[0])
        for scenario in ['dropouts','interference','flat_map']: results.append(run_case(17,scenario)[0])
        (out/'benchmark.json').write_text(json.dumps(results,indent=2,allow_nan=False)); print(json.dumps(results,indent=2))
        nominal=[r for r in results if r['scenario']=='nominal']
        base_mean=float(np.mean([r['dead_reckoning_rmse_m'] for r in nominal]))
        aided_mean=float(np.mean([r['magnetic_aided_rmse_m'] for r in nominal]))
        summary={'mean_per_run_dead_reckoning_rmse_m':base_mean,'mean_per_run_magnetic_aided_rmse_m':aided_mean,
                 'reduction_in_mean_per_run_rmse_pct':100*(1-aided_mean/base_mean),'nominal_runs':len(nominal)}
        (out/'benchmark_summary.json').write_text(json.dumps(summary,indent=2))
        table='<h2>All benchmark cases</h2><table><tr><th>Case</th><th>Seed</th><th>Dead-reckoning RMSE (m)</th><th>Aided RMSE (m)</th><th>Updates</th></tr>'
        for r in results:
            table+=f"<tr><td>{r['scenario']}</td><td>{r['seed']}</td><td>{r['dead_reckoning_rmse_m']:.2f}</td><td>{r['magnetic_aided_rmse_m']:.2f}</td><td>{r['measurement_updates']}</td></tr>"
        table+=f'</table><p>Mean per-run nominal RMSE: {base_mean:.2f} m → {aided_mean:.2f} m. Synthetic only; flat-map runs produce no magnetic updates.</p>'
        report=out/'report.html'; report.write_text(report.read_text()+table)

if __name__=='__main__': main()
