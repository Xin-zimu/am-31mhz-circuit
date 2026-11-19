"""Frozen driver, new independent NEC-derived single-frequency load fixtures."""
from run_nec import *
import sys, hashlib, concurrent.futures
OLD=ROOT.parent/'stage_am_alt3_20261115'
sys.path.insert(0,str(OLD/'scripts'))
from closure_metrics import analyse
NG=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
BASE=OLD/'round2_20261116/netlists/d05.cir'
OUT=ROOT/'driver_tabletop'; OUT.mkdir(exist_ok=True)

def execute(job):
 q,step=job; name=f'q{q}_s{step}'
 d=next(x for x in json.loads((ROOT/'tabletop.json').read_text()) if x['name']=='desk_r8_l0.5_n120_soil')
 omega=2*math.pi*31e6; c=-1/(omega*d['X']); l=-d['X']/omega; r=d['R']-d['X']/q
 t=BASE.read_text(encoding='utf-8')
 t=re.sub(r'^LTUNE .*$',f'LTUNE sense_out ant_n1 {l:.12g}',t,flags=re.M)
 t=re.sub(r'^RANT .*$',f'RANT ant_n1 ant_n2 {r:.12g}',t,flags=re.M)
 t=re.sub(r'^CANT .*$',f'CANT ant_n2 0 {c:.12g}',t,flags=re.M)
 t=re.sub(r'^tran .*$',f'tran {step}n 0.002 0.00185 {step}n uic',t,flags=re.M)
 t=t.replace('write d05.raw',f'write {name}.raw')
 # Changes are confined to L/R/C load, integration step and output name.
 p=OUT/(name+'.cir'); p.write_text(t,encoding='utf-8')
 if not (OUT/(name+'.raw')).exists():
  with (OUT/(name+'.log')).open('w') as log:
   z=subprocess.run([str(NG),'-b',p.name],cwd=OUT,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
  if z.returncode: raise RuntimeError(name)
 ans=analyse(OUT/(name+'.raw'))
 ans.update(Q=q,step_ns=step,NEC_case=d['name'],load_L_uH=l*1e6,load_C_pF=c*1e12,load_R_ohm=r,
     assumptions='NEC 31MHz equivalent R-C + series L at effective Q; unchanged frozen driver including 10ohm sense. 9V linear-regulator budget with 8mA ground current. Not measured.')
 (OUT/(name+'_metrics.json')).write_text(json.dumps(ans,indent=2))
 print(name,ans['carrier_fundamental_rms_mA'],ans['battery_budget_mW'],flush=True)
 return ans

if __name__=='__main__':
 before=hashlib.sha256(BASE.read_bytes()).hexdigest()
 (ROOT/'frozen_driver_sha256.json').write_text(json.dumps({str(BASE):before},indent=2))
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  rows=list(pool.map(execute,[(30,.25),(60,.25),(100,.25),(60,.125)]))
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==before
 save('driver_tabletop_summary',rows)
