"""C4 oscillator + real passive/BJT interface studies, NOT an AD835 model.

Y/Z load fixture: typical R/C plus independent signed DC current sources.
Z has no guaranteed maximum in the datasheet: 100uA is a stress assumption.
"""
from pathlib import Path
import hashlib,json,re,subprocess,concurrent.futures as cf,csv,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];HW=ROOT.parent
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
SRC=HW/'stage4_rf_oscillator/S04_RF_CARRIER/XTAL/c4_dual_load_20261030/netlists/c4_trap_0p125n_2k_rtol1e5.cir'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def snapshot():
    roots=[HW/'stage_am_ad835',HW/'stage4_rf_oscillator/AM01_2N3904_20261113',
      HW/'stage4_rf_oscillator/AM02_2_first_stage_20261113',HW/'stage4_rf_oscillator/AM02_3_second_stage_20261113',SRC.parent,HW/'repair_20261011']
    return {str(p.relative_to(HW)):sha(p) for root in roots for p in root.rglob('*')
      if p.is_file() and '__pycache__' not in p.parts}
def read_raw(p):
    b=p.read_bytes();off=b.index(b'Binary:\n');h=b[:off].decode('latin1')
    nv=int(re.search(r'No\. Variables:\s+(\d+)',h)[1]);n=int(re.search(r'No\. Points:\s+(\d+)',h)[1])
    names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+\s*$',h.rsplit('Variables:',1)[1],re.M)
    assert len(names)==nv
    a=np.frombuffer(b,dtype=np.float64,count=nv*n,offset=off+8).reshape(n,nv)
    return dict(zip(names,a.T))
def run(name,s):
    cir=ROOT/'netlists'/f'{name}.cir';cir.write_text(s,encoding='utf8')
    with (ROOT/'results'/f'{name}.log').open('w') as log:
        p=subprocess.run([str(EXE),'-b',str(cir)],cwd=ROOT/'results',stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    if p.returncode:raise RuntimeError(name+' failed')
    return read_raw(ROOT/'results'/f'{name}.raw')
def mean(t,x):return float(np.trapezoid(x,t)/(t[-1]-t[0]))
def fit(t,y,f):
    ts=t-t[0];m=np.column_stack([np.ones(len(t))]+[fn(2*np.pi*k*f*ts) for k in range(1,6) for fn in (np.cos,np.sin)])
    co=np.linalg.lstsq(m,y,rcond=None)[0];z=co[1::2]-1j*co[2::2];a=np.abs(z)
    return dict(dc=float(co[0]),vpp=float(np.ptp(y)),min=float(y.min()),max=float(y.max()),
        fundamental_vpp=float(2*a[0]),phase_deg=float(np.angle(z[0],deg=True)),
        thd=float(np.linalg.norm(a[1:])/a[0])),z[0]
def interface(top,iy=0,iz=0,r=2000,c=10e-12):
    if top=='load':return f'RLOADG out 0 {r}\nCLOADG out 0 {c}\nVY out y 0\nVZ y z 0\n',False
    if top=='direct':net='VY out y 0\nVZ y z 0\n'
    elif top in ('A','A470','A560','A470_AMB'):
        rs=330 if top=='A' else 560 if top=='A560' else 470
        net=f'RS out a {rs}\nRP a 0 680\nVY a y 0\n'
        net+='RZT a z 100\nRZB z 0 150.37593985\n' if top=='A470_AMB' else 'VZ a z 0\n'
    elif top=='B':net='''CBI out atten 10n
RSB atten rb 1000
RPB rb 0 1000
CB2 rb base 10n
RBT2 vcc base 10k
RBB2 base 0 10k
QBUF vcc base emit 2N3904
REB2 emit 0 330
CBO emit a 10n
RRETURN a 0 680
VY a y 0
VZ a z 0
'''
    elif top in ('C_A','C_B'):
        rz=330 if top=='C_A' else 1000
        net=f'RSY out y 330\nRBY y 0 680\nRSZ out z {rz}\nRBZ z 0 680\n'
    elif top=='B_Z06':
        # Buffered Y=Vc plus a real 0.6 Z tap (scheme B carrier connection).
        net='''CBI out atten 10n
RSB atten rb 1000
RPB rb 0 1000
CB2 rb base 10n
RBT2 vcc base 10k
RBB2 base 0 10k
QBUF vcc base emit 2N3904
REB2 emit 0 330
CBO emit a 10n
RRETURN a 0 680
VY a y 0
RZT a z 100
RZB z 0 150.37593985
'''
    elif top in ('CAP_ONLY','CAP_1K'):
        # DC-floating demonstration: COUTG blocks DC, no low-Z bias return.
        net='CBLK out y 10n\nVZ y z 0\n'
        if top=='CAP_1K':net+='RD y 0 1000\n'
    else:raise ValueError(top)
    net+=f'''* INPUT FIXTURE ONLY: not an AD835 macro-model
RY y 0 100k
CY y 0 2p
RZ z 0 60k
CZ z 0 2p
IY y 0 {iy}
IZ z 0 {iz}
'''
    return net,top=='B'
def build(name,top,iy=0,iz=0,r=2000,c=10e-12,step=.25,stop=2.5,start=2.45,startup=False):
    s=SRC.read_text(encoding='utf8').split('.control')[0]
    s=re.sub(r'RLOADG out 0 .*\nCLOADG out 0 .*\n','VSENSE out tp 0\n',s)
    net,buf=interface(top,iy,iz,r,c)
    # Every external interface connects to tp, preserving out as the original TP2.
    net=re.sub(r'\bout\b','tp',net)
    nodes='v(out) v(y) v(z) v(e) v(b) v(bf) v(ef) v(bg) v(eg) v(cg) i(vsup) i(vsense)'
    if buf:nodes+=' v(base) v(emit)'
    if startup:nodes='v(out) v(e)'
    s+=net+f'''
.control
set filetype=binary
set num_threads=1
op
print v(b) v(e) v(bf) v(ef) v(bg) v(eg) v(cg) @q1[ic] @qb[ic] @qg[ic]
save {nodes}
tran 0.5n {stop}m {0 if startup else start}m {step}n uic
write {name}.raw
quit
.endc
.end
'''
    return s
def measure(name,d,settings):
    t=d['time'];y=d['v(out)'];m=t>t[-1]-10e-6;t1=t[m];y1=y[m]
    zero=mean(t1,y1);idx=np.where((y1[:-1]<zero)&(y1[1:]>=zero))[0]
    cross=t1[idx]+(zero-y1[idx])*(t1[idx+1]-t1[idx])/(y1[idx+1]-y1[idx]);f=float(1/np.mean(np.diff(cross)))
    result=dict(name=name,**settings,frequency_hz=f,status='C4_INTERFACE_FIXTURE_ONLY')
    ph={}
    for node in ('out','y','z'):
        res,z=fit(t1,d[f'v({node})'][m],f);result[node]=res;ph[node]=z
    result['y_phase_relative_tp2_deg']=float(np.angle(ph['y']/ph['out'],deg=True))
    result['z_phase_relative_y_deg']=float(np.angle(ph['z']/ph['y'],deg=True))
    result['z_y_amplitude_ratio']=float(abs(ph['z']/ph['y']))
    _,icur=fit(t1,d['i(vsense)'][m],f)
    zin=ph['out']/icur
    result['interface_zin_ohm']=[float(zin.real),float(zin.imag)]
    result['supply_mw']=-5000*mean(t,d['i(vsup)'])
    result['y_within_nominal_1V']=max(abs(result['y']['min']),abs(result['y']['max']))<=1
    windows=[]
    for a,b in ((t[-1]-50e-6,t[-1]-25e-6),(t[-1]-25e-6,t[-1])):
        mask=(t>=a)&(t<=b);windows.append(float(np.ptp(y[mask])))
    result['last_windows_vpp']=windows;result['last_window_drift']=abs(windows[1]-windows[0])/windows[1]
    result['dc_nodes']={k:mean(t,v) for k,v in d.items() if k.startswith('v(')}
    result['q_vce_min']={'Q1':float(5-d['v(e)'].max()),'QB':float(5-d['v(ef)'].max()),'QG':float(np.min(d['v(cg)']-d['v(eg)']))}
    if 'v(emit)' in d:result['q_vce_min']['QBUF']=float(5-d['v(emit)'].max())
    result['netlist_sha256']=sha(ROOT/'netlists'/f'{name}.cir')
    (ROOT/'results'/f'{name}.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(name,'TP2',result['out']['vpp'],'Y',result['y']['vpp'],'peak',max(abs(result['y']['min']),abs(result['y']['max'])),'mW',result['supply_mw'],flush=True)
    return result
def job(name,**kw):
    d=run(name,build(name,**kw));return measure(name,d,kw)
def main():
    before=snapshot();(ROOT/'sources/protected_before.json').write_text(json.dumps(before,indent=2,ensure_ascii=False),encoding='utf8')
    (ROOT/'sources/C4_original.cir').write_bytes(SRC.read_bytes())
    jobs=[('load_1k_4p',dict(top='load',r=1000,c=4e-12)),('load_2k_4p',dict(top='load',r=2000,c=4e-12)),
          ('load_2k_10p',dict(top='load',r=2000,c=10e-12)),('load_10k_4p',dict(top='load',r=10000,c=4e-12)),
          ('load_37k5_4p',dict(top='load',r=37500,c=4e-12)),
          ('A_nom',dict(top='A',iy=10e-6,iz=50e-6)),('B_nom',dict(top='B',iy=10e-6,iz=50e-6)),
          ('C_A_nom',dict(top='C_A',iy=10e-6,iz=50e-6)),('C_B_nom',dict(top='C_B',iy=10e-6,iz=50e-6))]
    with cf.ThreadPoolExecutor(3) as pool:
        fs=[pool.submit(job,n,**k) for n,k in jobs]
        for f in cf.as_completed(fs):f.result()
    after=snapshot();assert before==after
    (ROOT/'results/protection_check.json').write_text(json.dumps(dict(files=len(before),changed=[])),encoding='utf8')
if __name__=='__main__':main()
