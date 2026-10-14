"""Corrected RC sensitivity test - netlist must start with a comment, not a title.

Finding: Multisim's nutmeg 'source' does NOT consume a SPICE title line.
A leading non-comment line becomes a component. Prefix with '*'.
"""
from pathlib import Path
import json, hashlib

KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
(KEEP / 'engine').mkdir(parents=True, exist_ok=True)

HEAD  = '* RC tolerance probe\n'
BODY  = 'V1 in 0 PULSE(0 1 0 1n 1n 5u 10u)\nR1 in out 1k\nC1 out 0 100n\n'

CASES = {
 'S0_plain':      (None, [], 'no card, no set'),
 'S1_opt_loose':  ('.options reltol=0.1 trtol=20', [], 'loose LTE via .options'),
 'S2_opt_tight':  ('.options reltol=1e-9 trtol=0.1', [], 'tight LTE via .options'),
 'S3_set_loose':  (None, ['set reltol = 0.1', 'set trtol = 20'], 'loose LTE via set'),
 'S4_set_tight':  (None, ['set reltol = 1e-9', 'set trtol = 0.1'], 'tight LTE via set'),
 'S5_opt_gear':   ('.options method=gear', [], 'gear via .options'),
 'S6_set_gear':   (None, ['set method = gear'], 'gear via set'),
}
man = {'tran': '1u 200u 0 10u uic', 'cases': {}}
for name, (opt, sets, note) in CASES.items():
    body = HEAD + BODY + (opt + '\n' if opt else '') + '.end\n'
    cir = ENG / f'{name}.cir'; cir.write_text(body, encoding='ascii')
    (KEEP / 'engine' / f'{name}.cir').write_text(body, encoding='ascii')
    L = [f'source {cir.as_posix()}', 'begin-scope page Transient Analysis',
         'save $out'] + sets + [
         'tran 1u 200u 0 10u uic',
         f'write-and-destroy-iplot "{(ENG / (name + ".raw")).as_posix()}"', 'end-scope']
    p = ENG / f'{name}.cmd'; p.write_text('\n'.join(L) + '\n', encoding='ascii')
    (KEEP / 'engine' / f'{name}.cmd').write_text('\n'.join(L) + '\n', encoding='ascii')
    man['cases'][name] = {'options': opt, 'set': sets, 'note': note,
                          'netlist_sha256': hashlib.sha256(body.encode()).hexdigest()}
for d in (KEEP/'engine', ENG):
    (d/'manifest_rc3.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
print('cases:', len(CASES))
print(HEAD + BODY + '.end')
