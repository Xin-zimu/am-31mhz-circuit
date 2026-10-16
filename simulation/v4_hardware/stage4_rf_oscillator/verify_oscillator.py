"""Independent 5 V oscillator exploration, NOT a qualified C518062 model.

Prepare one case, run its .cmd through run_s04.ps1, then measure the same name.
Crystal motional parameters and fundamental mode are explicitly hypothetical.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import numpy as np
from verify_poly import read_raw

HERE = Path(__file__).resolve().parent
OUT = HERE / 'c518062_model_20261016'
WORK = Path('D:/ms_xsp/s04_c518062_20261016')
MODEL = OUT / 'BFR93A_SPICE.prm'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(a):
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    if any((WORK / (a.name+ext)).exists() for ext in ('.raw','.log','.status.json')):
        raise ValueError('Choose a new case name; existing evidence cannot be overwritten.')
    cm, c0, cl = a.cm_ff*1e-15, a.c0_pf*1e-12, 18e-12
    fs = a.fl_mhz*1e6 / np.sqrt(1+cm/(c0+cl))
    lm = 1/((2*np.pi*fs)**2*cm)
    p = vars(a).copy()
    p.update(c518062_qualified=False, mode='ASSUMED fundamental, single-mode BVD',
             fs_hz=fs, lm_h=lm, cl_reference_f=cl,
             motional_q=2*np.pi*fs*lm/a.rm,
             no_injected_rf_source=True, initial_state='zero energy (UIC), rising supply',
             transistor_source='NXP official BFR93A_SPICE.prm, text transcribed via web reader',
             transistor_sha256=sha(MODEL))
    net = [
        '* Exploratory 5 V Colpitts; C518062 motional parameters NOT verified',
        '* Independent DUT; no RF generator, buffer, modulator or main project',
        '* BFR93A model port order C B E, not physical package pin numbering',
        f'* Assumed Cm={a.cm_ff} fF, C0={a.c0_pf} pF, Rm={a.rm} ohm',
        f'* fL={a.fl_mhz} MHz at CL=18 pF, fs={fs:.12g} Hz',
        f'VSUP vcc 0 PWL(0 0 {a.ramp_us}u 5)',
        'HISUP isupply 0 VSUP -1',
        'RBUP vcc base 10k', 'RBDN base 0 10k',
        'XQ vcc base emit BFR93A', f'RE emit 0 {a.re}',
        f'CF base emit {a.cf_pf}p', f'CE emit 0 {a.ce_pf}p',
        f'CPAR base 0 {a.stray_pf}p',
        '* High impedance observation only; no buffer or 2k/10pF load',
        'RPROBE emit 0 100meg',
        f'CX0 base 0 {a.c0_pf}p',
    ]
    if not a.no_motional:
        net += ['VXM base xr 0', f'RXM xr xl {a.rm}', f'LXM xl xc {lm:.15g}',
                f'CXM xc 0 {a.cm_ff}f', 'HIMOT imotional 0 VXM 1']
    else:
        net += ['VIMZERO imotional 0 0']
    net += [MODEL.read_text(encoding='ascii').rstrip(), '.end']
    signals = '$vcc $base $emit $isupply $imotional'
    cmd = (f'source {WORK.as_posix()}/{a.name}.cir\n'
           'begin-scope page Transient Analysis\n'
           f'save {signals}\niplot {signals}\n'
           f'tran {a.step_ns}n {a.stop_us}u {a.save_from_us}u {a.step_ns}n uic\n'
           f'write-and-destroy-iplot "{WORK.as_posix()}/{a.name}.raw"\nend-scope\n')
    (OUT/(a.name+'.cir')).write_text('\n'.join(net)+'\n', encoding='ascii')
    (OUT/(a.name+'.cmd')).write_text(cmd, encoding='ascii')
    (OUT/(a.name+'.input.json')).write_text(json.dumps(p, indent=2), encoding='utf-8')
    for ext in ('cir','cmd'):
        shutil.copy2(OUT/(a.name+'.'+ext), WORK/(a.name+'.'+ext))
    print(json.dumps({'prepared':a.name, 'fs_hz':fs, 'lm_h':lm, 'base':str(WORK/a.name)}))


def time_mean(t, v):
    return float(np.trapezoid(v, t)/(t[-1]-t[0]))


def measure(a):
    for ext in ('raw','log','status.json'):
        src = WORK/(a.name+'.'+ext)
        if src.exists():
            shutil.copy2(src, OUT/src.name)
    status = json.loads((OUT/(a.name+'.status.json')).read_text(encoding='utf-8-sig'))
    assert status['state']==0 and not status['last_error'] and not status.get('log_errors') and status['output_exists'], status
    assert not any(line.startswith('Error:') for line in (OUT/(a.name+'.log')).read_text(encoding='ascii').splitlines())
    p = json.loads((OUT/(a.name+'.input.json')).read_text())
    n, data = read_raw(OUT/(a.name+'.raw'))
    t = data[:,0]
    assert abs(t[-1]-p['stop_us']*1e-6)<1e-12
    def v(node):
        return data[:,n.index('v('+node+')')]
    tail = t >= t[-1]-20e-6
    tt = t[tail]
    y = v('emit')[tail]
    mean = time_mean(tt, y)
    amplitude = float(np.ptp(y)/2)
    idx = np.flatnonzero((y[:-1]<mean)&(y[1:]>=mean))
    cross = tt[idx]+(mean-y[idx])*(tt[idx+1]-tt[idx])/(y[idx+1]-y[idx])
    freq = float((len(cross)-1)/(cross[-1]-cross[0])) if len(cross)>2 and amplitude>1e-5 else None
    im = v('imotional')[tail]
    supply = v('isupply')[tail]
    r = dict(name=a.name, c518062_qualified=False, points=len(t), end_s=float(t[-1]),
             tail_window_s=[float(tt[0]),float(tt[-1])],
             output_dc_v=mean, output_vpp=float(np.ptp(y)),
             output_ac_rms_v=np.sqrt(time_mean(tt,(y-mean)**2)),
             frequency_hz=freq, frequency_error_ppm=None if freq is None else (freq/31e6-1)*1e6,
             motional_current_rms_a=np.sqrt(time_mean(tt,im**2)),
             crystal_motional_power_w=time_mean(tt,im**2)*p['rm'],
             mean_supply_current_a=time_mean(tt,supply),
             mean_5v_rail_power_w=time_mean(tt,v('vcc')[tail]*supply),
             crystal_terminal_vpp=float(np.ptp(v('base')[tail])),
             interpretation='Exploratory single-mode model; not crystal or system acceptance')
    # 5 us windows distinguish supply transient, ring-down and growing oscillation.
    envelope=[]
    for start in np.arange(np.ceil(t[0]/5e-6)*5e-6,t[-1]-4.999e-6,5e-6):
        mask=(t>=start)&(t<start+5e-6)
        envelope.append({'start_us':float(start*1e6), 'emit_vpp':float(np.ptp(v('emit')[mask])),
                         'motional_peak_a':float(np.max(abs(v('imotional')[mask])))})
    r['envelope_5us']=envelope
    if len(envelope)>=4:
        last=np.array([x['emit_vpp'] for x in envelope[-4:]])
        r['last_four_envelopes_relative_span']=float(np.ptp(last)/np.mean(last)) if np.mean(last)>1e-9 else None
    # Explicitly require 100 us of evidence, ten equal windows, and drift checks.
    # A small span over just four 5 us windows is NOT a steady-state verdict.
    windows=[]
    if t[0] <= t[-1]-99.999e-6:
        for start in np.arange(t[-1]-100e-6,t[-1]-9.999e-6,10e-6):
            mask=(t>=start)&(t<=start+10e-6)
            tw=t[mask]; yw=v('emit')[mask]; dc=time_mean(tw,yw)
            iz=np.flatnonzero((yw[:-1]<dc)&(yw[1:]>=dc))
            cz=tw[iz]+(dc-yw[iz])*(tw[iz+1]-tw[iz])/(yw[iz+1]-yw[iz])
            fw=float((len(cz)-1)/(cz[-1]-cz[0])) if len(cz)>2 and np.ptp(yw)>1e-5 else None
            windows.append(dict(start_us=float(start*1e6),vpp=float(np.ptp(yw)),dc_v=dc,
                                frequency_hz=fw,crystal_w=time_mean(tw,v('imotional')[mask]**2)*p['rm']))
    r['tail_10us_windows']=windows
    gate={'scope':'Exploratory model only, not C518062 acceptance',
          'criteria':'last 100 us: Vpp span <1%, fitted drift <1%, f span <10 ppm, DC span <10 mV, crystal P span <2%',
          'passed':False,'reason':'insufficient saved duration or no periodic signal'}
    if len(windows)==10 and all(w['frequency_hz'] is not None for w in windows):
        av=np.array([w['vpp'] for w in windows]); fv=np.array([w['frequency_hz'] for w in windows])
        pv=np.array([w['crystal_w'] for w in windows]); dv=np.array([w['dc_v'] for w in windows])
        asp=float(np.ptp(av)/av.mean()); fsp=float(np.ptp(fv)/fv.mean()*1e6)
        drift=float(np.polyfit(np.arange(10)*10e-6,av,1)[0]*100e-6/av.mean())
        psp=float(np.ptp(pv)/pv.mean()) if pv.mean()>0 else 0
        gate.update(vpp_relative_span=asp, fitted_vpp_relative_drift_100us=drift,
                    frequency_span_ppm=fsp, dc_span_v=float(np.ptp(dv)), crystal_power_relative_span=psp,
                    passed=bool(asp<.01 and abs(drift)<.01 and fsp<10 and np.ptp(dv)<.01 and psp<.02),
                    reason='evaluated ten consecutive 10 us windows')
    r['steady_window_screen']=gate
    r['sha256']={ext:sha(OUT/(a.name+'.'+ext)) for ext in ('cir','cmd','raw','log','input.json')}
    (OUT/(a.name+'.result.json')).write_text(json.dumps(r, indent=2), encoding='utf-8')
    # Compact plot data retain extrema from the full resolution raw file.
    np.savez_compressed(OUT/(a.name+'.plot.npz'), envelope=envelope,
                        t_us=(tt[tt>=tt[-1]-.25e-6]-tt[-1])*1e6,
                        emit=y[tt>=tt[-1]-.25e-6],
                        base=v('base')[tail][tt>=tt[-1]-.25e-6])
    print(json.dumps({k:v for k,v in r.items() if k not in ('sha256','envelope_5us','tail_10us_windows')}, indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare','measure'])
    parser.add_argument('name')
    parser.add_argument('--cm-ff', type=float, default=10)
    parser.add_argument('--c0-pf', type=float, default=3)
    parser.add_argument('--rm', type=float, default=30)
    parser.add_argument('--fl-mhz', type=float, default=31)
    parser.add_argument('--cf-pf', type=float, default=33)
    parser.add_argument('--ce-pf', type=float, default=33)
    parser.add_argument('--stray-pf', type=float, default=1)
    parser.add_argument('--re', type=float, default=1000)
    parser.add_argument('--ramp-us', type=float, default=1)
    parser.add_argument('--step-ns', type=float, default=.5)
    parser.add_argument('--stop-us', type=float, default=200)
    parser.add_argument('--save-from-us', type=float, default=0)
    parser.add_argument('--no-motional', action='store_true')
    args=parser.parse_args()
    assert args.name.replace('_','').isalnum(), 'Use an ASCII case name.'
    if args.action=='prepare': prepare(args)
    else: measure(args)
