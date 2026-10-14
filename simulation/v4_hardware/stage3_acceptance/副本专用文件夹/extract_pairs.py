"""Pair each ANALYSIS:list with the ASYS_OPT that follows it, in file order."""
import re, json
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

def balanced(t, start):
    j = t.index('{', start); depth = 0
    for k in range(j, len(t)):
        if t[k] == '{': depth += 1
        elif t[k] == '}':
            depth -= 1
            if depth == 0: return t[start:k+1]
    return None

def analyses(t):
    out = []
    for m in re.finditer(r'ANALYSIS:list\{', t):
        blk = balanced(t, m.start())
        aend = m.start() + len(blk)
        after = t[aend:aend + 6000]
        om = re.search(r'ASYS_OPT:list\{', after)
        opt = balanced(after, om.start()) if om else ''
        out.append((blk, opt))
    return out

for label, name in [('TMAX1ns', 'decoded_TMAX1ns.xml'), ('GEAR500_UIC(fails)', 'decoded_GEAR500_UIC_20us.xml')]:
    t = (KEEP/name).read_text(encoding='ascii', errors='replace')
    print('=' * 74)
    print(label, ' analysis blocks:', len(analyses(t)))
    for i, (blk, opt) in enumerate(analyses(t)):
        kv = {}
        for k in ['TSTEP','TSTOP','TSTART','TMAX','IC']:
            m = re.search(r'(?<![A-Za-z])'+k+r':(\w+)\{([^}]*)\}', blk)
            kv[k] = m.group(2) if m else None
        on = {mm.group(1): mm.group(3) for mm in re.finditer(r'\d+:list\{IsEnabled:long\{1\}\s*([A-Za-z_][\w]*):([\w\.]+)\{([^}]*)\}', opt)}
        print('  [%d] %s' % (i, kv))
        print('      ASYS_OPT ON: %s' % on)
