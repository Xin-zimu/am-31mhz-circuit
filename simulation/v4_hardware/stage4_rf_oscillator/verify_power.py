"""Partial TX power evidence; never treats missing RF stages as zero power.

Extract the unchanged LF circuit and measure its supply current using an ideal
CCVS monitor (1 V at IMON represents 1 A drawn). Validate the sign/scale with
a separate 5 V / 1 kohm fixture. Regulator losses are budget arithmetic, not a
regulator macro-model or complete transmitter acceptance.
"""
from pathlib import Path
import argparse, hashlib, json, shutil
import numpy as np
from verify_poly import read_raw, sha, BASE, FROZEN_SHA256

HERE=Path(__file__).resolve().parent
OUT=HERE/'power_20261016'
WORK=Path('D:/ms_xsp/s04_power_20261016')

def write_case(name,net,signals,tran):
    (OUT/(name+'.cir')).write_text(net,encoding='ascii')
    cmd=f'source {WORK.as_posix()}/{name}.cir\nbegin-scope page Transient Analysis\nsave {signals}\niplot {signals}\n{tran}\nwrite-and-destroy-iplot "{WORK.as_posix()}/{name}.raw"\nend-scope\n'
    (OUT/(name+'.cmd')).write_text(cmd,encoding='ascii')
    for ext in ['cir','cmd']: shutil.copy2(OUT/(name+'.'+ext),WORK/(name+'.'+ext))

def prepare():
    assert sha(BASE)==FROZEN_SHA256, 'Frozen S03 baseline changed.'
    OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    text=BASE.read_text(encoding='utf-8').split('*## Multisim Component VCC ##*')[0]
    # Explicit zero-to-5 V ramp charges the original 10.1 uF bypass capacitors.
    text=text.replace('vV5 V5 0 dc 5 ac 0 0\n+           distof1 0 0\n+           distof2 0 0',
        'vV5 V5 0 PWL(0 0 10u 5 2m 5)')
    text+='\n* Ideal readout only: positive IMON = current delivered by VV5\nHMON IMON 0 vV5 -1\n.end\n'
    write_case('lf_nominal',text,'$v5 $v1 $imon','tran 10n 2m 0 10n uic')
    write_case('monitor_control','* Current monitor polarity and scale control\nVV5 V5 0 5\nRTEST V5 0 1k\nHMON IMON 0 VV5 -1\n.end\n','$v5 $imon','tran 1n 20n 0 1n')
    (OUT/'inputs.json').write_text(json.dumps({'baseline_sha256':sha(BASE),'regulator':'ST L7805CV','regulator_iq_budget_a':.008,
        'regulator_iq_basis':'ST L78 Rev38 Table10: 8mA max at TJ=25C; not a full-temperature bound',
        'unknown_stages':['31MHz oscillator','buffer/calibration','real AM modulator','PA/matching','battery-direct TX loads'],
        'note':'All unknown stages remain null. No complete-TX pass is inferred.'},indent=2),encoding='utf-8')

def integrate(t,y):
    return float(np.trapezoid(y,t)/(t[-1]-t[0]))

def measure():
    assert sha(BASE)==FROZEN_SHA256, 'Frozen baseline changed.'
    for name in ['lf_nominal','monitor_control']:
        for ext in ['raw','log','status.json']:
            shutil.copy2(WORK/(name+'.'+ext),OUT/(name+'.'+ext))
        status=json.loads((OUT/(name+'.status.json')).read_text(encoding='utf-8-sig'))
        assert status['state']==0 and not status['last_error'] and status['output_exists'], (name,status)
    nc,ac=read_raw(OUT/'monitor_control.raw')
    control=float(ac[-1,nc.index('v(imon)')]); assert abs(control-.005)<1e-10
    n,a=read_raw(OUT/'lf_nominal.raw'); t=a[:,0]
    assert abs(t[-1]-.002)<1e-12
    current=a[:,n.index('v(imon)')]; voltage=a[:,n.index('v(v5)')]; v1=a[:,n.index('v(v1)')]
    tail=(t>=.0015); tt=t[tail]; ii=current[tail]; vv=voltage[tail]
    i5=integrate(tt,ii); p5=integrate(tt,ii*vv)
    level=(v1[tail].min()+v1[tail].max())/2
    k=np.flatnonzero((v1[:-1]<level)&(v1[1:]>=level))
    crosses=t[k]+(level-v1[k])*(t[k+1]-t[k])/(v1[k+1]-v1[k]); crosses=crosses[crosses>=.0015]
    b,e=crosses[-6],crosses[-1]
    grid=np.r_[b,t[(t>b)&(t<e)],e]
    ci=np.interp(grid,t,current); cv=np.interp(grid,t,voltage)
    i5=integrate(grid,ci); p5=integrate(grid,ci*cv)
    budget=[]
    for vb in [7.5,9,9.6]:
        budget.append({'battery_voltage_v':vb,'iq_assumed_a':.008,'max_5v_plus_direct_load_a_at_0p5w':.5/vb-.008,
            'lf_plus_regulator_only_battery_w':vb*(i5+.008),
            'lf_plus_regulator_only_loss_w':vb*(i5+.008)-p5,
            'remaining_unassigned_current_a':.5/vb-.008-i5})
    result={'date':'2026-10-16','solver':'Multisim 14.3 XSPICE command interface; isolated LF fixture',
        'status':'PARTIAL_MODEL_ONLY','entire_tx_battery_power_w':None,'entire_tx_passed':None,
        'current_monitor_control_a':control,'initial':'UIC, all capacitors zero; 0 to 5V linear supply ramp over 10us',
        'points':len(a),'end_s':float(t[-1]),'tail_window_s':[float(b),float(e)],'complete_cycles':5,
        'lf_i5_mean_a':i5,'lf_p5_mean_w':p5,'tail_peak_current_a':float(ci.max()),
        'startup_peak_current_a':float(current.max()),'source_energy_first_10us_j':float(np.trapezoid((current*voltage)[t<=10e-6],t[t<=10e-6])),
        'v1_frequency_hz':float(5/(e-b)),'v1_raw_vpp':float(np.ptp(v1[tail])),
        'linear_regulator_budget_scenarios':budget,'baseline_sha256':sha(BASE),
        'limitations':['LF macro-model supply current is not validated against physical LM393P over temperature.',
            'No oscillator, buffer, modulator or PA current has been measured.',
            '8mA is L7805C max at specified 25C conditions, not full-temperature guaranteed total.',
            'L7805C regulation requires at least 5mA total load; LF alone is below this. Budget terms assume a complete transmitter meets that condition.',
            'Power-up peak uses an ideal ramp source, not a 7805 startup model.',
            '7.5V and 9.6V are illustrative battery-voltage scenarios, not a battery specification.'],
        'sha256':{p.name:sha(p) for p in OUT.iterdir() if p.suffix in ['.raw','.cir','.cmd','.log']}}
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--measure',action='store_true');a=p.parse_args()
    if a.prepare: prepare()
    if a.measure: measure()
