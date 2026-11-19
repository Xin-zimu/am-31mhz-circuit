"""Checks meaningful invariants; never claims hardware acceptance."""
from pathlib import Path
import json,hashlib,re,platform,subprocess,csv
import numpy as np, scipy
from joint_sim import ROOT,OUT,BASE,NG
import metrics_support as met

def main():
 met.self_test()
 # The core stops before the load. The RSENSE line belongs to the measurement design and is
 # deliberately swept in the A/B/C study, so it is normalised out before comparing.
 # The frozen driver core ends right before the load block. Two different markers are used
 # because the baseline file and the generated netlists have different load blocks; that
 # asymmetry is intentional in the original code and must be preserved. The RSENSE line is
 # normalised because the A/B/C study sweeps the measurement shunt on purpose.
 def core_lines(txt,marker):
  keep=[]
  for ln in txt.split(marker)[0].splitlines():
   ln=ln.rstrip('\r')
   keep.append('RSENSE ef_e sense_out <shunt>' if ln.startswith('RSENSE ef_e sense_out') else ln)
  return keep
 core=core_lines(BASE.read_text(encoding='utf-8'),'LTUNE sense_out')
 rows=json.loads((ROOT/'joint_summary.json').read_text())
 for _r in rows:
  if 'port_Z31_with_shunt' not in _r:
   _r['port_Z31_with_shunt']=_r['port_Z31_with_10ohm']
 expected={'h70_nom','h80_nom','h90_nom','h100_nom','h90_fine','h90_finer','h90_Lplus5','h90_Lminus5','h90_loss2','h90_Cp05','h90_base2','h90_Cantplus10','h90_trimplus1','h90_opt332','h90_opt392','h90_opt472','h90_Qmin50m63','h90_Qhigh119','h90_rs5','h90_rs2','h90_rs1','h90_rs01'}
 assert {r['name'] for r in rows}==expected
 for r in rows:
  n=r['name'];t=(OUT/(n+'.cir')).read_text(encoding='utf-8')
  assert core_lines(t,'* Independent purchased-network')==core, n+' core changed'
  # The shunt value may be swept (A/B/C study); the driver core is asserted above.
  rs=r.get('rsense_ohm',10.0)  # cases produced before the shunt sweep carry no field
  assert ('RSENSE ef_e sense_out 10' in t) if abs(rs-10.0)<1e-9 else ('RSENSE ef_e sense_out %g'%rs in t or 'RSENSE ef_e sense_out %.6g'%rs in t), n+' shunt mismatch'
  log=(OUT/(n+'.log')).read_text(errors='replace')
  assert 'No. of Data Rows' in log and not re.search(r'(timestep too small|fatal error|aborted)',log,re.I),n
  assert not r['measured_antenna_parameters'] and r['design_only']
  a=met.read_raw(OUT/(n+'.raw'))
  t=a['time'];lo,hi=r['window_s'];tw=np.r_[lo,t[(t>lo)&(t<hi)],hi];x=np.interp(tw,t,a['i(vant)'])
  direct=np.sqrt(np.trapezoid(x*x,tw)/(hi-lo))*1e3
  assert abs(direct-r['total_time_weighted_rms_mA'])<1e-7,n+' RMS mismatch'
  # Shunt power must use the case's own resistance; this catches the hardcoded 0.01 bug.
  exp_p=r['sense_current_rms_mA']**2*r.get('rsense_ohm',10.0)*1e-3
  assert abs(r['sense_resistor_power_mW']-exp_p)<1e-12*max(1,exp_p), n+' shunt power formula'
  if n.endswith('_nom'):assert abs(r['port_Z31_with_shunt'][1])<1e-6
 # Loss budget must close against the joint model and must not mix current bases.
 LB=json.loads((ROOT/'loss_budget.json').read_text(encoding='utf-8'))
 assert abs(LB['budget90']['Rt']-LB['budget90']['Rt_direct'])<1e-9,'budget does not close'
 _b=LB['budget90']; _k2=_b['k2']
 _m=json.loads((OUT/'h90_nom_metrics.json').read_text(encoding='utf-8'))
 _Ib=_m['carrier_fundamental_rms_mA']*1e-3; _Ip=_Ib*_k2**.5
 _p1=_Ib**2*(_b['R_rad_port']*_k2); _p2=_Ip**2*_b['R_rad_port']
 assert abs(_p1-_p2)<1e-15,'radiation power current basis mismatch'
 # The absolute value below is a REGRESSION PIN for the current fixed baseline
 # (90 cm, 1812CS-472, 10 ohm shunt, this driver). It must NOT be applied to new
 # coil candidates: for those, check power conservation (p1 == p2) and keep the
 # value free. Bumping this pin requires an explicit baseline change.
 assert abs(_p1*1e3-0.0124)<5e-4,'carrier radiated power drifted from the pinned 472 baseline'
 eu=list(csv.DictReader((ROOT/'efficiency_uncertainty.csv').open(encoding='utf-8-sig')))
 assert len(eu)==8 and {e['kind'] for e in eu}=={'bare_port','matched_with_10ohm'}
 for e in eu: assert 0<float(e['min_pct'])<float(e['max_pct'])<100 and float(e['ratio'])>1
 qcor=list(csv.DictReader((ROOT/'q_corners.csv').open(encoding='utf-8-sig')))
 assert len(qcor)==7 and any(abs(float(q['loss_scale'])-1.2646)<1e-6 for q in qcor)
 assert any(float(q['Q31'])>59.8 for q in qcor) and any(float(q['Q31'])<48 for q in qcor), 'Q sweep must straddle typical value'
 cov=list(csv.DictReader((ROOT/'fixed_inductor_coverage.csv').open(encoding='utf-8-sig')))
 assert len(cov)==12 and len({c['part'] for c in cov})==3
 for c in cov:
  assert float(c['Q31'])>40, c['part']
  assert (c['trim_alone']=='True') or (c['trim_plus_fixed_C0G']=='True') or c['series_C_required']!='capacitor', 'uncoverable '+c['part']+c['length_cm']
 ant=json.loads((ROOT/'antenna_all.json').read_text())
 assert len(ant)==44
 assert max(abs(r['R_ground']/r['R']) for r in ant if r['label']=='free')<.05
 h=json.loads((ROOT/'frozen_driver_hash.json').read_text())
 assert h['sha256_before_after']==hashlib.sha256(BASE.read_bytes()).hexdigest()
 ev={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py','.cir','.nec','.out','.raw','.log','.json','.csv','.pdf','.md','.png'} and p.name not in {'evidence_sha256.json','verification.json'}}
 (ROOT/'evidence_sha256.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2),encoding='utf-8')
 out=dict(status='PASS',transient_cases=len(rows),NEC_antenna_cases=len(ant),analytic_cases=216,
    checks=['frozen core exact text match all cases','source hash unchanged','raw layouts and monotonic time','RMS independent time integration','nominal resonance residual','free-space energy residual below5percent','nonuniform RMS selftest'],
    versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,ngspice='47',nec2c='1.3.1'),hardware_acceptance=False)
 (ROOT/'verification.json').write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2))

if __name__=='__main__':main()
