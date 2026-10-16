"""Small-signal start-up sensitivity; AC injection is a test fixture, not the oscillator.

Remove the motional branch and measure the impedance of active circuitry || C0.
Find Im(Zport + Zmotional) = 0; -Re(Zport) is the local Rm cancellation limit.
This linear check does not establish nonlinear steady state or qualify C518062.
"""
import json
import shutil
import sys
import numpy as np
from verify_oscillator import OUT, WORK, sha

NAME='lowdrive_port_ac'


def prepare():
    assert not (WORK/(NAME+'.log')).exists()
    source=(OUT/'lowdrive_1ms_tail.cir').read_text(encoding='ascii')
    skip=('VSUP ', 'VXM ', 'RXM ', 'LXM ', 'CXM ', 'HIMOT ')
    lines=[s for s in source.splitlines() if not s.startswith(skip) and s!='.end']
    lines[0]='* AC test fixture: 1 A small-signal injection; not a transient DUT'
    lines+=['VSUP vcc 0 5', 'ITEST 0 base DC 0 AC 1', '.end']
    (OUT/(NAME+'.cir')).write_text('\n'.join(lines)+'\n',encoding='ascii')
    cmd=(f'source {WORK.as_posix()}/{NAME}.cir\nbegin-scope page AC Analysis\n'
         'save $base\niplot $base\nac lin 4001 30.98meg 31.02meg\n'
         f'write-and-destroy-iplot "{WORK.as_posix()}/{NAME}.raw"\nend-scope\n')
    (OUT/(NAME+'.cmd')).write_text(cmd,encoding='ascii')
    for ext in ('cir','cmd'):
        shutil.copy2(OUT/(NAME+'.'+ext),WORK/(NAME+'.'+ext))


def measure():
    for ext in ('raw','log','status.json'):
        shutil.copy2(WORK/(NAME+'.'+ext),OUT/(NAME+'.'+ext))
    status=json.loads((OUT/(NAME+'.status.json')).read_text(encoding='utf-8-sig'))
    assert status['output_exists'] and status['state']==0 and not status.get('log_errors')
    text=(OUT/(NAME+'.raw')).read_text(encoding='ascii')
    values=text.split('Values:\n',1)[1]
    z=[]
    for s in values.splitlines():
        if s.strip():
            real,imag=s.split()[-1].split(',')
            z.append(complex(float(real),float(imag)))
    data=np.array(z).reshape(-1,2)
    freq=data[:,0].real; zp=data[:,1]; w=2*np.pi*freq
    rows=[]
    for cm_ff in (5,10,20):
        for c0_pf in (1,3,7):
            cm=cm_ff*1e-15; c0=c0_pf*1e-12
            fs=31e6/np.sqrt(1+cm/(c0+18e-12))
            lm=1/((2*np.pi*fs)**2*cm)
            # Original port model contains C0=3 pF; replace only that admittance.
            zc=1/(1/zp+1j*w*(c0-3e-12))
            imag=zc.imag+w*lm-1/(w*cm)
            roots=np.flatnonzero(imag[:-1]*imag[1:]<0)
            assert len(roots)==1,(cm_ff,c0_pf,len(roots))
            i=roots[0]; mix=-imag[i]/(imag[i+1]-imag[i])
            f=float(freq[i]+mix*(freq[i+1]-freq[i]))
            rneg=-float(zc.real[i]+mix*(zc.real[i+1]-zc.real[i]))
            for rm in (10,30,100):
                rows.append(dict(cm_ff=cm_ff,c0_pf=c0_pf,rm_ohm=rm,
                    linear_balance_frequency_hz=f,negative_resistance_ohm=rneg,
                    small_signal_margin_ratio=rneg/rm,
                    positive_linear_growth=rneg>rm))
    result=dict(c518062_qualified=False,fixture='5 V, RE=4.7k, CF=CE=33p, Cstray=1p; official historical BFR93A',
        assumptions='Cm=5/10/20 fF; C0=1/3/7 pF; Rm=10/30/100 ohm, exploratory values, NOT guaranteed device bounds',
        method='1 A AC current injected into base; Zport includes active stage and C0; solve Im(Zport+Zmotional)=0',
        interpretation='Small-signal growth only; not nonlinear convergence, drive-level or component acceptance',
        cases=rows,sha256={ext:sha(OUT/(NAME+'.'+ext)) for ext in ('cir','cmd','raw','log')})
    (OUT/(NAME+'.result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    if sys.argv[1]=='prepare': prepare()
    else: measure()
