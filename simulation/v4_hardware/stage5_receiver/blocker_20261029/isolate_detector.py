"""Causal control: fixed wanted RF spectrum, linear addition of CW, real BAT85.
Ideal voltage source is a diagnostic intervention, not a proposed receiver.
"""
import json
import numpy as np
from run_diagnosis import *

def run(name,f,a,rs=0):
    c=config(blockers=[[f,a,0]],isolation=True,detector_source_ohm=rs)
    base=json.loads((HERE/'results/R2_clean.json').read_text())['metrics']['nodes']['rf']['spectral_complex']
    blk=json.loads((HERE/f'results/R2_{int(f/1e6)}_10.json').read_text())['metrics']['nodes']['rf']['spectral_complex'][str(int(f))]
    # Wanted RF terms are identical in every paired comparison. Add only CW.
    terms=[]
    for freq in [30.98e6,31e6,31.02e6]:
        z=complex(*base[str(int(freq))])
        terms.append(f'{abs(z):.15g}*cos(2*pi*{freq:.15g}*time+{np.angle(z):.15g})')
    z=complex(*blk)*a/.01
    terms.append(f'{abs(z):.15g}*cos(2*pi*{f:.15g}*time+{np.angle(z):.15g})')
    net='* Fixed wanted waveform + independent CW -> real BAT85 control\n'
    net+='BREPLAY drive 0 V='+'+'.join(terms)+'\n'
    net+=f'RS drive rf {max(rs,1e-6)}\n'
    net+=old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=100000))+old.old.models()
    net+='''
.options method=trap reltol=1e-4 trtol=3 abstol=1p vntol=1u temp=27
.control
set filetype=binary
save v(rf) v(det) v(out)
tran 0.5n 200u 100u 0.5n
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,net,c);r['metrics']=measure(d,c);save(r)
    print(name,r['metrics']['nodes']['out']['spectral_peak']['20000'],flush=True)

if __name__=='__main__':
    for rs in [0,50]:
        run(f'D_rs{rs}_clean',29e6,0,rs)
        for f in [29e6,33e6]:
            for a in [.003,.006,.01]:run(f'D_rs{rs}_{int(f/1e6)}_{a*1000:g}',f,a,rs)
