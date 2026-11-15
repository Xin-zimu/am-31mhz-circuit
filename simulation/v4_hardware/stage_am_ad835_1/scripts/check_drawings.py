"""Cross-check each drawing against the netlist that produced its numbers.

Two directions are enforced:
  * every interface device in the simulated netlist must be drawn;
  * every ref-des drawn on the sheet must exist in that netlist.
That way a schematic cannot quietly omit a component (as B originally did)
nor invent one.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NET = ROOT / 'netlists'
DRAW = ROOT / 'drawings'

# ref-des prefixes that belong to the shared C4 carrier module or the fixture
EXTERNAL_REFS = {'Q1', 'QB', 'QG', 'R1', 'R2', 'R3', 'C1', 'C2', 'C3', 'C4',
                 'CSTRAY', 'CX0', 'VXM', 'RM', 'LM', 'CM', 'CIN', 'RBT', 'RBB',
                 'REB', 'COUTB', 'CG', 'RG1', 'RG2', 'RCG', 'REG', 'COUTG',
                 'VSUP', 'VSENSE', 'out'}
FIXTURE_REFS = {'RY', 'CY', 'RZ', 'CZ', 'IY', 'IZ', 'VY', 'VZ'}

SHEETS = {
    'A470_nom': '候选A_被动衰减',
    'B_Z06_nom': '候选B_射频缓冲',
    'C_B_nom': '候选C_YZ独立分支',
}


def interface_devices(netname):
    body = (NET / f'{netname}.cir').read_text(encoding='utf8')
    # start after the VSENSE sense element, whose node names are not parts
    tail = body.split('VSENSE', 1)[-1].split('\n', 1)[-1]
    tail = tail.split('.control', 1)[0]
    out = []
    for line in tail.splitlines():
        line = line.strip()
        if not line or line.startswith(('*', '.', '+')) or 'FIXTURE' in line:
            continue
        if line.startswith(('.', 'set ', 'op', 'print', 'save', 'tran',
                            'write', 'quit', 'end')):
            continue
        ref = line.split()[0]
        if ref in FIXTURE_REFS or ref in EXTERNAL_REFS:
            continue
        out.append(ref)
    return out


def main():
    ok = True
    for net, sheet in SHEETS.items():
        devs = interface_devices(net)
        manifest = DRAW / f'{sheet}.devices.json'
        drawn = json.loads(manifest.read_text(encoding='utf8')) if manifest.exists() else []
        print(f'\n=== {sheet}   <-  netlists/{net}.cir ===')
        print(f'  netlist interface devices : {", ".join(devs) or "(none)"}')
        print(f'  drawn on the sheet        : {", ".join(drawn) or "(none)"}')
        missing = [d for d in devs if d not in drawn]
        extra = [d for d in drawn if d not in devs]
        if missing:
            ok = False
            print(f'  NOT DRAWN : {", ".join(missing)}')
        if extra:
            ok = False
            print(f'  NOT IN NETLIST : {", ".join(extra)}')
        # ideal sources are topology markers, not components
        if not missing and not extra:
            print('  RESULT: drawing matches netlist')
            if 'VY' in (NET / f'{net}.cir').read_text(encoding='utf8'):
                print('         (VY/VZ are the ideal fixture connections, not parts)')
    print('\nOVERALL:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
