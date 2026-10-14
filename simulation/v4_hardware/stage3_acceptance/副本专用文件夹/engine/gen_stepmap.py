"""Determine how TSTEP and TMAX map to the solver's accepted maximum step."""
from pathlib import Path
import json
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
base = (KEEP/'原始只读引用'/'cold_gui_actual.cir').read_bytes().rstrip()
(KEEP/'engine').mkdir(parents=True, exist_ok=True)
CASES = {
 'M_2n_2n':   'tran 2n 2u 0 2n uic',
 'M_1n_1n':   'tran 1n 2u 0 1n uic',
 'M_2n_1n':   'tran 2n 2u 0 1n uic',
 'M_1n_2n':   'tran 1n 2u 0 2n uic',
 'M_1n_1008p':'tran 1n 2u 0 1.008e-9 uic',
 'M_2n_1008p':'tran 2n 2u 0 1.008e-9 uic',
 'M_05n_2n':  'tran 500p 2u 0 2n uic',
 'M_1n_10n':  'tran 1n 2u 0 10n uic',
}
man={'cases':{}}
for name, tran in CASES.items():
    body = base + b'\n.end\n'
    (ENG/f'{name}.cir').write_bytes(body)
    (KEEP/'engine'/f'{name}.cir').write_bytes(body)
    L=[f'source {(ENG/f"{name}.cir").as_posix()}','begin-scope page Transient Analysis',
       'save $v1 $bb_in $bbo $v2','iplot $v1 $bb_in $bbo $v2',
       tran, f'write-and-destroy-iplot "{(ENG/f"{name}.raw").as_posix()}"','end-scope']
    (ENG/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    (KEEP/'engine'/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    man['cases'][name]={'tran':tran}
for d in (KEEP/'engine',ENG): (d/'manifest_stepmap.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
print('cases:',len(CASES))
