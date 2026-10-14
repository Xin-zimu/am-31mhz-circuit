"""Confirm the TMAX1ns project differs from GEAR500_UIC only in TMAX/TSTEP.

Component blocks must be identical (ignoring runtime ids), and only the transient
analysis control values may differ.
"""
from pathlib import Path
import re
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

def comps(t):
    return re.findall(r'<CiComponent Class="CiComponent".*?</CiComponent>', t, re.S)
def norm(b):
    return re.sub(r'\b(SymCompID|Circuit|CiID|Model)="[0-9]+"', r'\1="RID"', b)

a = (KEEP/'decoded_TMAX1ns.xml').read_text(encoding='ascii', errors='replace')
b = (KEEP/'decoded_GEAR500_UIC_20us.xml').read_text(encoding='ascii', errors='replace')
ca, cb = comps(a), comps(b)
print('component counts:', len(ca), len(cb))
print('byte-identical blocks:', ca == cb)
na, nb = [norm(x) for x in ca], [norm(x) for x in cb]
diff = [i for i,(x,y) in enumerate(zip(na,nb)) if x != y]
print('blocks differing ignoring runtime ids:', len(diff))

# Capacitor ICs
for lbl, t in [('TMAX1ns', a), ('GEAR500UIC', b)]:
    for name in ['C111','C115','CBB']:
        m = re.search(r'LocalName="&amp;ASC'+name+r'".*?</CiComponent>', t, re.S)
        blk = m.group(0) if m else ''
        val = re.search(r'(?:IC|InitialCondition)[^>]{0,80}', blk)
        print('  %-10s %-5s -> %s' % (lbl, name, val.group(0)[:70] if val else 'n/a'))
    # transient controls only
    ts = re.findall(r'TSTEP:double\{([^}]*)\}', t)
    tm = re.findall(r'TMAX:(\w+)\{([^}]*)\}', t)
    ic = re.findall(r'IC:string\{([^}]*)\}', t)
    print('  %-10s TSTEP=%s TMAX=%s IC=%s' % (lbl, set(ts), set(x[1] for x in tm), set(ic)))
