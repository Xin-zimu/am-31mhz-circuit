"""Bounded S05-07 follow-ups: exact-frequency manufacturer check, CK, stray coupling.

Every selected AC run is new. No historical transient is retried.
"""
from run_lc import *


def run_net(name, p, ft, command='ac lin 2401 20meg 44meg'):
    fp=HERE/'filters'/(name+'.cir'); fixed(fp,ft.encode('ascii'))
    c=d.config(front_file=str(fp),rs=p['rs'])
    net=d.circuit(c,'VIN src 0 DC 0 AC 1\n')+'RTEST rf 0 2000\nCTEST rf 0 10p\n'+d.old.old.models()
    net+='\n.options temp=27 tnom=27\n.control\nset filetype=binary\nsave all\n'+command+'\nwrite @RAW@\nquit\n.endc\n.end\n'
    raw,r=d.execute(name,net,{**c,'command':command})
    f=raw['frequency'].real;v=raw['v(input)'];z=p['rs']*v/(1-v)
    if len(f)>1:r['metrics']=metrics(f,raw['v(rf)'],z)
    else:r['metrics']=dict(f_hz=float(f[0]),rf_complex=[float(raw['v(rf)'][0].real),float(raw['v(rf)'][0].imag)])
    d.save(r);return r


def main():
    n=LoadedNetwork(); rows=json.loads((HERE/'sweep_results.json').read_text(encoding='utf-8'))
    byname={r['name']:r for r in rows}; out=[]
    p=byname['CS471_CT']['parameters']
    checks=[]
    for f in [29e6,31e6,33e6]:
        name=f'CS471_exact_{f/1e6:g}'
        r=run_net(name,p,filter_text(p,f),f'ac lin 1 {f:g} {f:g}')
        expected=n.response(p,[f])[0][0]; actual=complex(*r['metrics']['rf_complex'])
        checks.append(dict(name=name,relative_complex_error=float(abs(actual/expected-1)),
                           rf_v_v=float(abs(actual)),f_hz=f))
    assert max(r['relative_complex_error'] for r in checks)<1e-7
    dump(HERE/'manufacturer_exact_check.json',checks)
    # One additional adjustable CK; shape and matching objective fixed, no gain maximization.
    p=byname['P460_Q50_match']['parameters'];keys=['ct1','ct2','cs','ck']
    f=np.array([29,30,30.5,30.8,31,31.2,31.5,32,33])*1e6
    target=20*np.log10(abs(np.interp(f,n.f,n.ref))/abs(np.interp(31e6,n.f,n.ref)))
    def fun(x):
        h,z=n.response({**p,**dict(zip(keys,x))},f)
        gam=(z[4]-50)/(z[4]+50)
        return np.r_[20*np.log10(abs(h)/abs(h[4]))-target,8*gam.real,8*gam.imag]
    opt=least_squares(fun,[p[k] for k in keys],bounds=([20,25,8,1.5],[65,70,30,4]),
                      xtol=1e-11,ftol=1e-11,gtol=1e-11,max_nfev=120)
    p={**p,**{k:float(v) for k,v in zip(keys,opt.x)}}
    out.append(dict(name='P460_match_CK',parameters=p,metrics=spice('P460_match_CK',p),
                    optimizer=dict(nfev=opt.nfev,cost=float(opt.cost),success=bool(opt.success))))
    # Readily made CSEL=20p and CK=2.7p; only tune two CT values again.
    p,opt2=tune(n,{**p,'cs':20.,'ck':2.7})
    out.append(dict(name='P460_Cs20_CK2p7_CT',parameters=p,metrics=spice('P460_Cs20_CK2p7_CT',p),optimization=opt2))
    base=byname['P460_Q50_CT']['parameters']
    for k in [-.03,-.01,.01,.03]:
        name=('P460_mutual_'+str(k)).replace('-','m').replace('.','p')
        # Negative k represented with reversed L2 terminal orientation.
        ft=filter_text(base)
        if k<0:ft=ft.replace(f"LSEL2 ln2 0 {base['l2']:.12g}n",f"LSEL2 0 ln2 {base['l2']:.12g}n")
        ft+=f'KSTRAY LSEL1 LSEL2 {abs(k):.12g}\n'
        r=run_net(name,base,ft)
        out.append(dict(name=name,parameters={'mutual_k':k},metrics=r['metrics']))
    for q in [200,500]:
        name=f'P460_CTlossQ{q}'
        ft=filter_text(base)
        for i in [1,2]:
            ct=base[f'ct{i}'];esr=1/(2*np.pi*31e6*ct*1e-12*q)
            ft=ft.replace(f'CTUNE{i} tank{i} 0 {ct:.12g}p',f'RCT{i} tank{i} ct_loss{i} {esr:.12g}\nCTUNE{i} ct_loss{i} 0 {ct:.12g}p')
        r=run_net(name,base,ft)
        out.append(dict(name=name,parameters={'total_CT_q_at31_assumption':q},metrics=r['metrics']))
    dump(HERE/'extension_results.json',out)
    p,op=tune(n,{**byname['P460_Q50_CT']['parameters'],'cs':15.,'co':11.})
    m=spice('P460_C15_C11_CT',p)
    dump(HERE/'standard_values.json',dict(name='P460_C15_C11_CT',parameters=p,metrics=m,optimization=op))
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
