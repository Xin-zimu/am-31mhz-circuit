from pathlib import Path
import re,json
from design_stage1 import HERE,evaluate,metrics,read_raw
# Recover completed calibrations; do not rerun already completed sweeps.
records=[]
for p in sorted(HERE.glob('LM393_20k_D*_A*.cir')):
    if not p.with_suffix('.raw').exists():continue
    t=p.read_text(); ma=re.search(r'D(\d+)_A(\d+)',p.stem)
    r=float(re.search(r'RVRF FSET RAMP (\S+)',t)[1])+22000
    dp=float(re.search(r'RVDB DUTY DUTY_BOT (\S+)',t)[1])/10000
    ap=float(re.search(r'RVAB V1 0 (\S+)',t)[1])/20000
    records.append(dict(name=p.stem,rfreq=r,dp=dp,ap=ap,target_duty=int(ma[1]),target_amp=int(ma[2]),**metrics(read_raw(p.with_suffix('.raw')))))
a4=next(x for x in records if x['name']=='LM393_20k_D40_A4')
d50=next(x for x in records if x['name']=='LM393_20k_D50_A3')
name='LM393_20k_D50_A4'
m=evaluate(d50['rfreq'],d50['dp'],a4['ap'],name)
records.append(dict(name=name,rfreq=d50['rfreq'],dp=d50['dp'],ap=a4['ap'],target_duty=50,target_amp=4,**m))
(HERE/'calibration.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
t=(HERE/(name+'.cir')).read_text()
# Netlist import loses discrete semiconductor models. Use six-terminal native
# placeholders, then install the intact manufacturer subcircuit in native templates.
t=t[:t.index('*****************************************************************************')]
t=re.sub(r'XU1A.*','ECOMP1 OSC 0 POLY(2) (HYST,RAMP) (V5,0) 0 1 0',t)
t=re.sub(r'XU1B.*','ECOMP2 PWM_RAW 0 POLY(2) (DUTY,RAMP) (V5,0) 0 1 0',t)
t+='\n.tran 50n 1.5m 0 50n\n.end\n'
(HERE/'stage1_layout.cir').write_text(t,encoding='ascii')
print(m)
