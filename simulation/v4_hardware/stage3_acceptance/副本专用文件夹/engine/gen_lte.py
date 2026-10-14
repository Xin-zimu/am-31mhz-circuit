"""Decisive LTE-control test.

Previous RC test was invalid: TMAX=10us clamped the step so LTE never bound.
Here TMAX = TSTOP (no clamp) on a SIN source, so the accepted step is decided
purely by local truncation error.
"""
from pathlib import Path
import json, hashlib

KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
(KEEP / 'engine').mkdir(parents=True, exist_ok=True)
HEAD = '* LTE control probe\n'
BODY = 'V1 in 0 SIN(0 1 1k)\nR1 in out 1k\nC1 out 0 100n\n'

CASES = {
 'L0_plain':      (None, [], 'no LTE control card at all'),
 'L1_opt_r1e-2':  ('.options reltol=1e-2', [], 'loose via .options'),
 'L2_opt_r1e-9':  ('.options reltol=1e-9', [], 'tight via .options'),
 'L3_set_r1e-2':  (None, ['set reltol = 0.01'], 'loose via set'),
 'L4_set_r1e-9':  (None, ['set reltol = 1e-09'], 'tight via set'),
 'L5_opt_guess':  ('.options reltol=1e-2', ['set reltol = 1e-2'], 'both channels'),
 'L6_opt_trtol':  ('.options reltol=1e-3 trtol=0.01', [], 'tight trtol via .options'),
 'L7_opt_plural': ('.option reltol=1e-9', [], 'singular spelling'),
}
man = {'tran': '1u 5m 0 5m uic (TMAX=TSTOP: no clamp)', 'cases': {}}
for name, (opt, sets, note) in CASES.items():
    body = HEAD + BODY + (opt + '\n' if opt else '') + '.end\n'
    cir = ENG / f'{name}.cir'; cir.write_text(body, encoding='ascii')
    (KEEP / 'engine' / f'{name}.cir').write_text(body, encoding='ascii')
    L = [f'source {cir.as_posix()}', 'begin-scope page Transient Analysis',
         'save $out'] + sets + [
         'tran 1u 5m 0 5m uic',
         f'write-and-destroy-iplot "{(ENG / (name + ".raw")).as_posix()}"', 'end-scope']
    p = ENG / f'{name}.cmd'; p.write_text('\n'.join(L) + '\n', encoding='ascii')
    (KEEP / 'engine' / f'{name}.cmd').write_text('\n'.join(L) + '\n', encoding='ascii')
    man['cases'][name] = {'options': opt, 'set': sets, 'note': note,
                          'netlist_sha256': hashlib.sha256(body.encode()).hexdigest()}
for d in (KEEP/'engine', ENG):
    (d/'manifest_lte.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
print('cases:', len(CASES))
