"""Locate the transient control values in decoded project XML by direct search."""
import re
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

for label, name in [('TMAX1ns','decoded_TMAX1ns.xml'), ('GEAR500UIC','decoded_GEAR500_UIC_20us.xml')]:
    t = (KEEP/name).read_text(encoding='ascii', errors='replace')
    print('='*72)
    print(label, len(t), 'chars')
    for k in ['TSTEP','TSTOP','TSTART','TMAX','IC','MAX_POINTS','DISCARD_PLOTS']:
        hits = [(m.start(), m.group(2)) for m in re.finditer(r'(?<![A-Za-z])'+k+r':(\w+)\{([^}]*)\}', t)]
        # keep the first few distinct
        vals = []
        for pos, v in hits:
            if v not in vals: vals.append(v)
        print('   %-14s n=%-4d values=%s' % (k, len(hits), vals[:6]))
    # ASYS_OPT enabled items
    m = re.search(r'ASYS_OPT:list\{', t)
    if m:
        i = t.index('{', m.start()); depth=0
        for j in range(i, len(t)):
            if t[j]=='{': depth+=1
            elif t[j]=='}':
                depth-=1
                if depth==0: break
        blk = t[m.start():j+1]
        on = {}
        for mm in re.finditer(r'\d+:list\{IsEnabled:long\{1\}\s*([A-Za-z_][\w]*):([\w\.]+)\{([^}]*)\}', blk):
            on[mm.group(1)] = mm.group(3)
        print('   ASYS_OPT ON:', on)
        print('   ASYS_OPT len:', len(blk))
