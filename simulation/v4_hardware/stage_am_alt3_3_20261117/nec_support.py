"""Reproducible NEC2 runs; solver is upstream nec2c, not a local MoM implementation."""
from pathlib import Path
import subprocess, re, math, json, csv
import numpy as np

ROOT=Path(__file__).resolve().parent
EXE=ROOT/'tools/nec2c.exe'
RUN=ROOT/'runs'; RUN.mkdir(exist_ok=True)
NUM=r'[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?'

def solve(name, cards):
    inp=RUN/(name+'.nec'); out=RUN/(name+'.out')
    text='CM AM-ALT.3.3 '+name+'\nCE\n'+'\n'.join(cards)+'\nEN\n'
    if not out.exists() or not inp.exists() or inp.read_text()!=text:
        inp.write_text(text,encoding='ascii')
        p=subprocess.run([str(EXE),'-i',inp.name,'-o',out.name],cwd=RUN,capture_output=True,text=True,timeout=180)
        if p.returncode: raise RuntimeError(name+': '+p.stderr+p.stdout)
    t=out.read_text()
    block=t.split('ANTENNA INPUT PARAMETERS')[1]
    row=block.split('(WATTS)')[1].strip().splitlines()[0]
    v=[float(x) for x in re.findall(NUM,row)]
    r,x=v[6:8]
    loss=float(re.search(r'STRUCTURE LOSS\s*=\s*('+NUM+')',t)[1])
    pin=float(re.search(r'INPUT POWER\s*=\s*('+NUM+')',t)[1])
    pat=[]
    if 'RADIATION PATTERNS' in t:
        for line in t.split('RADIATION PATTERNS')[-1].splitlines():
            vals=re.findall(NUM,line)
            if len(vals)==11 and re.match(r'^\s*\d+\.\d+\s+\d+\.\d+',line):
                z=[float(k) for k in vals]; pat.append(z[:5])
    result=dict(name=name,R=r,X=x,L_uH=-x/(2*math.pi*31),loss_fraction=loss/pin,
                I_peak_1V_A=math.hypot(v[4],v[5]),pattern=pat)
    if pat:
        pp=np.array(pat); th=np.unique(pp[:,0]); ph=np.unique(pp[:,1]); g=10**(pp[:,4].reshape(len(ph),len(th))/10)
        integ=np.trapezoid(np.trapezoid(g*np.sin(np.radians(th)),np.radians(th),axis=1),np.radians(ph))/(4*math.pi)
        result.update(radiated_fraction=float(integ),R_radiated=float(r*integ),R_wire=float(r*loss/pin),
                      R_ground=float(r*(1-integ-loss/pin)),gain_max_dBi=float(pp[:,4].max()),
                      peak_theta_deg=float(pp[np.argmax(pp[:,4]),0]))
    return result

def gw(tag,n,p,q,r=.0005):
    return 'GW %d %d '%(tag,n)+' '.join('%.9g'%x for x in (*p,*q,r))

def model(nrad=4,length=.5,angle=0,h=1,n=40,ground='free',plate=0,mesh=6,pec=False,extra=None):
    # A 1.000 m wire; source is its first segment, at the ground-system junction.
    c=[gw(1,n,(0,0,h),(0,0,h+1))]
    tag=2
    if plate:
        # Thin-wire square grid surrogate, intersections are always endpoints.
        step=plate/mesh
        for i in range(mesh+1):
            for j in range(mesh):
                for swap in [False,True]:
                    a=[-plate/2+i*step,-plate/2+j*step,h]
                    b=[a[0],a[1]+step,h]
                    if swap: a[:2]=a[:2][::-1]; b[:2]=b[:2][::-1]
                    c.append(gw(tag,1,a,b)); tag+=1
    else:
        for k in range(nrad):
            az=2*math.pi*k/nrad; el=math.radians(angle)
            q=(length*math.cos(el)*math.cos(az),length*math.cos(el)*math.sin(az),h-length*math.sin(el))
            c.append(gw(tag,max(4,round(n*length)),(0,0,h),q)); tag+=1
    if extra:
        for p,q in extra:
            c.append(gw(tag,max(4,round(n*math.dist(p,q))),p,q)); tag+=1
    c+=['GE 0']
    if ground!='free':
        er,sig=ground; c+=['GN 2 0 0 0 %g %g'%(er,sig)]
    if not pec: c+=['LD 5 0 0 0 5.8e7']
    c+=['FR 0 1 0 0 31 0','EX 0 1 1 0 1 0','RP 0 %d 73 1000 0 0 5 5'%(37 if ground=='free' else 19)]
    return c

def save(name,data):
    (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')

def benchmarks():
    b=solve('official_ex1',[gw(0,7,(0,0,-.25),(0,0,.25),.001),'GE 0','EX 0 0 4 0 1','XQ'])
    b['reference']=[82.6979,46.3060]; b['pass']=abs(b['R']-82.6979)<.02 and abs(b['X']-46.3060)<.02
    allb=[b]
    for n in [21,41,81]:
        d=solve('dipole_'+str(n),[gw(1,2*n+1,(0,0,-2.417741935),(0,0,2.417741935)),'GE 0','FR 0 1 0 0 31','EX 0 1 %d 0 1'%(n+1),'XQ'])
        m=solve('monopole_'+str(n),[gw(1,n,(0,0,0),(0,0,2.417741935)),'GE 1','GN 1','FR 0 1 0 0 31','EX 0 1 1 0 1','XQ'])
        m['image_relative_error']=abs(complex(d['R'],d['X'])/2-complex(m['R'],m['X']))/abs(complex(m['R'],m['X']))
        allb += [d,m]
    save('benchmarks',allb)
    assert b['pass'] and allb[-1]['image_relative_error']<.03
    print('Benchmarks passed',flush=True)

def scan():
    rows=[]
    for nr in [4,8]:
        for length in [.25,.5,.75,1.0]:
            for a in [0,30,45]:
                name=f'r{nr}_l{length}_a{a}'
                d=solve(name,model(nr,length,a)); d.update(nrad=nr,length=length,angle=a); rows.append(d)
    for side in [.2,.3,.5]:
        d=solve('plate_'+str(side),model(plate=side)); d.update(plate_side=side); rows.append(d)
    save('geometry',rows)
    for d in rows: print(d['name'],round(d['R'],3),round(d['X'],2),round(d['L_uH'],4),flush=True)

def refine():
    rows=[]
    for nr,length in [(4,.5),(4,.75),(8,.5),(8,.75)]:
        for n in [20,40,80]:
            d=solve(f'conv_r{nr}_l{length}_n{n}',model(nr,length,45,n=n)); rows.append(d)
        for h in [.8,1.2,1.6]:
            for label,g in [('dry',(5,.001)),('nom',(13,.005)),('wet',(20,.03))]:
                d=solve(f'env_r{nr}_l{length}_h{h}_{label}',model(nr,length,45,h=h,n=40,ground=g))
                d.update(nrad=nr,length=length,h=h,soil=label); rows.append(d)
    for side in [.2,.3,.5]:
        for mesh in [4,8,12]: rows.append(solve(f'plate{side}_mesh{mesh}',model(plate=side,mesh=mesh)))
    save('refine',rows)
    for d in rows:
        print(d['name'],round(d['R'],3),round(d['X'],2),round(d['L_uH'],4),round(d.get('radiated_fraction',0),3),flush=True)

if __name__=='__main__':
    benchmarks(); scan(); refine()
