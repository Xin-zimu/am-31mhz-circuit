"""Generate and measure independent tests of the frozen Multisim POLY model.

Run with --prepare, execute both .cmd files with run_s04.ps1, then --measure.
The actual subcircuit is extracted verbatim, never reimplemented in the DUT.
"""
from pathlib import Path
import argparse, hashlib, json, shutil
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'poly_direct_20261016/verified'
WORK = Path('D:/ms_xsp/s04_poly_20261016/verified')
BASE = HERE.parent / 'repair_20261011/final_actual.cir'
FROZEN_SHA256 = 'd9aba8eff74e679f709bc6a680bf569e6dab87a00303b6ff138f19d4964ccaaf'
CASES = [(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,4,0),
         (.5,4,0),(-1,4,0),(1,-4,0),(1,4,7),(1,4,-7),(2,3,5)]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_raw(path):
    with path.open(encoding='ascii') as f:
        names=[]; variables=False
        for line in f:
            if line.strip()=='Variables:': variables=True; continue
            if line.strip()=='Values:': break
            if variables and line.strip(): names.append(line.split()[-1].lower())
        a=np.fromiter((float(s.split()[-1]) for s in f if s.strip()),dtype=float).reshape(-1,len(names))
    assert np.all(np.isfinite(a)) and np.all(np.diff(a[:,0])>=0)
    return names,a

def prepare():
    assert sha(BASE)==FROZEN_SHA256, 'Frozen S03 baseline changed; investigate before generating fixtures.'
    OUT.mkdir(exist_ok=True,parents=True); WORK.mkdir(exist_ok=True,parents=True)
    source=BASE.read_text(encoding='utf-8')
    start=source.index('.SUBCKT POLYSourceEAM_-EAM')
    end=source.index('.ENDS',start)+len('.ENDS')
    sub=source[start:end]
    text=['* S04 direct POLY truth table; original subcircuit unchanged',sub]
    for i,(c,m,z) in enumerate(CASES):
        text += [f'VC{i} c{i} 0 {c}',f'VM{i} m{i} 0 {m}',f'VZ{i} z{i} 0 {z}',
                 f'X{i} c{i} 0 m{i} 0 z{i} 0 y{i} 0 POLYSourceEAM_-EAM']
    # Two diagnostic outputs isolate the two non-zero original coefficients.
    text += ['VDC a 0 2','VDM b 0 3','VDZ z 0 5',
             'EP2 p2 0 POLY(3) (a,0) (b,0) (z,0) 0 0.6 0 0 0 0 0 0 0 0 0 0 0 0 0',
             'EP6 p6 0 POLY(3) (a,0) (b,0) (z,0) 0 0 0 0 0 0.1 0 0 0 0 0 0 0 0 0',
             'Xfloat a 0 b 0 floating5 floating6 yf 0 POLYSourceEAM_-EAM','.end']
    write_case('truth_table','\n'.join(text),' '.join('$y'+str(i) for i in range(len(CASES)))+' $p2 $p6 $yf','tran 1n 20n 0 1n')
    rf='\n'.join(['* S04 POLY 31 MHz transient; original model unchanged',sub,
        'VC c 0 sin(0 1 31meg)','VCH ch 0 sin(0 .5 31meg)',
        'VM m 0 sin(2 2 20k)',
        'Xfull c 0 m 0 f5 f6 y 0 POLYSourceEAM_-EAM',
        'Xhalf ch 0 m 0 h5 h6 yh 0 POLYSourceEAM_-EAM','.end'])
    write_case('rf_transfer',rf,'$c $ch $m $y $yh','tran .5n 50u 0 .5n')
    write_case('rf_refined',rf,'$c $ch $m $y $yh','tran .25n 50u 0 .25n')
    (OUT/'inputs.json').write_text(json.dumps({'baseline_sha256':sha(BASE),'cases':CASES,'subcircuit':sub},indent=2),encoding='utf-8')

def write_case(name,net,signals,analysis):
    (OUT/(name+'.cir')).write_text(net+'\n',encoding='ascii')
    shutil.copy2(OUT/(name+'.cir'),WORK/(name+'.cir'))
    cmd=f'source {WORK.as_posix()}/{name}.cir\nbegin-scope page Transient Analysis\nsave {signals}\niplot {signals}\n{analysis}\nwrite-and-destroy-iplot "{WORK.as_posix()}/{name}.raw"\nend-scope\n'
    (OUT/(name+'.cmd')).write_text(cmd,encoding='ascii')
    shutil.copy2(OUT/(name+'.cmd'),WORK/(name+'.cmd'))

def measure():
    assert sha(BASE)==FROZEN_SHA256, 'Frozen baseline changed.'
    for name in ['truth_table','rf_transfer','rf_refined']:
        for ext in ['raw','log','status.json']:
            path=WORK/(name+'.'+ext)
            if path.exists(): shutil.copy2(path,OUT/path.name)
        status=json.loads((OUT/(name+'.status.json')).read_text(encoding='utf-8-sig'))
        assert status['state']==0 and not status['last_error'] and status['output_exists'], (name,status)
    n,a=read_raw(OUT/'truth_table.raw')
    assert abs(a[-1,0]-20e-9)<1e-15
    rows=[]
    for i,(c,m,z) in enumerate(CASES):
        measured=float(a[-1,n.index(f'v(y{i})')]); expected=.6*c+.1*c*m
        rows.append(dict(vc=c,vm=m,v3=z,measured_v=measured,expected_v=expected,error_v=measured-expected,old_formula_v=.6*m+.1*m*c))
    nr,ar=read_raw(OUT/'rf_transfer.raw')
    assert abs(ar[-1,0]-50e-6)<1e-13
    c=ar[:,nr.index('v(c)')]; m=ar[:,nr.index('v(m)')]
    y=ar[:,nr.index('v(y)')]; yh=ar[:,nr.index('v(yh)')]
    # Coherent 50 us record contains 1 modulation period and 1550 carrier periods.
    grid=np.arange(0,50e-6,.5e-9)
    yi=np.interp(grid,ar[:,0],y)
    amplitudes={str(f):float(2*abs(np.mean(yi*np.exp(-2j*np.pi*f*grid)))) for f in [20e3,30.98e6,31e6,31.02e6]}
    result={'date':'2026-10-16','solver':'Multisim 14.3 XSPICE command interface; independent fixture, not GUI/full system',
        'formula':'TP3 = 0.6*Vc + 0.1*Vc*Vm = Vc*(0.6+0.1*Vm)',
        'truth_table':rows,'isolated_p2_v':float(a[-1,n.index('v(p2)')]),'isolated_p6_v':float(a[-1,n.index('v(p6)')]),
        'original_floating_third_input_v':float(a[-1,n.index('v(yf)')]),
        'rf':{'points':len(ar),'end_s':float(ar[-1,0]),'max_formula_error_v':float(np.max(abs(y-(.6+.1*m)*c))),
            'max_half_carrier_error_v':float(np.max(abs(yh-.5*y))),'spectral_peak_v':amplitudes},
        'baseline_unchanged':sha(BASE)==json.loads((OUT/'inputs.json').read_text())['baseline_sha256'],
        'sha256':{p.name:sha(p) for p in OUT.iterdir() if p.suffix in ['.raw','.cir','.cmd','.log']}}
    nf,af=read_raw(OUT/'rf_refined.raw')
    assert abs(af[-1,0]-50e-6)<1e-13
    cf=af[:,nf.index('v(c)')]; mf=af[:,nf.index('v(m)')]; yf=af[:,nf.index('v(y)')]
    fine_error=float(np.max(abs(yf-(.6+.1*mf)*cf)))
    fine_grid=np.arange(0,50e-6,.25e-9); yfi=np.interp(fine_grid,af[:,0],yf)
    fine_spectrum={str(f):float(2*abs(np.mean(yfi*np.exp(-2j*np.pi*f*fine_grid)))) for f in [20e3,30.98e6,31e6,31.02e6]}
    result['rf_refined']={'points':len(af),'end_s':float(af[-1,0]),'max_formula_error_v':fine_error,'spectral_peak_v':fine_spectrum}
    # Transient interpolation is numerical, unlike the exact constant-input tests.
    # Verify refinement reduces its residual and resolves 0.8/0.1/0.1 V components.
    result['acceptance']={'dc_abs_tolerance_v':1e-8,'transient_abs_tolerance_v':5e-6,'spectral_relative_tolerance':.002,'requires_refinement_improvement':True}
    result['passed']=bool(max(abs(r['error_v']) for r in rows)<1e-8 and result['rf']['max_formula_error_v']<5e-6 and fine_error<result['rf']['max_formula_error_v'] and result['rf']['max_half_carrier_error_v']<1e-8 and result['baseline_unchanged'] and all(abs(fine_spectrum[str(f)]/amp-1)<.002 for f,amp in [(30.98e6,.1),(31e6,.8),(31.02e6,.1)]))
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--prepare',action='store_true'); p.add_argument('--measure',action='store_true'); args=p.parse_args()
    if args.prepare: prepare()
    if args.measure: measure()
