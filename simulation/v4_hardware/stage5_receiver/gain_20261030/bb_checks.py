"""Local OPA197 small-signal stability and gain checks, same 9 V circuit."""
from run_gain import *

def ac(name,loop=False,**kw):
    c=cfg(**kw)
    net='* Local baseband frequency/return-ratio check\nVSUP vcc 0 9\nVIN out 0 DC .2 AC '+('0' if loop else '1')+'\n'+bb(c)
    if loop:
        net=net.replace('XOPA bbin neg','VTEST inv neg DC 0 AC 1\nXOPA bbin inv')
    raw,r=wrapper(name,net,'ac dec 150 1 100meg',c,'all')
    f=raw['frequency'].real
    if loop:
        h=-raw['v(neg)']/raw['v(inv)']
        g=20*np.log10(abs(h));phase=np.unwrap(np.angle(h))*180/np.pi
        cross=np.where((g[:-1]>0)&(g[1:]<=0))[0]
        i=int(cross[0]);alpha=-g[i]/(g[i+1]-g[i])
        fc=np.exp(np.log(f[i])+alpha*np.log(f[i+1]/f[i]));ph=phase[i]+alpha*(phase[i+1]-phase[i])
        r['metrics']=dict(unity_loop_hz=float(fc),phase_at_unity_deg=float(ph),phase_margin_deg=float(180+ph),method='series injection at inverting input; DC loop closed')
    else:
        h=raw['v(final)'];g20=np.interp(2e4,f,abs(h));high=f[(f>2e4)&(abs(h)<g20/np.sqrt(2))][0]
        r['metrics']=dict(gain20=float(g20),upper_3db_hz=float(high),gain2MHz=float(np.interp(2e6,f,abs(h))))
    d.save(r);print(json.dumps(dict(name=name,**r['metrics'])),flush=True)

def step(name,**kw):
    c=cfg(step=10,start=100,stop=400,**kw)
    net='* Local small-signal square response; 100mV output target\nVSUP vcc 0 9\nVIN out 0 PULSE(.2 .20454545 50u 10n 10n 24.99u 50u)\n'+bb(c)
    raw,r=wrapper(name,net,'tran 10n 400u 100u 10n',c,'v(out) v(bbin) v(ref) v(bbo) v(final) i(vsup)')
    r['metrics']=metrics(raw,c);d.save(r)
    print(json.dumps(dict(name=name,final=r['metrics']['final'])),flush=True)

if __name__=='__main__':
    ac('BB22_ac')
    ac('BB22_loop',loop=True)
    ac('BB22_loop_C1000',loop=True,bb_cap=1000)
    step('BB22_smallstep')
    step('BB22_smallstep_C1000',bb_cap=1000)
