"""Test option-channel ordering: 'set' before vs after 'source'."""
from pathlib import Path
import json, hashlib
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
base = (KEEP/'原始只读引用'/'cold_gui_actual.cir').read_bytes().rstrip()
CASES = {
 'V0_after':  ('after',  [('reltol','0.0001'),('trtol','1'),('itl4','500'),('method','gear')]),
 'V1_before': ('before', [('reltol','0.0001'),('trtol','1'),('itl4','500'),('method','gear')]),
 'V2_before_loose': ('before', [('reltol','0.1'),('trtol','20')]),
 'V3_after_loose':  ('after',  [('reltol','0.1'),('trtol','20')]),
}
man = {'tran':'2n 2u 0 2n uic','cases':{}}
for name,(where,opts) in CASES.items():
    body = base + b'\n.end\n'
    cir = ENG/f'{name}.cir'; cir.write_bytes(body)
    (KEEP/'engine').mkdir(parents=True, exist_ok=True)
    (KEEP/'engine'/f'{name}.cir').write_bytes(body)
    sets = [f'set {k} = {v}' for k,v in opts]
    L = []
    if where=='before': L += sets
    L += [f'source {cir.as_posix()}','begin-scope page Transient Analysis','save $v1 $bb_in $bbo $v2','iplot $v1 $bb_in $bbo $v2']
    if where=='after': L += sets
    L += ['tran 2n 2u 0 2n uic', f'write-and-destroy-iplot "{(ENG/(name+".raw")).as_posix()}"','end-scope']
    (ENG/f'{name}.cmd').write_text('\n'.join(L)+'\n', encoding='ascii')
    (KEEP/'engine'/f'{name}.cmd').write_text('\n'.join(L)+'\n', encoding='ascii')
    man['cases'][name] = {'set_position':where,'options':opts,'cmd':str(ENG/f'{name}.cmd')}
for d in (KEEP/'engine', ENG):
    (d/'manifest_order.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(man, indent=1))
