"""Frozen-driver A-E simulation batch. Every new run has its own files."""
import concurrent.futures
import hashlib
import json
import math
import re
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'round2_20261116'
NG=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
BASE=ROOT/'netlists/closure_sense10_fine.cir'
CASES={
 'd125':dict(step=.125), 'd0625':dict(step=.0625),
 'c_lowC_loss':dict(c=6,q=30,retune=True),
 'c_highC_lowLoss':dict(c=12,q=100,retune=True),
 'c_det_minus3':dict(c=8.913*.97),
 'c_det_plus3':dict(c=8.913*1.03),
 'c_device_slow':dict(bf=100,tf=1.3,cj=1.2),
 'c_device_fast':dict(bf=600,tf=.8,cj=.8),
 'c_supply_low':dict(vcc=4.75), 'c_supply_high':dict(vcc=5.25),
 'e_adverse':dict(c=6,q=30,retune=True,bf=100,tf=1.3,cj=1.2,vcc=4.75),
 'd05':dict(step=.05),
}

def prepare():
    for folder in ['netlists','results']:
        (OUT/folder).mkdir(parents=True,exist_ok=True)
    # Freeze exact prior artifacts before generating separate simulation fixtures.
    frozen=[BASE, ROOT/'scripts/closure_metrics.py',ROOT/'results/closure_sense10_fine_metrics.json',ROOT/'results/closure_review.json']
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen}
    p=OUT/'frozen_sha256.json'
    if p.exists():
        assert json.loads(p.read_text())==manifest, 'Frozen files changed'
    else:
        p.write_text(json.dumps(manifest,indent=2)+'\n')
    text=BASE.read_text(encoding='utf-8')
    model=re.search(r'(?ims)^\.model 2N3904\s+NPN\(.*?\)',text)[0]
    defs={}
    for name,cfg in CASES.items():
        step=cfg.get('step',.25); c=cfg.get('c',8.913)
        l=1/(2*math.pi*31e6)**2/(c*1e-12)*1e6 if cfg.get('retune') else 2.9572
        r=4.224+1+2*math.pi*31e6*l*1e-6/cfg.get('q',60)
        # Preserve exact nominal R used by the previous result for D convergence.
        if 'q' not in cfg and not cfg.get('retune'): r=14.824
        s=text.replace(text.splitlines()[0],f'* AM-ALT.3 frozen-driver round2: {name}')
        s=re.sub(r'^LTUNE .*$',f'LTUNE sense_out ant_n1 {l:.12g}u',s,flags=re.M)
        s=re.sub(r'^RANT .*$',f'RANT ant_n1 ant_n2 {r:.12g}',s,flags=re.M)
        s=re.sub(r'^CANT .*$',f'CANT ant_n2 0 {c:.12g}p',s,flags=re.M)
        if 'vcc' in cfg:
            s=s.replace('VSUP vcc 0 PWL(0 0 1u 5)',f"VSUP vcc 0 PWL(0 0 1u {cfg['vcc']})")
            s=s.replace('V5 V5 0 5',f"V5 V5 0 {cfg['vcc']}")
        if 'bf' in cfg:
            m=model.replace('2N3904','DRIVER_VAR',1)
            m=re.sub(r'Bf=\S+',f"Bf={cfg['bf']}",m)
            m=re.sub(r'Tf=\S+',f"Tf={301.2*cfg['tf']}p",m)
            m=re.sub(r'Cjc=\S+',f"Cjc={3.638*cfg['cj']}p",m)
            m=re.sub(r'Cje=\S+',f"Cje={4.493*cfg['cj']}p",m)
            s=s.replace('QCE drv_c drv_b drv_e 2N3904','QCE drv_c drv_b drv_e DRIVER_VAR').replace('QEF vcc drv_c ef_e 2N3904','QEF vcc drv_c ef_e DRIVER_VAR')
            s=s.replace('.control',m+'\n.control')
        s=re.sub(r'^save .*$', 'save v(v1) v(vcc) v(v5) v(tp3) v(drv_b) v(drv_c) v(drv_e) v(ef_e) v(sense_out) i(ltune) i(vsup) i(v5) @qce[ic] @qce[ib] @qef[ic] @qef[ib]',s,flags=re.M)
        s=re.sub(r'^tran .*$',f'tran {step}n 0.002 0.00185 {step}n uic',s,flags=re.M)
        s=re.sub(r'^write .*$',f'write {name}.raw',s,flags=re.M)
        # Fixed two-transistor driver, same bias and emitter resistors in EVERY case.
        for line in ['RDB1 vcc drv_b 40000','RDB2 drv_b 0 10000','RDC vcc drv_c 1250','RDE drv_e 0 150','REF ef_e 0 200','RSENSE ef_e sense_out 10']:
            assert line in s
        (OUT/'netlists'/f'{name}.cir').write_text(s,encoding='utf-8')
        defs[name]={**cfg,'step_ns':step,'C_pF':c,'L_uH':l,'RANT_ohm':r,'fixture_only':True}
    (OUT/'cases.json').write_text(json.dumps(defs,indent=2)+'\n')

def run(name):
    start=time.time(); dest=OUT/'results'; log=dest/f'{name}.log'
    if (dest/f'{name}.raw').exists() and log.exists() and 'ngspice-47 done' in log.read_text(errors='replace'):
        return dict(name=name,status='existing_complete')
    p=subprocess.run([str(NG),'-b','-o',str(log),str(OUT/'netlists'/f'{name}.cir')],cwd=dest,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,timeout=3600)
    ok=p.returncode==0 and 'ngspice-47 done' in log.read_text(errors='replace')
    return dict(name=name,status='complete' if ok else 'failed',returncode=p.returncode,seconds=time.time()-start)

if __name__=='__main__':
    prepare()
    # Independent ngspice processes; unique file names and logs, no shared writes.
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for future in concurrent.futures.as_completed([pool.submit(run,k) for k in CASES]):
            row=future.result(); results.append(row)
            (OUT/'run_status.json').write_text(json.dumps(results,indent=2)+'\n')
            print(json.dumps(row),flush=True)
