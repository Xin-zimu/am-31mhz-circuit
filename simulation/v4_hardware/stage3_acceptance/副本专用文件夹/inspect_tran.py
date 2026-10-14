"""Inspect the TMAX1ns project's saved transient analysis block."""
import re, json, sys
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

def spans(t, key):
    out = []
    for m in re.finditer(r'(?<![A-Za-z_])' + re.escape(key) + r'\{', t):
        i = t.index('{', m.start()); depth = 0
        for j in range(i, len(t)):
            if t[j] == '{': depth += 1
            elif t[j] == '}':
                depth -= 1
                if depth == 0:
                    out.append((m.start(), j+1, t[m.start():j+1])); break
    return out

t = (KEEP/'decoded_TMAX1ns.xml').read_text(encoding='ascii', errors='replace')
tr = spans(t, 'TRAN:list')
print('TRAN blocks:', len(tr))
for off, end, blk in tr[:1]:
    print('--- block at', off, 'len', len(blk), '---')
    print(blk[:1600])
