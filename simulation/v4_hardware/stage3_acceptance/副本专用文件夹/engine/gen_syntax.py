"""Decisive syntax test: Multisim help shows 'set retol=0.01' (no spaces).

Using the real circuit at TMAX=2ns, LTE demonstrably binds (engine steps reach
8e-14, far below TMAX). If any syntax makes the step profile change, the channel works.
"""
from pathlib import Path
import json
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
base = (KEEP/'原始只读引用'/'cold_gui_actual.cir').read_bytes().rstrip()
body = base + b'\n.end\n'
(KEEP/'engine').mkdir(parents=True, exist_ok=True)

CASES = {
 'X0_none':        [],
 'X1_sp_reltol':   ['set reltol = 0.01'],
 'X2_nosp_reltol': ['set reltol=0.01'],
 'X3_nosp_tight':  ['set reltol=1e-09'],
 'X4_nosp_trtol':  ['set trtol=0.01'],
 'X5_nosp_itl4':   ['set itl4=1000'],
 'X6_nosp_method': ['set method=gear'],
 'X7_all_nosp':    ['set reltol=0.01','set trtol=0.01','set itl4=1000','set method=gear'],
 'X8_before_src':  ['set reltol=0.01','set trtol=0.01'],
}
man={'tran':'tran 2n 2u 0 2n uic','cases':{}}
for name, sets in CASES.items():
    (ENG/f'{name}.cir').write_bytes(body)
    (KEEP/'engine'/f'{name}.cir').write_bytes(body)
    pre = sets if name=='X8_before_src' else []
    post = [] if name=='X8_before_src' else sets
    L = pre + [f'source {(ENG/f"{name}.cir").as_posix()}','begin-scope page Transient Analysis',
       'save $v1 $bb_in $bbo $v2','iplot $v1 $bb_in $bbo $v2'] + post + [
       'tran 2n 2u 0 2n uic', f'write-and-destroy-iplot "{(ENG/f"{name}.raw").as_posix()}"','end-scope']
    (ENG/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    (KEEP/'engine'/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    man['cases'][name]={'set':sets,'position':'before' if name=='X8_before_src' else 'after'}
for d in (KEEP/'engine',ENG): (d/'manifest_syntax.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
print('cases:',len(CASES))
