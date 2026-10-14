"""Extract the saved transient analysis block from decoded .ms14 XML (correct parse)."""
import re, json
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')

def block_at(t, start_idx):
    i = t.index('{', start_idx); depth = 0
    for j in range(i, len(t)):
        if t[j] == '{': depth += 1
        elif t[j] == '}':
            depth -= 1
            if depth == 0: return t[start_idx:j+1]
    return None

def report(label, path):
    t = path.read_text(encoding='ascii', errors='replace')
    # the analysis control block is the ANALYSIS:list preceded by TRAN:list{NODES...
    outs = []
    for m in re.finditer(r'TRAN:list\{NODES:list\{', t):
        # walk back to the enclosing ANALYSIS:list{
        a = t.rfind('ANALYSIS:list{', 0, m.start())
        if a < 0: continue
        blk = block_at(t, a)
        outs.append(blk)
    print('=' * 72)
    print(label, ' analysis blocks:', len(outs))
    if not outs: return
    blk = outs[0]
    for k in ['TSTEP','TSTOP','TSTART','TMAX','IC','MAX_POINTS','DISCARD_PLOTS']:
        mm = re.search(r'\b' + k + r':(\w+)\{([^}]*)\}', blk)
        print('   %-14s = %s' % (k, mm.group(2) if mm else None))
    om = re.search(r'ASYS_OPT:list\{(.*)\}\s*$', blk, re.S)
    body = om.group(1) if om else ''
    on, off = {}, {}
    for mm in re.finditer(r'\d+:list\{IsEnabled:long\{(\d)\}\s*([A-Za-z_][\w]*):([\w\.]+)\{([^}]*)\}', body):
        (on if mm.group(1) == '1' else off)[mm.group(2)] = mm.group(4)
    print('   ON :', on)
    print('   OFF:', off)
    # node list
    nm = re.search(r'UserNodes:list\{(.*?)\}\s*Nodes:list', blk, re.S)
    print('   UserNodes:', re.findall(r'NAME:string\{\$([^}]*)\}', nm.group(1)) if nm else None)
    return blk

report('TMAX1ns project', KEEP/'decoded_TMAX1ns.xml')
report('GEAR500 UIC project', KEEP/'decoded_GEAR500_UIC_20us.xml')
