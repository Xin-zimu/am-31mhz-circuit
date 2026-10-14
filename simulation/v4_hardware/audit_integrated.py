from pathlib import Path
import re,json,hashlib
import numpy as np
H=Path(__file__).resolve().parent
def read_gui(p):
    d={}
    for b in p.read_text().split('---- Trace:')[1:]:
        name=re.search(r'"([^"]+)"',b)[1].lower()
        a=np.array([list(map(float,l.split())) for l in b.splitlines()[1:] if l.strip() and not l.startswith('----')])
        d[name]=(a[:,0],a[:,1])
    return d
def block(s,key):
    m=re.search(r'(?<![A-Za-z])'+re.escape(key)+r'\{',s);start=m.start();depth=0
    for i in range(m.end()-1,len(s)):
        if s[i]=='{':depth+=1
        if s[i]=='}':
            depth-=1
            if depth==0:return s[start:i+1]
    raise ValueError(key)
def crossings(t,y,level,up=True):
    mask=(y[:-1]<level)&(y[1:]>=level) if up else (y[:-1]>=level)&(y[1:]<level)
    i=np.where(mask)[0]
    return t[i]+(level-y[i])/(y[i+1]-y[i])*(t[i+1]-t[i])
if __name__=='__main__':
    result={}
    for name,xml in [('LM393_20k_Stage1','lf_disk_audit.xml'),('AM_20k_31MHz_V4_Hardware','v4_disk_audit.xml')]:
        tr=block((H/xml).read_text(),'TRAN:list')
        result[name]={'initial_condition':re.search(r'IC:string\{([^}]*)',tr)[1],
                      'tstop_s':float(re.search(r'TSTOP:double\{([^}]*)',tr)[1]),
                      'sha256':hashlib.sha256((H/(name+'.ms14')).read_bytes()).hexdigest()}
        assert result[name]['initial_condition']=='zero_ic'
    d=read_gui(H/'results/native_am200us.txt')
    t,y=d['v(v1)'];assert t[-1]>=.0002*(1-1e-6)
    lo,hi=np.quantile(np.interp(np.linspace(50e-6,200e-6,10000),t,y),[.02,.98])
    ups=crossings(t,y,(lo+hi)/2);downs=crossings(t,y,(lo+hi)/2,False)
    ups=ups[ups>30e-6];period=np.diff(ups)
    widths=[downs[downs>x][0]-x for x in ups if np.any(downs>x)]
    result['integrated_v1']={'frequency_hz':float(1/period.mean()),'duty_pct':float(np.mean(widths)/period.mean()*100),'vpp':float(hi-lo),'low_v':float(lo),'high_v':float(hi),'points':len(t),'end_s':float(t[-1])}
    tr,rf=d['v(tp3)'];v1=np.interp(tr,t,y);env=.6+.1*v1
    normalized=rf/env
    # Fit the actual native RF waveform to the known 31 MHz carrier on all saved samples.
    m=tr>20e-6;tt=tr[m];z=normalized[m];basis=np.column_stack([np.sin(2*np.pi*31e6*tt),np.cos(2*np.pi*31e6*tt)])
    beta=np.linalg.lstsq(basis,z,rcond=None)[0];err=z-basis@beta
    result['am_modulation']={'carrier_hz':31e6,'carrier_fit_amplitude':float(np.linalg.norm(beta)),'normalized_rms_error':float(np.sqrt(np.mean(err**2))),
       'expected_low_envelope_peak_v':float(.6+.1*lo),'expected_high_envelope_peak_v':float(.6+.1*hi),'formula':'TP3=(0.6+0.1*V1)*sin(2*pi*31MHz*t)'}
    for node in ['v(tp6)','v(v2)']:
        tt,z=d[node];result[node]={'min_v':float(z.min()),'max_v':float(z.max()),'end_s':float(tt[-1]),'inside_0_to_9v':bool(z.min()>=-1e-3 and z.max()<=9.001)}
    (H/'results/integrated_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
