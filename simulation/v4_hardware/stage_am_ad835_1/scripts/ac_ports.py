"""DC operating-point AC impedance, explicitly not periodic steady-state Zout."""
import rf_study as L
import numpy as np
import json,re,subprocess
def one(top,port):
    name='ac_'+top+'_'+port
    s=L.SRC.read_text(encoding='utf8').split('.control')[0]
    s=s.replace('VSUP vcc 0 PWL(0 0 1u 5)','VSUP vcc 0 DC 5')
    s=re.sub(r'RLOADG out 0 .*\nCLOADG out 0 .*\n','',s)
    if top=='source':net='RDC out 0 1G\n'
    else:net=L.interface(top)[0]
    s+=net+f'\nITEST 0 {port} DC 0 AC 1\n'
    s+=f'''
.control
set filetype=binary
op
print v(b) v(e) v(bf) v(ef) v(bg) v(eg) v(cg) @q1[ic] @qb[ic] @qg[ic]
save v(out) v(y) v(z)
ac lin 1 31meg 31meg
write {name}.raw
quit
.endc
.end
'''
    path=L.ROOT/'netlists'/f'{name}.cir';path.write_text(s,encoding='utf8')
    with (L.ROOT/'results'/f'{name}.log').open('w') as f:
        r=subprocess.run([str(L.EXE),'-b',str(path)],cwd=L.ROOT/'results',stdout=f,stderr=subprocess.STDOUT,timeout=30)
    assert r.returncode==0
    b=(L.ROOT/'results'/f'{name}.raw').read_bytes();off=b.index(b'Binary:\n');h=b[:off].decode('latin1')
    names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+\s*$',h.rsplit('Variables:',1)[1],re.M)
    a=np.frombuffer(b,dtype=np.complex128,offset=off+8)
    data=dict(zip(names,a));z=data[f'v({port})']
    return dict(topology=top,port=port,z_real=float(z.real),z_imag=float(z.imag),
        z_abs=float(abs(z)),phase_deg=float(np.angle(z,deg=True)),
        definition='DC5 operating-point AC at31MHz; input RC included; NOT periodic steady-state output impedance',
        all_nodes={k:[float(v.real),float(v.imag)] for k,v in data.items()})
if __name__=='__main__':
    res=[one('source','out')]
    for top in ('A','A470','B','C_A','C_B','A470_AMB'):
        for port in ('y','z'):res.append(one(top,port))
    (L.ROOT/'results/ac_impedances.json').write_text(json.dumps(res,indent=2))
    print(json.dumps(res,indent=2))
