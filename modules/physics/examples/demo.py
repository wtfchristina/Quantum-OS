import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json,time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rq_sensing import SimulatedNVSensor,estimate_field
from rq_sensing.core import lineshape

def run():
    out=Path('demo_output'); out.mkdir(exist_ok=True)
    sensor=SimulatedNVSensor(seed=17)
    t=np.arange(40)*sensor.config.dwell_s*len(sensor.frequency_mhz)
    truth=65+15*np.sin(np.linspace(0,2*np.pi,len(t))); temp=np.linspace(293.15,297.15,len(t))
    fits=[]; scans=[]; durations=[]; rows=[]
    for timestamp,b,temperature in zip(t,truth,temp):
        scan=sensor.acquire(b,temperature,timestamp); start=time.perf_counter(); fit=estimate_field(scan)
        durations.append(time.perf_counter()-start); fits.append(fit); scans.append(scan)
        rows.append({'true_axial_magnitude_ut':float(b),'true_temperature_k':float(temperature),**fit.to_dict()})
    accepted=np.array([f.accepted for f in fits]); recovered=np.array([f.axial_magnitude_ut if f.accepted else np.nan for f in fits])
    std=np.array([f.field_std_ut if f.accepted else np.nan for f in fits]); error=recovered[accepted]-truth[accepted]
    metrics={'scope':'Synthetic axial ODMR; not hardware or navigation validation','seed':17,'scans':len(t),
      'accepted_scans':int(sum(accepted)),'rmse_ut':float(np.sqrt(np.mean(error**2))) if len(error) else None,
      'max_abs_error_ut':float(max(abs(error))) if len(error) else None,
      'approx_95pct_interval_coverage':float(np.mean(abs(error)<=1.96*std[accepted])) if len(error) else None,
      'median_fit_latency_ms':float(np.median(durations)*1000),'scan_duration_s':float(t[1]-t[0]),'config':sensor.config.__dict__}
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False))
    (out/'estimates.json').write_text(json.dumps(rows,indent=2,allow_nan=False))
    scan=scans[0]; fit=fits[0]
    np.savetxt(out/'sample_spectrum.csv',np.column_stack([scan.frequency_mhz,scan.counts]),delimiter=',',header='frequency_mhz,counts',comments='')
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    ax=axes[0,0]; ax.plot(scan.frequency_mhz,scan.counts/np.median(scan.counts),'.',ms=3,label='Poisson counts')
    ax.plot(scan.frequency_mhz,lineshape(scan.frequency_mhz,*fit.fit_parameters),label='Fit')
    ax.set(xlabel='Microwave frequency (MHz)',ylabel='Normalized fluorescence',title='ODMR resonance fit'); ax.legend()
    ax=axes[0,1]; ax.plot(t/60,truth,label='True axial magnitude'); ax.errorbar(t/60,recovered,yerr=1.96*std,fmt='.',label='Estimate ±1.96σ')
    ax.set(xlabel='Elapsed scan time (min)',ylabel='Axial magnitude (µT)',title='Magnetic field recovery'); ax.legend()
    ax=axes[1,0]; ax.plot(t/60,temp,label='True temperature'); ax.plot(t/60,[f.temperature_proxy_k for f in fits],'.',label='Midpoint proxy')
    ax.set(xlabel='Elapsed scan time (min)',ylabel='Temperature (K)',title='Common-mode temperature drift'); ax.legend()
    ax=axes[1,1]; ax.axhline(0,color='gray'); ax.plot(t/60,recovered-truth,'.')
    ax.set(xlabel='Elapsed scan time (min)',ylabel='Estimate − truth (µT)',title=f"Synthetic RMSE: {metrics['rmse_ut']:.3f} µT")
    fig.suptitle('RelativisticQ-PNT Quantum Sensing v0.2 sensor pipeline • SIMULATED DATA',fontsize=16)
    fig.tight_layout(); fig.savefig(out/'demo.png',dpi=160); plt.close(fig)
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>RelativisticQ-PNT demo</title><style>body{background:#0c1627;color:#eef5ff;font:18px system-ui;max-width:1100px;margin:40px auto}img{width:100%}pre{white-space:pre-wrap}</style><h1>RelativisticQ-PNT Quantum Sensing v0.2 sensor pipeline</h1><p>Simulated axial NV magnetometry. No hardware or navigation accuracy claim.</p><img src="demo.png" alt="Spectrum fit and field recovery"><pre>'+json.dumps(metrics,indent=2)+'</pre>')
    print(json.dumps(metrics,indent=2))
    if not np.all(accepted): raise RuntimeError('Default demo unexpectedly rejected a scan')
if __name__=='__main__': run()
