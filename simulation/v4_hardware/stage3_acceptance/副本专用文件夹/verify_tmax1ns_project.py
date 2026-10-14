"""Verify the TMAX1ns project: active transient settings + capacitor initial conditions."""
import re
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

def active_analysis(t):
    """First ANALYSIS:list after a TRAN:list - the analysis the project runs."""
    i = t.find('ANALYSIS:list{')
    while i >= 0:
        # balanced block
        j = t.index('{', i); depth = 0
        for k in range(j, len(t)):
            if t[k] == '{': depth += 1
            elif t[k] == '}':
                depth -= 1
                if depth == 0: break
        blk = t[i:k+1]
        if 'TRAN:list{' in blk:
            return blk
        i = t.find('ANALYSIS:list{', k)
    return None

def show(label, name):
    t = (KEEP/name).read_text(encoding='ascii', errors='replace')
    blk = active_analysis(t)
    print('='*72)
    print(label)
    print('  block chars:', len(blk))
    for key in ['TSTEP','TSTOP','TSTART','TMAX','IC']:
        m = re.search(r'(?<![A-Za-z])'+key+r':(\w+)\{([^}]*)\}', blk)
        print('    %-8s = %s' % (key, m.group(2) if m else None))
    om = re.search(r'ASYS_OPT:list\{(.*)\}\s*$', blk, re.S)
    body = om.group(1) if om else ''
    on = {mm.group(1): mm.group(3) for mm in re.finditer(r'\d+:list\{IsEnabled:long\{1\}\s*([A-Za-z_][\w]*):([\w\.]+)\{([^}]*)\}', body)}
    print('    ASYS_OPT ON:', on)
    nm = re.search(r'UserNodes:list\{(.*?)\}\s*Nodes:list', blk, re.S)
    print('    UserNodes:', re.findall(r'NAME:string\{\$([^}]*)\}', nm.group(1)) if nm else None)
    # capacitor ICs by parameter block
    for cap in ['C111','C115','CBB']:
        m = re.search(r'LocalName="&amp;ASC'+cap+r'"', t)
        if not m: print('    %-5s: component not found' % cap); continue
        seg = t[m.start():m.start()+4000]
        vals = re.findall(r'(?:Value|IC|InitialCondition|Parameter)[^>]{0,120}', seg)
        print('    %-5s ->' % cap, [v[:90] for v in vals[:3]])

show('TMAX1ns project', 'decoded_TMAX1ns.xml')
show('GEAR500 UIC project (fails)', 'decoded_GEAR500_UIC_20us.xml')
