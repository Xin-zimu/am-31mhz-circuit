"""Step 6: supply rise-time orthogonal control.

Replace the ideal DC source feeding the comparator with a PWL ramp of 1/10/100 ns.
This changes the test condition, so it is archived separately and is NOT evidence
for the nominal cold start.
"""
from pathlib import Path
import json, re
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
base = (KEEP/'原始只读引用'/'cold_gui_actual.cir').read_text(encoding='ascii')
(KEEP/'engine').mkdir(parents=True, exist_ok=True)

# find the DC supply lines that set the 4.5 V / 5 V rails
dclines = [l for l in base.split('\n') if re.match(r'^v\w+\s+\S+\s+0\s+dc\s', l, re.I)]
print('DC supply lines found:')
for l in dclines: print('   ', l.strip())

CASES = {
 'RT_ideal':  '',
 'RT_1ns':    '1n',
 'RT_10ns':   '10n',
 'RT_100ns':  '100n',
}
man = {'note': 'PWL rise time on the ideal 5 V rail; separate archive, changes test conditions',
       'dc_lines': [l.strip() for l in dclines], 'cases': {}}
for name, rt in CASES.items():
    text = base
    if rt:
        # V5 at 5 V, VCC/VREF rails derived from it: ramp every 5 V-class DC source
        text = re.sub(r'^(vV5\s+V5\s+0\s+dc\s+)([\d\.]+)',
                      lambda m: m.group(1) + m.group(2) + ' PWL(0 0 ' + rt + ' ' + m.group(2) + ')',
                      text, flags=re.I | re.M)
    body = text.rstrip() + '\n.end\n'
    (ENG/f'{name}.cir').write_text(body, encoding='ascii')
    (KEEP/'engine'/f'{name}.cir').write_text(body, encoding='ascii')
    L=[f'source {(ENG/f"{name}.cir").as_posix()}','begin-scope page Transient Analysis',
       'save $v1 $bb_in $bbo $v2','iplot $v1 $bb_in $bbo $v2',
       'tran 1n 20u 0 1n uic', f'write-and-destroy-iplot "{(ENG/f"{name}.raw").as_posix()}"','end-scope']
    (ENG/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    (KEEP/'engine'/f'{name}.cmd').write_text('\n'.join(L)+'\n',encoding='ascii')
    man['cases'][name]={'rise_time': rt or 'ideal step','tran':'1n 20u 0 1n uic'}
for d in (KEEP/'engine',ENG): (d/'manifest_risetime.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(man['cases'],indent=1))
