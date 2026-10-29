"""One-variable physical sensitivity, not component qualification/Monte Carlo."""
from run_gain import *

def make_filter(name,q=50,cp=1,ck=2.485,l1=470,l2=470,ct1=39.59,ct2=45.83,cs=14.529,co=10.81):
    net=f'''* A2 topology; loss approximation at 31 MHz, Q={q}, Cp={cp}p
CSEL input tank1 {cs}p
RLOSS1 tank1 ln1 {2*np.pi*31e6*l1*1e-9/q:.12g}
LSEL1 ln1 0 {l1}n
CSELF1 tank1 0 {cp}p
CTUNE1 tank1 0 {ct1}p
CK tank1 tank2 {ck}p
RLOSS2 tank2 ln2 {2*np.pi*31e6*l2*1e-9/q:.12g}
LSEL2 ln2 0 {l2}n
CSELF2 tank2 0 {cp}p
CTUNE2 tank2 0 {ct2}p
COUT tank2 port {co}p
RPORT port 0 1Meg
'''
    p=HERE/'filters'/(name+'.cir');fixed(p,net.encode());return p

def ac_case(name,**kw):
    rs=kw.pop('rs',50)
    p=make_filter(name,**kw)
    raw,r=d.ac('C_'+name,front_file=str(p),rs=rs)
    f=raw['frequency'].real;h=raw['v(rf)'];vin=raw['v(input)']
    z=vin/((1-vin)/rs);z31=np.interp(31e6,f,z.real)+1j*np.interp(31e6,f,z.imag)
    gamma=(z31-50)/(z31+50)
    r['physical']=dict(parameters=dict(rs=rs,**kw),zin31=[float(z31.real),float(z31.imag)],return_loss50_db=float(-20*np.log10(abs(gamma))),vswr50=float((1+abs(gamma))/(1-abs(gamma))))
    # Keep extended data outside the immutable solver result.
    fixed(HERE/'results'/('C_'+name+'_physical.json'),json.dumps(r['physical'],indent=2).encode())
    return {**r['metrics'],**r['physical'],'name':name}

def main():
    rows=[]
    for q in [20,30,40,50,80]:rows.append(ac_case('Q'+str(q),q=q))
    for cp in [.5,1.347,2]:rows.append(ac_case('Cp'+str(cp).replace('.','p'),cp=cp))
    for ck in [2.185,2.785]:rows.append(ac_case('CK'+str(ck).replace('.','p'),ck=ck))
    for scale in [.95,1.05,.8,1.2]:rows.append(ac_case('Lboth'+str(scale).replace('.','p'),l1=470*scale,l2=470*scale))
    rows.append(ac_case('L_mismatch',l1=470*.95,l2=470*1.05))
    rows.append(ac_case('CTplus1',ct1=40.59,ct2=46.83))
    for rs in [100,200]:rows.append(ac_case('RS'+str(rs),rs=rs))
    rows.append(ac_case('rounded_C',cs=14.5,co=10.8,ck=2.4,ct1=39.6,ct2=45.8))
    fixed(HERE/'component_sensitivity.json',json.dumps(rows,indent=2).encode())
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
