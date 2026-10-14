from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
WORK = Path('D:/ms_xsp/v3_20k')
WORK.mkdir(parents=True, exist_ok=True)
base = (HERE.parents[1]/'debug/xsp_kit_ascii/net_am.cir').read_text()
base = '* ' + base
commands = []
for amp in [1, 2, 3, 4]:
    name = f'baseline_A{amp}'
    net = re.sub(r'VINPUT[^\n]+', f'VINPUT V1 0 PULSE(0 {amp} 10u 20n 20n 25u 50u)', base)
    (WORK/f'{name}.cir').write_text(net, encoding='ascii')
    commands += [f'source {WORK/name}.cir', 'begin-scope page Transient Analysis',
                 'checknodes 3', 'save $v1 $v2 $tp6 $tp3 $tp2',
                 'iplot $v1 $v2 $tp6 $tp3 $tp2', 'set trtol = 7', 'set itl4 = 100',
                 'set convlimit', 'set rshunt = 1e+012', 'set dynamicdc', 'set inertialdelay',
                 'tran -env-options 2n 5m 4.8m 2n auto_ic auto_tstep auto_tmax',
                 f'write-and-destroy-iplot "{WORK/name}.raw"', 'end-scope']
(WORK/'baseline.cmd').write_text('\n'.join(commands).replace('D:/', 'D:\\').replace('/v3_20k/', '\\v3_20k\\')+'\n', encoding='ascii')
print(WORK/'baseline.cmd')
