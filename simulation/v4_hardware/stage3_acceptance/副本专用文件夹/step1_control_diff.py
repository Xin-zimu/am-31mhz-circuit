"""Step 1 (S03-04): extract and compare GUI analysis-control blocks. Read-only."""
from pathlib import Path
import re, json, sys, hashlib

SRC = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
HERE = Path(__file__).resolve().parent

FILES = [
    'gui_baseline_audit.xml',
    'gui_2ms_saved_settings.xml',
    'cold_2ms_saved_settings.xml',
    'cold_explicit_zero_settings.xml',
    'trap500_20us_settings.xml',
    'gear500_20us_settings.xml',
    'gear500_reopen_saved_settings.xml',
    'gear500_uic_settings.xml',
]

def load(name):
    raw = (SRC / name).read_bytes()
    return raw.decode('ascii', 'replace'), hashlib.sha256(raw).hexdigest()

def transient_blocks(text):
    out = []
    for m in re.finditer(r'TRAN:list\{', text):
        start = m.start()
        # balanced braces from the '{'
        i = text.index('{', start)
        depth, j = 0, i
        while j < len(text):
            if text[j] == '{': depth += 1
            elif text[j] == '}':
                depth -= 1
                if depth == 0: break
            j += 1
        out.append((start, text[start:j+1]))
    return out

def kv(block):
    vals = {}
    for k in ['TSTEP', 'TSTOP', 'TSTART', 'TMAX', 'IC', 'MAX_POINTS', 'DISCARD_PLOTS']:
        m = re.search(r'\b' + k + r':(\w+)\{([^}]*)\}', block)
        vals[k] = m.group(2) if m else None
    return vals

def optgroup(block):
    m = re.search(r'ASYS_OPT:list\{(.*)\}\s*$', block, re.S)
    body = m.group(1) if m else ''
    opts = {}
    for mm in re.finditer(r'\d+:list\{IsEnabled:long\{(\d)\}\s*([A-Za-z_][\w]*):([\w\.]+)\{([^}]*)\}', body):
        opts[mm.group(2)] = {'enabled': mm.group(1) == '1', 'value': mm.group(4)}
    return opts

report = {}
for name in FILES:
    text, sha = load(name)
    blocks = transient_blocks(text)
    entry = {'sha256': sha, 'bytes': (SRC/name).stat().st_size, 'transient_count': len(blocks), 'transients': []}
    for pos, blk in blocks:
        entry['transients'].append({'offset': pos, 'kv': kv(blk), 'options': optgroup(blk)})
    # extra keyword presence anywhere in file
    entry['keywords'] = {k: len(re.findall(r'\b' + k + r'\b', text, re.I))
                         for k in ['suposc', 'convlimit', 'rshunt', 'dynamicdc', 'inertialdelay', 'method', 'maxord', 'zero_ic', 'uic']}
    report[name] = entry

(HERE / 'step1_control_scan.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# print a compact comparison
names = list(report)
print('files:', len(names))
for n in names:
    e = report[n]
    print('=' * 70)
    print(n, e['sha256'][:16], e['bytes'], 'transients=', e['transient_count'])
    for i, t in enumerate(e['transients']):
        print('  [%d] @%d %s' % (i, t['offset'], t['kv']))
        en = {k: v['value'] for k, v in t['options'].items() if v['enabled']}
        dis = {k: v['value'] for k, v in t['options'].items() if not v['enabled']}
        print('      ON :', en)
        print('      OFF:', dis)
    print('  keywords:', e['keywords'])
