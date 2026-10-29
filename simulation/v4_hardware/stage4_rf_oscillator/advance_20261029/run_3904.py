"""Independent 2N3904 assembly-model screening, not a hardware qualification."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess, time, urllib.request
import numpy as np

HERE=Path(__file__).resolve().parent
WORK=Path('D:/ms_xsp/s04_3904_20261029')
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
URL='https://home.uncg.edu/~ehhellen/spice_stuff.html'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def model():
    src=HERE/'uncg_spice_stuff.html'
    if not src.exists():
        src.write_bytes(urllib.request.urlopen(URL,timeout=45).read())
    content=src.read_text(errors='replace')
    m=re.search(r'\.model\s+2N3904\s+NPN\(.*?\)',content,re.I|re.S)
    assert m, 'Expected model not found in source'
    mdl=m.group().replace('\r','')
    assert 'Tf=301.2p' in mdl and 'Bf=416.4' in mdl
    (HERE/'2N3904_UNCG.lib').write_text(mdl+'\n',encoding='ascii')
    return mdl,sha(src)

def readraw(p):
    with p.open('rb') as f:
        header=[];names=[];inside=False
        while True:
            s=f.readline().decode('ascii').strip()
            if s=='Binary:':break
            header.append(s)
            if s=='Variables:':inside=True;continue
            if inside and s:names.append(s.split()[1].lower())
        a=np.fromfile(f,dtype='<f8').reshape(-1,len(names))
    assert np.isfinite(a).all() and np.all(np.diff(a[:,0])>=0)
    assert len(a)==int(next(s.split(':')[1] for s in header if s.startswith('No. Points:')))
    return dict(zip(names,a.T))

def metrics(d,start,stop,rm):
    mask=(d['time']>=start)&(d['time']<=stop)
    t=d['time'][mask];e=d['v(e)'][mask]
    def mean(x):return float(np.trapezoid(x,t)/(t[-1]-t[0]))
    dc=mean(e);v=e-dc;idx=np.where((v[:-1]<=0)&(v[1:]>0))[0]
    crossings=t[idx]-v[idx]*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])
    freq=float((len(crossings)-1)/(crossings[-1]-crossings[0])) if len(idx)>10 else None
    return dict(vpp=float(np.ptp(e)),dc=dc,frequency_hz=freq,
                sense_vpp=float(np.ptp(d['v(sense)'][mask])),
                crystal_power_w=rm*mean(d['i(vxm)'][mask]**2),
                supply_power_w=-mean(d['v(vcc)'][mask]*d['i(vsup)'][mask]),
                base_dc=mean(d['v(b)'][mask]))

def run(a):
    WORK.mkdir(parents=True,exist_ok=True)
    assert re.fullmatch(r'[a-z0-9_]+',a.name)
    raw=WORK/(a.name+'.raw');log=WORK/(a.name+'.log')
    assert not raw.exists() and not (HERE/(a.name+'.result.json')).exists(), 'Use a new name'
    mdl,srchash=model()
    cm=a.cm*1e-15;c0=a.c0*1e-12
    fs=31e6/np.sqrt(1+cm/(18e-12+c0));lm=1/((2*np.pi*fs)**2*cm)
    net=f'''* 2N3904 experimental perfboard R1 screening; no hardware qualification
* UNCG public educational 2N3904 model, not a model of the delivered transistor lot
* C518062 BVD values and fundamental mode assumed, not measured
VSUP vcc 0 PWL(0 0 1u 5)
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
C3 vcc 0 100n
C4 vcc 0 10u
CSTRAY b 0 {a.stray}p
CX0 b 0 {a.c0}p
VXM b xr 0
RM xr xl {a.rm}
LM xl xc {lm:.16g}
CM xc 0 {a.cm}f
* 10X probe represented as 10 Mohm || 12 pF at SENSE; approximate, not instrument-specific
RPROBE sense 0 10meg
CPROBE sense 0 12p
'''
    if a.c5>0:net+=f'C5 e sense {a.c5}p\n'
    net+=mdl+f'''
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=binary
set num_threads=1
save v(vcc) v(b) v(e) v(sense) i(vsup) i(vxm)
tran {a.step}n {a.stop}m {a.stop-.1}m {a.step}n uic
write {raw.as_posix()}
quit
.endc
.end
'''
    src=HERE/(a.name+'.cir');src.write_text(net,encoding='ascii')
    local=WORK/(a.name+'.cir');local.write_text(net,encoding='ascii')
    inp=vars(a).copy();inp.update(model_source=URL,source_sha256=srchash,net_sha256=sha(src),
        simulator_sha256=sha(EXE),fs_hz=float(fs),lm_h=float(lm),probe_r_ohm=10e6,probe_c_pf=12,
        c518062_qualified=False,delivered_transistor_model_verified=False,
        ideal_voltage_supply=True,physical_layout_parasitics_extracted=False)
    (HERE/(a.name+'.input.json')).write_text(json.dumps(inp,indent=2),encoding='utf-8')
    t0=time.monotonic()
    p=subprocess.run([str(EXE),'-b','-n','-o',str(log),str(local)],cwd=WORK,
        capture_output=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    seconds=time.monotonic()-t0
    txt=log.read_text(errors='replace');(HERE/(a.name+'.log')).write_text(txt,encoding='utf-8')
    assert p.returncode==0 and raw.exists() and not re.search(r'^\s*(error|fatal)',txt,re.I|re.M), txt[-2000:]
    d=readraw(raw);end=a.stop*1e-3
    windows=[metrics(d,end-100e-6+i*10e-6,end-100e-6+(i+1)*10e-6,a.rm) for i in range(10)]
    tail=metrics(d,end-20e-6,end,a.rm)
    vv=np.array([w['vpp'] for w in windows]);pp=np.array([w['crystal_power_w'] for w in windows])
    ff=np.array([w['frequency_hz'] or 0 for w in windows]);dc=np.array([w['dc'] for w in windows])
    checks=dict(vpp_span=float(np.ptp(vv)/max(np.mean(vv),1e-30)),
        vpp_drift_100us=float(np.polyfit(np.arange(10)*10e-6,vv,1)[0]*100e-6/max(np.mean(vv),1e-30)),
        frequency_span_ppm=float(np.ptp(ff)/max(np.mean(ff),1)*1e6),dc_span_v=float(np.ptp(dc)),
        crystal_power_span=float(np.ptp(pp)/max(np.mean(pp),1e-30)))
    signal=bool(tail['vpp']>.001 and tail['frequency_hz'] is not None)
    passed=bool(signal and checks['vpp_span']<.01 and abs(checks['vpp_drift_100us'])<.01
        and checks['frequency_span_ppm']<10 and checks['dc_span_v']<.01 and checks['crystal_power_span']<.02)
    out=dict(name=a.name,seconds=seconds,points=len(d['time']),tail=tail,windows=windows,
        steady_screen=checks,steady_screen_pass=passed,signal_detected=signal,
        raw_path=str(raw),raw_sha256=sha(raw),input=inp)
    (HERE/(a.name+'.result.json')).write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ['name','seconds','tail','steady_screen','steady_screen_pass']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--c5',type=float,default=2.2)
    p.add_argument('--rm',type=float,default=30);p.add_argument('--cm',type=float,default=10)
    p.add_argument('--c0',type=float,default=3);p.add_argument('--stray',type=float,default=1)
    p.add_argument('--step',type=float,default=.125);p.add_argument('--stop',type=float,default=2)
    run(p.parse_args())
