"""Prepare isolated command-engine runs; never alter existing projects or data."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'engine/L_7ms_1ns.cir'
RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0304_acceptance_20261014')
RUNTIME.mkdir(parents=True, exist_ok=True)
base = SRC.read_bytes()
cases = {
    'TSTART_full20us': ('20u', '0', None),
    'TSTART_tail20us': ('20u', '10u', None),
    'COLD_A4_9ms_tail': ('9m', '8.5m', None),
    'COLD_A2_9ms_tail': ('9m', '8.5m', ('10905.5', '9094.46')),
}
manifest = {'date': '2026-10-14', 'authorization': 'User agreed to skip native GUI reproduction as a prerequisite.',
    'scope': 'Multisim command-line engine source + tran, dispatched via COM DoCommandLine. No native GUI pass claimed.',
    'source': str(SRC), 'source_sha256': hashlib.sha256(base).hexdigest(),
    'requested_tstep_s': 1e-9, 'requested_tmax_s': 1e-9,
    'initial': 'UIC, C111/C115/CBB zero, ideal supplies, calculation from t=0',
    'effective_solver_options_equality_to_gui': 'not proven, not claimed', 'cases': {}}
for tag, (stop, start, amplitude) in cases.items():
    net = base
    changes = []
    if amplitude:
        for component, value in zip(['rRVAT', 'rRVAB'], amplitude):
            pattern = rb'(?m)^('+component.encode()+rb'\s+\S+\s+\S+\s+)(\S+)'
            old = re.search(pattern, net).group(2).decode('ascii')
            net, count = re.subn(pattern, lambda m: m.group(1)+value.encode(), net)
            assert count == 1
            changes.append({'component': component, 'old_ohm': old, 'new_ohm': value})
    for receiver in [b'rRG_BB BB_FB VREF 10000', b'rRF_BB BBO FB_TRIM 150000',
                     b'rRV_BB FB_TRIM BB_FB 3511', b'rRLOAD V2 0 1000000']:
        assert receiver in net
    cmd = f'''source {RUNTIME.as_posix()}/{tag}.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n {stop} {start} 1n uic
write-and-destroy-iplot "{RUNTIME.as_posix()}/{tag}.raw"
end-scope
'''.encode('ascii')
    for directory in [HERE, RUNTIME]:
        for ext, data in [('cir', net), ('cmd', cmd)]:
            path = directory/f'{tag}.{ext}'
            with path.open('xb') as f:
                f.write(data)
    manifest['cases'][tag] = {'tran': f'tran 1n {stop} {start} 1n uic', 'changes': changes,
        'netlist_sha256': hashlib.sha256(net).hexdigest(), 'command_sha256': hashlib.sha256(cmd).hexdigest()}
(HERE/'run_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=False, indent=2))
