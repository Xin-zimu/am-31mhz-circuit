"""Prepare S03-05 input-only variants of the accepted complete netlist."""
from pathlib import Path
import csv
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
OLD = STAGE / '副本专用文件夹' / 'final2_20261014'
RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')
CASES = [('C1', 1, 10), ('C2', 1, 50), ('C3', 4, 10), ('C6', 4, 30), ('C7', 3, 50)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    base = (OLD / 'REF_4Vpp_tail.cir').read_bytes()
    template = (OLD / 'REF_4Vpp_tail.cmd').read_text(encoding='ascii')
    table_path = STAGE.parent / 'potentiometer_settings.csv'
    rows = list(csv.DictReader(table_path.open(encoding='utf-8-sig')))
    manifest = {'date': '2026-10-14', 'runtime_dir': str(RUNTIME),
                'baseline': str(OLD / 'REF_4Vpp_tail.cir'), 'baseline_sha256': sha(base),
                'calibration_source': str(table_path), 'calibration_sha256': sha(table_path.read_bytes()),
                'tran': 'tran 2n 5m 4.5m 2n uic',
                'initial': 'UIC; C111=0.43 V, C115=-4.1 V, CBB=4.5 V; precharged',
                'entry': 'COM DoCommandLine source+tran engine; not native GUI',
                'effective_tolerance': 'engine defaults reltol=1e-3/trtol=7, per S03-04 diagnosis; retained set lines do not establish applied tolerance',
                'cases': [], 'reuse': {'C4': str(OLD / 'REF_4Vpp_tail.cir'), 'C5': str(OLD / 'LIN_2Vpp_tail.cir')}}
    for case, amplitude, duty in CASES:
        row = next(r for r in rows if int(r['D_percent']) == duty and int(r['Vpp']) == amplitude)
        # Preserve the rounded, accepted 4 Vpp divider and 50% duty divider
        # exactly when those controls are not being changed.
        targets = {}
        if amplitude != 4:
            targets.update({k: f'{float(row[k[1:]+"_ohm"]):.6f}' for k in ('rRVAT', 'rRVAB')})
        if duty != 50:
            targets.update({k: f'{float(row[k[1:]+"_ohm"]):.6f}' for k in ('rRVDT', 'rRVDB')})
        net = base
        changes = []
        for comp, value in targets.items():
            pattern = rb'(?m)^(' + comp.encode() + rb'\s+\S+\s+\S+\s+)(\S+)'
            match = re.search(pattern, net)
            assert match, comp
            changes.append({'component': comp, 'from': match[2].decode(), 'to': value})
            net, count = re.subn(pattern, lambda m: m[1] + value.encode(), net)
            assert count == 1
        changed_lines = [(a.decode(), b.decode()) for a, b in zip(base.splitlines(), net.splitlines()) if a != b]
        assert len(base.splitlines()) == len(net.splitlines())
        assert len(changed_lines) == len(targets)
        assert all(a.split()[0] in targets for a, b in changed_lines)
        tag = f'{case}_{amplitude}Vpp_D{duty}_5ms'
        cmd = template.replace('D:/ms_xsp/stage3_acceptance/s0304_final2_20261014', RUNTIME.as_posix()).replace('REF_4Vpp_tail', tag).encode('ascii')
        for directory in (HERE, RUNTIME):
            for suffix, data in (('.cir', net), ('.cmd', cmd)):
                path = directory / (tag + suffix)
                if path.exists():
                    assert path.read_bytes() == data, f'Refusing overwrite: {path}'
                else:
                    path.write_bytes(data)
        manifest['cases'].append({'case': case, 'tag': tag, 'target_vpp': amplitude, 'target_duty_percent': duty,
                                  'changes': changes, 'cir_sha256': sha(net), 'cmd_sha256': sha(cmd),
                                  'all_other_netlist_bytes_unchanged': True})
    (HERE / 'run_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
