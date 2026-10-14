"""Determine which control channel actually reaches the solver.

tran uses TMAX=100n so LTE (reltol/trtol) has room to bite; a 31 MHz signal at
100 ns steps is aliased on purpose - we are counting solver behaviour, not waveforms.
"""
from pathlib import Path
import hashlib, json, shutil

WS   = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS / '副本专用文件夹'
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
SRC  = WS / 'cold_gui_actual.cir'
base = SRC.read_bytes().rstrip()

# name: (options_card or None, list of set commands, note)
CASES = {
 'T1_base':        (None, [], 'no control card at all'),
 'T2_opt_loose':   ('.options reltol=0.1 trtol=7', [], 'very loose LTE via .options'),
 'T3_opt_tight':   ('.options reltol=1e-9 trtol=1', [], 'very tight LTE via .options'),
 'T4_set_loose':   (None, ['set reltol = 0.1'], 'very loose LTE via set'),
 'T5_set_rshunt1': (None, ['set rshunt = 1'], 'rshunt=1 ohm: must change values if set works'),
 'T6_opt_rshunt1': ('.options rshunt=1', [], 'rshunt=1 ohm via .options'),
}
man = {'staging': str(ENG), 'tran': '2n 500n 0 100n uic', 'cases': {}}
for name, (opt, sets, note) in CASES.items():
    body = base + b'\n' + (opt.encode('ascii') + b'\n' if opt else b'') + b'.end\n'
    cir = ENG / f'{name}.cir'; cir.write_bytes(body)
    shutil.copy2(cir, KEEP / 'engine' / f'{name}.cir')
    L = [f'source {cir.as_posix()}', 'begin-scope page Transient Analysis',
         'save $v1 $bb_in $bbo $v2', 'iplot $v1 $bb_in $bbo $v2']
    L += sets
    L += ['tran 2n 500n 0 100n uic',
          f'write-and-destroy-iplot "{(ENG / (name + ".raw")).as_posix()}"', 'end-scope']
    cmd = ENG / f'{name}.cmd'; cmd.write_text('\n'.join(L) + '\n', encoding='ascii')
    shutil.copy2(cmd, KEEP / 'engine' / f'{name}.cmd')
    man['cases'][name] = {'options': opt, 'set': sets, 'note': note,
                          'netlist_sha256': hashlib.sha256(body).hexdigest()}
(KEEP/'engine'/'manifest_channels.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
(ENG/'manifest_channels.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(man, indent=1)[:1200])
