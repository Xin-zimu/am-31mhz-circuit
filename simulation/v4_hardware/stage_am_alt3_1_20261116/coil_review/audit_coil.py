"""Coupled manufacturability screen, not a full-wave coil simulation or bench result."""
from pathlib import Path
import math,json,itertools,hashlib
import numpy as np
from scipy.optimize import brentq
P=Path(__file__).resolve().parent
F=31e6;W=2*math.pi*F;TARGET=3.4899598601799258e-6
MU=4*math.pi*1e-7;RHO=1/5.8e7
# Medhurst, Wireless Engineer March 1947, p84 Table VI; restrict to this interval.
ASPECT=np.array([.8,.9,1.,1.5,2.,2.5,3.])
H=np.array([.46,.46,.46,.47,.50,.56,.61])

def geometry(n,length,D=25.,wire=1.):
 r=D/2/25.4;b=length/25.4
 L=r*r*n*n/(9*r+10*b)*1e-6
 C=float(np.interp(length/D,ASPECT,H))*D/10*1e-12
 wire_len=math.hypot(math.pi*D/1000*n,length/1000)+.02
 # conservative surface-length convention: overall occupied winding length.
 pitch=(length-wire)/(n-1)
 return L,C,wire_len,pitch

def impedance(f,n,length,extra_pf=0.,cscale=1.,kprox=2.,rcontact=.2,tand=.005):
 L,C,wire_len,pitch=geometry(n,length);C=C*cscale+extra_pf*1e-12
 delta=math.sqrt(2*RHO/(2*math.pi*f*MU))
 rskin=RHO*wire_len/(math.pi*.001*delta)
 R=kprox*rskin+rcontact
 y=1/complex(R,2*math.pi*f*L)+complex(2*math.pi*f*C*tand,2*math.pi*f*C)
 return 1/y,L,C,R,rskin,pitch

def evaluate(n,length,**kwargs):
 z,L,C,R,rskin,pitch=impedance(F,n,length,**kwargs)
 fs=brentq(lambda f:impedance(f,n,length,**kwargs)[0].imag,40e6,200e6)
 return dict(turns=n,diameter_mm=25,wire_mm=1,length_mm=length,pitch_mm=pitch,
  L0_uH=L*1e6,Ctotal_pF=C*1e12,L_eff31_uH=z.imag/W*1e6,
  X31_ohm=z.imag,ESR31_ohm=z.real,Q31=z.imag/z.real,SRF_MHz=fs/1e6,
  R_branch31_ohm=R,R_skin31_ohm=rskin,**kwargs)

bound=dict(target_Leff_uH=TARGET*1e6,target_X_ohm=W*TARGET,
  maximum_terminal_ESR_Q60=W*TARGET/60,maximum_terminal_ESR_Q100=W*TARGET/100,
  L0_min_SRF62_uH=.75*TARGET*1e6,L0_max_uH=TARGET*1e6,
  Ctotal_max_pF=1/(3*W*W*TARGET)*1e12,
  Rbranch_max_at_SRF62_Q60=W*TARGET/60*.75**2,
  skin_depth_um=math.sqrt(2*RHO/(W*MU))*1e6)
original=evaluate(16,35)
tuned=[]
for n in [14,16,18]:
 for cp in [0,.5,1,1.5]:
  l=brentq(lambda l:impedance(F,n,l,extra_pf=cp)[0].imag/W-TARGET,25,75)
  d=evaluate(n,l,extra_pf=cp);d['passes_Q60_SRF62_model']=d['Q31']>=60 and d['SRF_MHz']>=62;tuned.append(d)
stress=[]
for scale,cp,k,rc,td in itertools.product([.8,1,1.2],[0,.5,1,1.5],[1,3,5],[.1,1],[.001,.02]):
 l=brentq(lambda l:impedance(F,16,l,extra_pf=cp,cscale=scale,kprox=k,rcontact=rc,tand=td)[0].imag/W-TARGET,25,75)
 d=evaluate(16,l,extra_pf=cp,cscale=scale,kprox=k,rcontact=rc,tand=td)
 d['passes']=d['Q31']>=60 and d['SRF_MHz']>=62;stress.append(d)

# Exact two-capacitor fit under ideal frequency reading, showing cap tolerance alone.
fits=[];trueL=3e-6;trueC=1.5e-12
for e1,e2 in itertools.product([-0.01,.01],repeat=2):
 c1=100e-12;c2=220e-12
 y1=trueL*(c1*(1+e1)+trueC);y2=trueL*(c2*(1+e2)+trueC)
 l=(y2-y1)/(c2-c1);cp=y1/l-c1
 fits.append(dict(error_C100=e1,error_C220=e2,Lfit_uH=l*1e6,Cfit_pF=cp*1e12))
result=dict(model='(Rac+jwL0) in parallel with Ctotal and G=w*Ctotal*tan_delta. Empirical C estimate and assumed loss scenarios; not measured.',
 bounds=bound,original=original,tuned=tuned,stress=stress,cap_tolerance_fits=fits)
(P/'coupled_coil_results.json').write_text(json.dumps(result,indent=2))
assert abs(1/(2*math.pi*math.sqrt(bound['L0_min_SRF62_uH']*1e-6*bound['Ctotal_max_pF']*1e-12))-62e6)<1
assert all(abs(d['L_eff31_uH']-TARGET*1e6)<1e-8 for d in tuned+stress)
assert min(d['Cfit_pF'] for d in fits)<0
print(json.dumps(dict(bounds=bound,original=original,tuned=tuned,stress_summary=dict(count=len(stress),pass_count=sum(d['passes'] for d in stress),minQ=min(d['Q31'] for d in stress)),cap_tolerance_fits=fits),indent=2))
