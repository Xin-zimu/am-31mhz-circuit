"""Numerical passive LC design using R2's extracted small-signal input load.
Theory/linear network calculation only; downstream SPICE is separate evidence.
Two lossy 470nH parallel tanks with capacitive input, intertank and output coupling.
"""
import json
import numpy as np
from scipy.optimize import least_squares
from run_diagnosis import HERE,WORK,readraw,fixed

d=readraw(WORK/'R2_ac.raw');freq=d['frequency'].real
yin=2j*np.pi*freq*1e-9*(d['v(port)']-d['v(b1)'])/d['v(port)']
gain=d['v(rf)']/d['v(port)']

def response(f,p,q=50):
    ca,cb,ck,ct1,ct2=np.array(p)*1e-12
    w=2*np.pi*np.array(f);jw=1j*w;n=len(w)
    yload=np.interp(f,freq,yin);g=np.interp(f,freq,gain)
    mat=np.zeros((n,4,4),dtype=complex)
    mat[:,0,0]=1/50
    mat[:,3,3]=yload
    for a,b,c in [(0,1,ca),(1,2,ck),(2,3,cb)]:
        y=jw*c;mat[:,a,a]+=y;mat[:,b,b]+=y;mat[:,a,b]-=y;mat[:,b,a]-=y
    loss=2*np.pi*31e6*470e-9/q
    mat[:,1,1]+=1/(loss+jw*470e-9)+jw*(ct1+1e-12)
    mat[:,2,2]+=1/(loss+jw*470e-9)+jw*(ct2+1e-12)
    b=np.zeros((n,4),dtype=complex);b[:,0]=1/50
    v=np.linalg.solve(mat,b[...,None])[...,0]
    return v[:,3]*g,v

def design(bw):
    # Fit realizable Butterworth-like relative passband; center gain has a soft
    # objective, never silently normalize insertion loss out of SPICE results.
    f=31e6+np.array([-2,-1,-.75,-.5,-.25,0,.25,.5,.75,1,2])*bw
    target=-10*np.log10(1+(2*(f-31e6)/bw)**4)
    def residual(p):
        h,_=response(f,p);a=20*np.log10(abs(h));rel=a-a[5]
        return np.r_[((rel-target)*np.array([.3,.6,1,2,1,0,1,2,1,.6,.3])),
            max(0,20*np.log10(68.449)-a[5])*.12]
    results=[]
    for scale in [.7,1,1.4]:
        r=least_squares(residual,[12*scale,6*scale,bw/31e6*55/1.4,39,47],
            bounds=([1,1,.1,5,5],[60,60,15,70,70]),max_nfev=600,
            xtol=1e-10,ftol=1e-10,gtol=1e-10)
        results.append(r)
    r=min(results,key=lambda x:np.linalg.norm(x.fun));p=np.round(r.x,3)
    ff=np.linspace(24e6,38e6,14001);h,_=response(ff,p);a=abs(h);good=ff[a>=max(a)/np.sqrt(2)]
    h0=response(np.array([29e6,31e6,33e6]),p)[0]
    m=dict(target_bw=bw,values_pf=p.tolist(),actual_bw=float(np.ptp(good)),peak_f=float(ff[a.argmax()]),
        g31=float(abs(h0[1])),relative29_db=float(20*np.log10(abs(h0[0]/h0[1]))),
        relative33_db=float(20*np.log10(abs(h0[2]/h0[1]))),
        gain_change_db=float(20*np.log10(abs(h0[1])/68.449)),optimizer_cost=float(np.linalg.norm(r.fun)),
        evidence_type='linear network calculation; not transistor transient or actual hardware')
    tag=f'A{bw/1e6:g}M';ca,cb,ck,ct1,ct2=p
    net=f'''* {tag}: two capacitively coupled lossy parallel LC tanks.
* Q=50 at 31MHz, Cp=1p per tank; assumptions, not vendor qualification.
CSEL input tank1 {ca}p
RLOSS1 tank1 ln1 1.83092019851
LSEL1 ln1 0 470n
CSELF1 tank1 0 1p
CTUNE1 tank1 0 {ct1}p
CK tank1 tank2 {ck}p
RLOSS2 tank2 ln2 1.83092019851
LSEL2 ln2 0 470n
CSELF2 tank2 0 1p
CTUNE2 tank2 0 {ct2}p
COUT tank2 port {cb}p
'''
    fixed(HERE/'filters'/(tag+'.cir'),net.encode())
    fixed(HERE/'filters'/(tag+'_design.json'),json.dumps(m,indent=2).encode())
    print(json.dumps(m),flush=True)

if __name__=='__main__':
    design(2e6);design(1e6)
