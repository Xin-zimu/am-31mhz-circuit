"""Read-only netlist inspection: engine vs GUI entry, switches, time-dependent sources.

No simulator calls.
"""
from pathlib import Path
import re
import difflib
import json

BASE = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
GUI_ACTUAL = BASE / '副本专用文件夹/gui_evidence_20261014/S03_GUI_COLD_20us_actual.cir'
ENGINE = BASE / 'cold_engine_gui_net.cir'
ENGINE_7MS = BASE / '副本专用文件夹/engine/L_7ms_1ns.cir'
OUT = Path(__file__).resolve().parent


def read_net(p):
    b = Path(p).read_bytes()
    if b.startswith((b'\xff\xfe', b'\xfe\xff')):
        return b.decode('utf-16')
    return b.decode('utf-8-sig', errors='replace')


def control_lines(text):
    return [l.strip() for l in text.splitlines()
            if re.match(r'^\s*\.(tran|options?|ic|nodeset|temp|width|save|print|four|ac|dc|op|step|end|include|lib|param)\b',
                        l, re.I)]


def census(text):
    counts = {}
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        c = s[0].upper()
        counts[c] = counts.get(c, 0) + 1
    return counts


def switches(text):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r'^[sSwW]\w*\s', s) and not s.upper().startswith(('SUBCKT', 'SET')):
            out.append(s)
    return out


def switch_models(text):
    return [l.strip() for l in text.splitlines()
            if re.search(r'\.model\s+\S+\s+(sw|vswitch|csw)\b', l, re.I)]


def time_dependent(text):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if re.search(r'\b(sin|sine|pulse|pwl|exp|sffm|am)\s*\(', s, re.I):
            out.append(s)
    return out


def behavioral(text):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r'^[bB]\w*\s', s) or re.search(r'\bV\s*=\s*\{|\bI\s*=\s*\{', s):
            out.append(s)
    return out


report = {}
for label, path in [('GUI actual export', GUI_ACTUAL),
                    ('ENGINE (same circuit)', ENGINE),
                    ('ENGINE 7 ms', ENGINE_7MS)]:
    print('=' * 78)
    print(f'{label}: {path.name}  ({path.stat().st_size} bytes)')
    print('=' * 78)
    if not path.exists():
        print('  MISSING')
        continue
    text = read_net(path)
    ctrl = control_lines(text)
    print('  control lines (.tran/.options/.ic/...):')
    print('    ' + (', '.join(ctrl) if ctrl else '(NONE)'))
    cen = census(text)
    print('  element census: ' + ', '.join(f'{k}={v}' for k, v in sorted(cen.items())))
    sw = switches(text)
    sm = switch_models(text)
    print(f'  switch elements: {len(sw)}')
    for s in sw[:6]:
        print('    ' + s[:110])
    if len(sw) > 6:
        print(f'    ... (+{len(sw)-6} more)')
    print(f'  switch models: {len(sm)}')
    for s in sm:
        print('    ' + s[:110])
    td = time_dependent(text)
    print(f'  time-dependent source functions: {len(td)}')
    for s in td[:8]:
        print('    ' + s[:110])
    bh = behavioral(text)
    print(f'  behavioral sources: {len(bh)}')
    for s in bh[:8]:
        print('    ' + s[:110])
    report[label] = {'file': path.name, 'bytes': path.stat().st_size,
                     'control_lines': ctrl, 'switches': len(sw), 'switch_models': sm,
                     'time_dependent': td, 'behavioral': bh}
    print()

# Are the GUI-actual and engine netlists the same circuit?
if GUI_ACTUAL.exists() and ENGINE.exists():
    a = read_net(GUI_ACTUAL).splitlines()
    b = read_net(ENGINE).splitlines()
    print('=' * 78)
    print(f'DIFF  {GUI_ACTUAL.name}  vs  {ENGINE.name}   '
          f'({len(a)} vs {len(b)} lines)')
    print('=' * 78)
    diff = list(difflib.unified_diff(a, b, lineterm='', n=0))
    # ignore pure index/name churn: show only meaningful lines
    shown = 0
    for line in diff:
        if line.startswith(('---', '+++', '@@')):
            if shown < 60:
                print(line)
            continue
        if line.startswith(('+', '-')):
            if shown < 60:
                print(line[:150])
            shown += 1
    print(f'  total changed lines: {shown}')
    report['diff_changed_lines'] = shown
    report['diff_lines'] = [l[:200] for l in diff if l.startswith(('+', '-'))
                            and not l.startswith(('+++', '---'))][:60]

(OUT / 'netlist_inspection.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print('7 carrier periods at 31 MHz = %.6f ns' % (7 / 31e6 * 1e9))
print('observed GUI failure time  = 225.797635 ns')
print('1/(32*31MHz)               = %.6f ns  (= the 1.0080645161290323 ns cap)' % (1 / (32 * 31e6) * 1e9))
