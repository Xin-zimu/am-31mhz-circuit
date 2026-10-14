"""7 ms cold start (10 ms hit an internal simulation error)."""
from pathlib import Path
import json
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
base = (KEEP/'原始只读引用'/'cold_gui_actual.cir').read_bytes().rstrip()
(KEEP/'engine').mkdir(parents=True, exist_ok=True)
name, tran = 'L_7ms_1ns', 'tran 1n 7m 0 1n uic'
body = base + b'\n.end\n'
(ENG/f'{name}.cir').write_bytes(body); (KEEP/'engine'/f'{name}.cir').write_bytes(body)
L=[f'source {(ENG/f"{name}.cir").as_posix()}','begin-scope page Transient Analysis',
   'save $v1 $bb_in $bbo $v2','iplot $v1 $bb_in $bbo $v2',
   tran, f'write-and-destroy-iplot "{(ENG/f"{name}.raw").as_posix()}"','end-scope']
(ENG/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
(KEEP/'engine'/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
man={'cases':{name:{'tran':tran,'purpose':'cold start settling; 10 ms exceeded solver limit'}}}
for d in (KEEP/'engine',ENG): (d/'manifest_7ms.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
print('ok')
