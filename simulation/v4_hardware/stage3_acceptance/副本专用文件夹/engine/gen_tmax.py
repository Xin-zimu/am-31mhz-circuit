"""Step 2: TMAX/TSTEP sweep on the engine, plus min-step-floor probes."""
from pathlib import Path
import json, hashlib
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
base = (KEEP/'原始只读引用'/'cold_gui_actual.cir').read_bytes().rstrip()

CASES = {
 'W_tmax2n_20u':   ('tran 2n 20u 0 2n uic',   'reference: request 2ns'),
 'W_tmax1n_20u':   ('tran 1n 20u 0 1n uic',   'step2: TMAX=TSTEP=1ns'),
 'W_tmax500p_20u': ('tran 500p 20u 0 500p uic','TMAX=0.5ns'),
 'W_tmax100p_20u': ('tran 100p 20u 0 100p uic','TMAX=0.1ns'),
 'W_tmax10p_20u':  ('tran 10p 20u 0 10p uic', 'TMAX=0.01ns'),
 'W_tmax1n_1u':    ('tran 1n 1u 0 1n uic',    'shorter window at 1ns'),
 'W_tstep2n_tmax500p': ('tran 2n 20u 0 500p uic','TSTEP=2n but TMAX=0.5ns'),
}
man={'cases':{}}
for name,(tran,note) in CASES.items():
    body = base + b'\n.end\n'
    (ENG/f'{name}.cir').write_bytes(body)
    (KEEP/'engine').mkdir(parents=True, exist_ok=True)
    (KEEP/'engine'/f'{name}.cir').write_bytes(body)
    L=[f'source {(ENG/f"{name}.cir").as_posix()}','begin-scope page Transient Analysis',
       'save $v1 $bb_in $bbo $v2','iplot $v1 $bb_in $bbo $v2',
       'set convlimit','set rshunt = 1e+012','set dynamicdc','set inertialdelay','set suposc',
       'set trtol = 1','set reltol = 0.0001','set itl4 = 500','set method = gear',
       tran, f'write-and-destroy-iplot "{(ENG/f"{name}.raw").as_posix()}"','end-scope']
    (ENG/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    (KEEP/'engine'/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    man['cases'][name]={'tran':tran,'note':note}
for d in (KEEP/'engine',ENG): (d/'manifest_tmax.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(man['cases'],indent=1))
