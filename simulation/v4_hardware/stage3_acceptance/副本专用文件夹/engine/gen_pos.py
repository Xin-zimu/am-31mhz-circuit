"""Where must .options live? Test card position and form."""
from pathlib import Path
import json
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
raw = (KEEP/'原始只读引用'/'cold_gui_actual.cir').read_bytes().rstrip().decode('ascii')
lines = raw.split('\n')
HEAD = lines[0]
BODY = '\n'.join(lines[1:])
(KEEP/'engine').mkdir(parents=True, exist_ok=True)

CASES = {
 # name: netlist text
 'Y0_plain':      BODY + '\n.end\n',
 'Y1_opt_top':    HEAD + '\n.options reltol=1e-09 trtol=0.01\n' + BODY + '\n.end\n',
 'Y2_opt_bottom': HEAD + '\n' + BODY + '\n.options reltol=1e-09 trtol=0.01\n.end\n',
 'Y3_opt_before_end': HEAD + '\n' + BODY + '\n.options reltol=0.1\n.end\n',
 'Y4_opt_two':    HEAD + '\n.options reltol=1e-09\n' + BODY + '\n.options reltol=1e-09\n.end\n',
}
man={'tran':'tran 2n 2u 0 2n uic','cases':{}}
for name, text in CASES.items():
    (ENG/f'{name}.cir').write_text(text, encoding='ascii')
    (KEEP/'engine'/f'{name}.cir').write_text(text, encoding='ascii')
    L=[f'source {(ENG/f"{name}.cir").as_posix()}','begin-scope page Transient Analysis',
       'save $v1 $bb_in $bbo $v2','iplot $v1 $bb_in $bbo $v2',
       'tran 2n 2u 0 2n uic', f'write-and-destroy-iplot "{(ENG/f"{name}.raw").as_posix()}"','end-scope']
    (ENG/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    (KEEP/'engine'/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    man['cases'][name]={'has_options':'options' in text}
for d in (KEEP/'engine',ENG): (d/'manifest_pos.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
print('cases:',len(CASES))
