"""Manufacturer-based local RF model; all installation variables are assumptions."""
from pathlib import Path
import json,re,math,subprocess,hashlib,csv,sys
import numpy as np
from scipy.optimize import brentq
import metrics_support as met
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'stage_am_alt3_20261115/round2_20261116/netlists/d05.cir'
NG=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
OUT=ROOT/'joint';OUT.mkdir(exist_ok=True)
W=2*math.pi*31e6
# Coilcraft Document 158, 1812CS-472: R2 + ((RVAR+jwL) || (R1+1/jwCp)).
PART=dict(R1=85.,R2=5.4,Cp=.122e-12,L=4.775e-6,k=.00180)

def coil(f=31e6,scale=1.,loss=1.,extra=0.):
    w=2*math.pi*f;p=PART
    z=p['R2']*loss+1/(1/(p['k']*math.sqrt(f)*loss+1j*w*p['L']*scale)+1/(p['R1']+1/(1j*w*p['Cp'])))
    return 1/(1/z+1j*w*extra)

def ant(d,f=31e6,contact=.2,base=.5e-12,cscale=1):
    w=2*math.pi*f
    z=d['R']+contact+1j*(w*d['Lant_H']-1/(w*d['Cant_F']*cscale))
    return 1/(1/z+1j*w*base)

def design(d):
    x=(coil()+ant(d)).imag+W*2e-9
    c=1/(W*x)
    return c

RSENSE=10.0  # measurement shunt; overridable for the A/B/C sweep

def execute(job):
    h,label,step,ls,loss,extra,contact,base,cs,capscale=job
    rs=RSENSE
    d=next(x for x in json.loads((ROOT/'antenna_nominal.json').read_text()) if x['length_m']==h)
    name=f'h{round(h*100)}_{label}'; c=design(d)*capscale
    p=PART;rvar=p['k']*math.sqrt(31e6)*loss
    capr=.0025/(W*c) # explicit engineering interpolation, not guaranteed Q31
    load=f'''* Independent purchased-network candidate. Frequency-frozen skin resistance at 31 MHz.
RCOILDC sense_out coil_a {p['R2']*loss:.12g}
RCOILSKIN coil_a coil_b {rvar:.12g}
LTUNE coil_b coil_out {p['L']*ls:.12g}
CCOIL coil_a coil_c {p['Cp']:.12g}
RCOILPAR coil_c coil_out {p['R1']:.12g}
CINSTALL sense_out coil_out {max(extra,1e-18):.12g}
CTRIM coil_out trim_a {c:.12g}
RTRIM trim_a trim_b {capr:.12g}
LLEAD trim_b ant_feed 2n
CBASE ant_feed 0 {base:.12g}
VANT ant_feed ant_r 0
RANT ant_r ant_l {d['R']+contact:.12g}
LANT ant_l ant_n2 {d['Lant_H']:.12g}
CANT ant_n2 0 {d['Cant_F']*cs:.12g}
'''
    t=BASE.read_text(encoding='utf-8')
    t=re.sub(r'^LTUNE .*?^CANT .*?$',load.rstrip(),t,flags=re.M|re.S)
    t=t.replace('RSENSE ef_e sense_out 10',f'RSENSE ef_e sense_out {rs:.12g}')
    t=t.replace('i(ltune) i(vsup)','i(ltune) i(vant) v(ant_feed) i(vsup)')
    t=re.sub(r'^tran .*$',f'tran {step}n 0.002 0.00185 {step}n uic',t,flags=re.M)
    t=t.replace('write d05.raw',f'write {name}.raw')
    path=OUT/(name+'.cir')
    if (OUT/(name+'.raw')).exists() and path.exists() and path.read_text(encoding='utf-8')!=t:
        raise RuntimeError('Input changed with cached raw: use a new case name/directory: '+name)
    path.write_text(t,encoding='utf-8')
    if not (OUT/(name+'.raw')).exists():
        with (OUT/(name+'.log')).open('w') as log:
            z=subprocess.run([str(NG),'-b',path.name],cwd=OUT,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        if z.returncode: raise RuntimeError(name)
    # Keep the tested RMS implementation, substituting the actual radiator branch current.
    original=met.read_raw
    def read_actual(path):
        a=original(path);a['i(ltune)']=a['i(vant)'];return a
    met.read_raw=read_actual
    try: ans=met.analyse(OUT/(name+'.raw'))
    finally: met.read_raw=original
    a=original(OUT/(name+'.raw'));t0,t1=ans['window_s'];t=a['time'];keep=(t>=t0)&(t<=t1)
    a={k:v[keep] for k,v in a.items()};t=a['time'];wt=met.weights(t);wt/=wt.sum()
    for q,vc,ve,vb in [('qce','v(drv_c)','v(drv_e)','v(drv_b)'),('qef','v(vcc)','v(ef_e)','v(drv_c)')]:
        ic=a['i(@'+q+'[ic])'];ib=a['i(@'+q+'[ib])']
        power=(a[vc]-a[ve])*ic+(a[vb]-a[ve])*ib
        ans[q+'_peak_ic_mA']=float(max(ic)*1000)
        ans[q+'_average_power_mW']=float(wt@power*1000)
        ans[q+'_peak_power_mW']=float(max(power)*1000)
    cur=a['i(vant)']; cross=np.flatnonzero((cur[:-1]<0)&(cur[1:]>=0))
    pk=np.array([max(abs(cur[l:r+1])) for l,r in zip(cross[:-1],cross[1:])])*1000
    hp=ans['high_plateau_median_peak_mA'];lp=ans['low_plateau_median_peak_mA']
    ans['envelope_overshoot_pct_step']=float((max(pk)-hp)/(hp-lp)*100)
    ans['envelope_undershoot_pct_step']=float((lp-min(pk))/(hp-lp)*100)
    ans['antenna_peak_V']=float(max(abs(a['v(ant_feed)'])))
    ans['sense_current_rms_mA']=float(np.sqrt(wt@(((a['v(ef_e)']-a['v(sense_out)'])/rs)**2))*1000)
    # Source port and radiator current differ because CBASE draws current.
    ans['sense_resistor_power_mW']=ans['sense_current_rms_mA']**2*rs*1e-3  # I^2 R, mA^2*ohm = uW, *1e-3 -> mW
    z=rs+coil(scale=ls,loss=loss,extra=extra)+ant(d,contact=contact,base=base,cscale=cs)+capr+1j*W*2e-9+1/(1j*W*c)
    def react(f):
        w=2*math.pi*f
        return (coil(f,ls,loss,extra)+ant(d,f,contact,base,cs)+1j*w*2e-9+1/(1j*w*c)).imag
    f0=brentq(react,25e6,40e6)
    ans.update(name=name,length_m=h,step_ns=step,Ctrim_total_pF=c*1e12,part_model_parameters=PART,rsense_ohm=rs,
       coil_Z31_ohm=[coil(scale=ls,loss=loss,extra=extra).real,coil(scale=ls,loss=loss,extra=extra).imag],
       port_Z31_with_shunt=[z.real,z.imag],port_Z31_with_10ohm=[z.real,z.imag],resonance_Hz=f0,
       assumptions=dict(L_scale=ls,coil_loss_scale=loss,coil_extra_C_pF=extra*1e12,contact_ohm=contact,base_C_pF=base*1e12,antenna_C_scale=cs,trim_C_scale=capscale),
       metric_notes='Radiator current is I(VANT); RMS trapezoidal, complete baseband periods. Manufacturer typical L model, Rskin frozen at31MHz in transient; not a broadband harmonic certification.')
    # Conditional far-field screening with new NEC gain. RX h_eff=1m is retained as a hypothesis, never measured.
    for theta in [65,85]:
        gains=[p[4] for p in d['pattern'] if p[0]==theta]
        g=10**(float(np.mean(gains))/10)
        field_per_A=math.sqrt(376.730313668*d['R']*g/(2*math.pi*6**2))
        voc_need=4/(.4777*(ans['modulation_index']/.5))*1e-3
        required=voc_need/field_per_A
        ans[f'link_theta{theta}']=dict(Epeak_per_Irms=field_per_A,required_carrier_mA_RXheff1m=required*1000,
           V2pp_estimate_RXheff1m=ans['carrier_fundamental_rms_mA']/1000*field_per_A*1000*.4777*(ans['modulation_index']/.5))
    (OUT/(name+'_metrics.json')).write_text(json.dumps(ans,indent=2))
    print(name,round(ans['carrier_fundamental_rms_mA'],4),round(ans['battery_budget_mW'],2),flush=True)
    return ans

def main():
    before=hashlib.sha256(BASE.read_bytes()).hexdigest()
    jobs=[(h,'nom',.25,1,1,0,.2,.5e-12,1,1) for h in [.7,.8,.9,1.]]
    jobs += [(.9,'fine',.125,1,1,0,.2,.5e-12,1,1),(.9,'finer',.0625,1,1,0,.2,.5e-12,1,1),
       (.9,'Lplus5',.25,1.05,1,0,.2,.5e-12,1,1),(.9,'Lminus5',.25,.95,1,0,.2,.5e-12,1,1),
       (.9,'loss2',.25,1,2,0,2,.5e-12,1,1),(.9,'Cp05',.25,1,1,.5e-12,.2,.5e-12,1,1),
       (.9,'base2',.25,1,1,0,.2,2e-12,1,1),(.9,'Cantplus10',.25,1,1,0,.2,.5e-12,1.1,1),
       (.9,'trimplus1',.25,1,1,0,.2,.5e-12,1,1.01)]
    if len(sys.argv)>1:jobs=[j for j in jobs if j[1] in sys.argv[1:]]
    rows=[execute(j) for j in jobs]
    assert before==hashlib.sha256(BASE.read_bytes()).hexdigest()
    (ROOT/'frozen_driver_hash.json').write_text(json.dumps({'path':str(BASE),'sha256_before_after':before},indent=2))
    allrows=[json.loads(p.read_text()) for p in sorted(OUT.glob('*_metrics.json'))]
    (ROOT/'joint_summary.json').write_text(json.dumps(allrows,indent=2))

if __name__=='__main__':main()
