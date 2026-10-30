"""S05-07: loaded LC tuning; historical raw reuse + new short AC fixtures.

No transient or historical runner main is invoked. RF transistor values stay fixed.
Analytic search is distinguished from full ngspice verification in every record.
"""
from pathlib import Path
import sys, json, itertools
import numpy as np
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
sys.path.insert(0, str(STAGE/'blocker_20261029'))
import run_diagnosis as d
d.HERE = HERE
d.WORK = Path('D:/ms_xsp/s05_lc_20261030')
fixed, sha = d.fixed, d.sha
PREV = STAGE/'gain_20261030'
BASE = dict(l1=470., l2=470., q1=50., q2=50., cp1=1., cp2=1.,
            ct1=39.59, ct2=45.83, cs=14.529, co=10.81, ck=2.485,
            rs=50., coil='constant_esr', board1=0., board2=0.)


def dump(path, value):
    fixed(path, (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8'))


class LoadedNetwork:
    """Extract fixed amplifier port admittance/transfer from archived C_Q50 raw."""
    def __init__(self):
        self.record = json.loads((PREV/'results/C_Q50.json').read_text())
        self.path = Path(self.record['raw_path'])
        assert sha(self.path) == self.record['raw_sha256']
        r = d.readraw(self.path)
        self.f = r['frequency'].real
        self.ref = r['v(rf)']
        # Includes RPORT 1 MOhm; no 50 Ohm load is substituted for Q1.
        self.yload = 2j*np.pi*self.f*10.81e-12*(r['v(tank2)']-r['v(port)'])/r['v(port)']
        self.amp = r['v(rf)']/r['v(port)']
        self.raw = r

    @staticmethod
    def coil_z(f, p, i):
        w = 2*np.pi*f
        l = p[f'l{i}']*1e-9
        if p['coil'] == 'coilcraft_1008cs':
            # Official Document 158-1/2, 2026-04-30: R2 + [(Rvar+jwL)||(R1+1/jwC)].
            z = 1.2 + 1/(1/(4.27e-4*np.sqrt(f)+1j*w*l)+1/(31+1/(1j*w*.156e-12)))
        else:
            z = 1/(1/(2*np.pi*31e6*l/p[f'q{i}']+1j*w*l)+1j*w*p[f'cp{i}']*1e-12)
        return z

    def response(self, p, f=None):
        f = self.f if f is None else np.asarray(f, dtype=float)
        w = 2*np.pi*f
        yl = np.interp(f, self.f, self.yload)
        ha = np.interp(f, self.f, self.amp)
        # Nodes: input, tank1, tank2, port. Norton source = 1/Rs A.
        y = np.zeros((len(f),4,4), dtype=complex)
        b = np.zeros((len(f),4), dtype=complex)
        y[:,0,0] += 1/p['rs']; b[:,0] = 1/p['rs']
        for a,c,key in [(0,1,'cs'), (1,2,'ck'), (2,3,'co')]:
            v = 1j*w*p[key]*1e-12
            y[:,a,a] += v; y[:,c,c] += v; y[:,a,c] -= v; y[:,c,a] -= v
        for i in [1,2]:
            y[:,i,i] += 1/self.coil_z(f,p,i)+1j*w*(p[f'ct{i}']+p[f'board{i}'])*1e-12
        y[:,3,3] += yl
        v = np.linalg.solve(y,b[...,None])[...,0]
        z = p['rs']*v[:,0]/(1-v[:,0])
        return v[:,3]*ha, z


def metrics(f, h, z):
    g = abs(h); db = 20*np.log10(g); k = int(np.argmax(g))
    threshold = db[k]-3.01029995664
    # Contiguous passband around global maximum; flag split passbands explicitly.
    good = db >= threshold
    a = k
    while a > 0 and good[a-1]: a -= 1
    b = k
    while b+1 < len(f) and good[b+1]: b += 1
    assert a > 0 and b < len(f)-1
    lo = float(np.interp(threshold, db[a-1:a+1], f[a-1:a+1]))
    hi = float(np.interp(threshold, db[b:b+2][::-1], f[b:b+2][::-1]))
    g31 = float(np.interp(31e6,f,g)); z31 = complex(np.interp(31e6,f,z))
    gam = abs((z31-50)/(z31+50))
    return dict(gain31_v_v=g31, gain31_db=float(20*np.log10(g31)),
                fpeak_mhz=float(f[k]/1e6), flo_mhz=lo/1e6, fhi_mhz=hi/1e6,
                center_edges_mhz=(lo+hi)/2e6, bw_mhz=(hi-lo)/1e6,
                disconnected_3db=bool(np.count_nonzero(good)!=b-a+1),
                relative29_db=float(20*np.log10(np.interp(29e6,f,g)/g31)),
                relative33_db=float(20*np.log10(np.interp(33e6,f,g)/g31)),
                zin31_ohm=[z31.real,z31.imag], return_loss50_db=float(-20*np.log10(max(gam,1e-15))),
                vswr50=float((1+gam)/(1-gam)))


def tune(n, p, matching=False):
    """Two CT trimmers fit nominal relative amplitude shape; optional CSEL search.

    Objective fixed before evaluating cases, not an official course pass criterion.
    All search evaluations are analytic, selected solutions get ngspice AC checks.
    """
    f = np.array([29,30,30.5,30.8,31,31.2,31.5,32,33])*1e6
    target = 20*np.log10(abs(np.interp(f,n.f,n.ref))/abs(np.interp(31e6,n.f,n.ref)))
    keys = ['ct1','ct2']+(['cs'] if matching else [])
    x0 = [p[k] for k in keys]
    def fun(x):
        h,z = n.response({**p, **dict(zip(keys,x))}, f)
        err = (20*np.log10(abs(h)/abs(h[4]))-target)
        if matching:
            gam = (z[4]-50)/(z[4]+50)
            err = np.r_[err, 8*gam.real,8*gam.imag]
        return err
    r = least_squares(fun,x0,bounds=([20,25]+([8] if matching else []),
                                    [65,70]+([30] if matching else [])),
                      xtol=1e-11,ftol=1e-11,gtol=1e-11,max_nfev=120)
    out = {**p, **{k:float(v) for k,v in zip(keys,r.x)}}
    return out, dict(success=bool(r.success),nfev=r.nfev,cost=float(r.cost),
                     parameters=keys, objective='relative shape to archived A2; plus 8*complex reflection if matching')


def filter_text(p, frozen_frequency=31e6):
    t = '* S05-07 independent loaded LC fixture; original active stages unchanged\n'
    t += f"CSEL input tank1 {p['cs']:.12g}p\nCK tank1 tank2 {p['ck']:.12g}p\nCOUT tank2 port {p['co']:.12g}p\nRPORT port 0 1Meg\n"
    for i in [1,2]:
        t += f"CTUNE{i} tank{i} 0 {p[f'ct{i}']:.12g}p\n"
        if p[f'board{i}']:
            t += f"CBOARD{i} tank{i} 0 {p[f'board{i}']:.12g}p\n"
        if p['coil']=='coilcraft_1008cs':
            t += f'''* RVAR held at {frozen_frequency:g} Hz; full sweep is an explicit approximation.
RDC{i} tank{i} int{i} 1.2
RSKIN{i} int{i} ln{i} {4.27e-4*np.sqrt(frozen_frequency):.12g}
LSEL{i} ln{i} 0 {p[f'l{i}']:.12g}n
CSELF{i} int{i} cap{i} .156p
RPAR{i} cap{i} 0 31
'''
        else:
            t += f'''RLOSS{i} tank{i} ln{i} {2*np.pi*31e6*p[f'l{i}']*1e-9/p[f'q{i}']:.12g}
LSEL{i} ln{i} 0 {p[f'l{i}']:.12g}n
CSELF{i} tank{i} 0 {p[f'cp{i}']:.12g}p
'''
    return t


def spice(name,p):
    fp = HERE/'filters'/(name+'.cir');fixed(fp,filter_text(p).encode('ascii'))
    raw,r = d.ac(name,front_file=str(fp),rs=p['rs'])
    f=raw['frequency'].real;v=raw['v(input)'];z=p['rs']*v/(1-v)
    m=metrics(f,raw['v(rf)'],z)
    dump(HERE/'results'/(name+'_measured.json'),dict(parameters=p,metrics=m,
         kind='ngspice AC; 1008CS RVAR frozen at 31 MHz when applicable',source_result=name+'.json'))
    return m


def main():
    n=LoadedNetwork()
    h,z=n.response(BASE)
    reuse=dict(max_relative_complex_error=float(np.max(abs(h/n.ref-1))),
               raw_path=str(n.path),raw_sha256=sha(n.path),metrics=metrics(n.f,n.ref,z),
               source='archived C_Q50; no baseline rerun')
    assert reuse['max_relative_complex_error'] < 1e-8
    dump(HERE/'baseline_reuse.json',reuse)
    rows=[]
    def add(name,p,solve=False,matching=False,verify=True):
        opt=None
        if solve:p,opt=tune(n,p,matching)
        h,z=n.response(p)
        row=dict(name=name,parameters=p,optimization=opt,analytic=metrics(n.f,h,z))
        if verify:
            row['spice']=spice(name,p)
            row['gain_spice_minus_analytic_db']=row['spice']['gain31_db']-row['analytic']['gain31_db']
        rows.append(row);return p
    # Independent opposite deviations missing from the previous simple common-mode retune.
    for name,s1,s2 in [('Lminusplus',.95,1.05),('Lplusminus',1.05,.95)]:
        p={**BASE,'l1':470*s1,'l2':470*s2}
        add(name+'_untuned',p)
        add(name+'_CT',p,True)
    # Actual manufacturer's typical frequency loss model: not a worst-case production guarantee.
    p={**BASE,'coil':'coilcraft_1008cs','l1':465.,'l2':465.,'board1':1.,'board2':1.}
    add('CS471_untuned',p)
    add('CS471_CT',p,True)
    # Through-hole 132-17L 460nH: data-sheet informed envelope, NOT a manufacturer model.
    # Q @31 is assumed independently; Cp from SRF340 MHz is only an approximate starting point.
    cp=1/((2*np.pi*340e6)**2*460e-9)*1e12
    part={**BASE,'l1':460.,'l2':460.,'cp1':cp,'cp2':cp,'board1':1.,'board2':1.,
          'cs':14.5,'co':10.8,'ck':2.4}
    tuned=add('P460_Q50_CT',part,True)
    for q in [40.,65.,80.]:
        add(f'P460_Q{int(q)}_CT',{**part,'q1':q,'q2':q},True)
    matched=add('P460_Q50_match',part,True,True)
    # Rounded settings with adjustable total CT, plus finite board/probe perturbations.
    rounded={**matched,'cs':round(matched['cs'],1),'ct1':round(matched['ct1'],1),'ct2':round(matched['ct2'],1)}
    add('P460_match_rounded',rounded)
    add('P460_probe10p',{**tuned,'board2':11.})
    add('P460_RS200',{**tuned,'rs':200.})
    # Four independent L corners; constant branch Q50 with fixed Cp and +1p board per tank.
    for sign1,sign2 in itertools.product([-1,1], repeat=2):
        p={**part,'l1':460*(1+.05*sign1),'l2':460*(1+.05*sign2)}
        add(f'P460_L{sign1:+d}_{sign2:+d}_CT'.replace('+','p').replace('-','m'),p,True)
    # Separate small perturbations, re-tune CT only: unknown stray, CK, input/output coupling.
    for tag,changes in [('stray_high',dict(board1=2.,board2=2.)),
                        ('CK_low',dict(ck=2.2)),('CK_high',dict(ck=2.6)),
                        ('coupling_low',dict(cs=14.5*.98,co=10.8*.98)),
                        ('coupling_high',dict(cs=14.5*1.02,co=10.8*1.02))]:
        add('P460_'+tag+'_CT',{**part,**changes},True)
    dump(HERE/'sweep_results.json',rows)
    f=np.array([25.,29.,31.,33.,100.])*1e6;zz=n.coil_z(f,{**BASE,'coil':'coilcraft_1008cs','l1':465.},1)
    dump(HERE/'manufacturer_model_impedance.json',dict(model='Coilcraft 1008CS-471 Document158-2 2026-04-30 typical',
         points=[dict(f_mhz=float(fi/1e6),r_ohm=float(z.real),x_ohm=float(z.imag),q_terminal=float(z.imag/z.real),
                      apparent_l_nh=float(z.imag/(2*np.pi*fi)*1e9)) for fi,z in zip(f,zz)]))
    print('Completed new AC cases:',len(rows),'baseline numerical relative error',reuse['max_relative_complex_error'])


if __name__=='__main__':main()
