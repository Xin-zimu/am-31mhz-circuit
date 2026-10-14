"""Decisive experiment: inject the GUI's own option block into the netlist.

The engine 'set' command is a no-op (proved: set reltol/trtol/itl4/method changed nothing).
The netlist-level '.options' card is the control line that actually reaches the solver.
If the GUI option block alone reproduces the ~226 ns failure, the fault is control settings,
not circuit structure.
"""
from pathlib import Path
import hashlib, json, shutil

WS   = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS / '副本专用文件夹'
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
SRC  = WS / 'cold_gui_actual.cir'

base = SRC.read_bytes().rstrip()
assert b'.options' not in base.lower() and b'.option ' not in base.lower()

CASES = {
 'O0_none':      '',
 'O1_gui_all':   '.options reltol=0.0001 trtol=1 itl4=500 method=gear',
 'O2_reltol':    '.options reltol=0.0001',
 'O3_trtol':     '.options trtol=1',
 'O4_itl4':      '.options itl4=500',
 'O5_gear':      '.options method=gear',
 'O6_xspice_def':'.options reltol=0.001 trtol=7 itl4=100',
 'O7_convlimit': '.options reltol=0.0001 trtol=1 itl4=500 method=gear convlimit',
}
manifest = {'source': {'file': str(SRC), 'sha256': hashlib.sha256(SRC.read_bytes()).hexdigest()},
            'mechanism': 'netlist .options card appended, nothing else changed',
            'cases': {}}
for name, opt in CASES.items():
    body = base + b'\n' + (opt.encode('ascii') + b'\n' if opt else b'') + b'.end\n'
    cir = ENG / f'{name}.cir'
    cir.write_bytes(body)
    shutil.copy2(cir, KEEP / 'engine' / f'{name}.cir')
    cmd = (f'source {cir.as_posix()}\n'
           'begin-scope page Transient Analysis\n'
           'save $v1 $bb_in $bbo $v2\n'
           'iplot $v1 $bb_in $bbo $v2\n'
           'tran 2n 2u 0 2n uic\n'
           f'write-and-destroy-iplot "{(ENG / (name + ".raw")).as_posix()}"\n'
           'end-scope\n')
    p = ENG / f'{name}.cmd'
    p.write_text(cmd, encoding='ascii')
    shutil.copy2(p, KEEP / 'engine' / f'{name}.cmd')
    manifest['cases'][name] = {'options_card': opt, 'netlist_sha256': hashlib.sha256(body).hexdigest(),
                               'cmd': str(p), 'raw_expected': str(ENG / f'{name}.raw')}
(KEEP / 'engine' / 'manifest_options.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(ENG / 'manifest_options.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(manifest['cases'], indent=1))
