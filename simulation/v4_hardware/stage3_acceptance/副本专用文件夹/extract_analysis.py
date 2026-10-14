"""Extract the analysis control block (TSTEP/TSTOP/TMAX/IC + ASYS_OPT) from decoded projects."""
import re, json
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
WS   = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')

def find_block(t):
    for m in re.finditer(r'ANALYSIS:list\{', t):
        i = t.index('{', m.start()); depth = 0
        for j in range(i, len(t)):
            if t[j] == '{': depth += 1
            elif t[j] == '}':
                depth -= 1
                if depth == 0:
                    return t[m.start():j+1]
    return None

def opts(blk):
    m = re.search(r'ASYS_OPT:list\{(.*)\}\s*$', blk, re.S)
    body = m.group(1) if m else ''
    out = {}
    for mm in re.finditer(r'\d+:list\{IsEnabled:long\{(\d)\}\s*([A-Za-z_][\w]*):([\w\.]+)\{([^}]*)\}', body):
        out[mm.group(2)] = {'on': mm.group(1) == '1', 'val': mm.group(4)}
    return out

for label, path in [('TMAX1ns project', KEEP/'decoded_TMAX1ns.xml'),
                    ('GEAR500 UIC project', KEEP/'decoded_GEAR500_UIC_20us.xml')]:
    t = path.read_text(encoding='ascii', errors='replace')
    blk = find_block(t)
    print('='*70)
    print(label, 'block len', len(blk) if blk else None)
    for k in ['TSTEP','TSTOP','TSTART','TMAX','IC','MAX_POINTS']:
        m = re.search(r'\b'+k+r':(\w+)\{([^}]*)\}', blk)
        print('   %-11s = %s' % (k, m.group(2) if m else None))
    o = opts(blk)
    print('   ON :', {k: v['val'] for k, v in o.items() if v['on']})
    print('   OFF:', {k: v['val'] for k, v in o.items() if not v['on']})
