"""Step 1: rigorous netlist + control-line comparison. Read-only on sources."""
from pathlib import Path
import re, json, hashlib, difflib

SRC = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
SCRATCH = Path(r'D:\ms_xsp\stage3_acceptance')
OUT = SRC / '副本专用文件夹'

def read_text(p):
    return Path(p).read_text(encoding='ascii', errors='replace')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

pairs = [
    ('GUI-export (UIC project)', SRC/'cold_gui_actual.cir', None),
    ('engine-run header(same bytes)', SRC/'cold_engine_gui_net.cir', None),
    ('engine-run nominal', SRC/'nominal_full.cir', None),
    ('GUI-exported nominal_full(copy)', None, None),
]

gui = read_text(SRC/'cold_gui_actual.cir')
eng_gui = read_text(SRC/'cold_engine_gui_net.cir')
nom = read_text(SRC/'nominal_full.cir')

def norm(t):
    # strip trailing whitespace and drop empty lines for structural compare
    return [l.rstrip() for l in t.replace('\r\n','\n').split('\n')]

a = norm(gui); b = norm(eng_gui); c = norm(nom)
print('GUI-export lines      :', len(a), sha(SRC/'cold_gui_actual.cir')[:16])
print('engine gui_net lines  :', len(b), sha(SRC/'cold_engine_gui_net.cir')[:16])
print('engine nominal lines  :', len(c), sha(SRC/'nominal_full.cir')[:16])

# compare ignoring blank lines
def solid(lines): return [l for l in lines if l.strip()!='']
sa, sb, sc = solid(a), solid(b), solid(c)
print('solid lines gui/engine-gui/engine-nominal:', len(sa), len(sb), len(sc))
print('gui == engine-gui minus .end ?', sa == [l for l in sb if l.strip().lower()!='.end'])
print('gui == engine-nominal ?', sa == sc)

dl = [d for d in difflib.unified_diff(sa, sc, 'GUI', 'engine_nominal', lineterm='', n=0)]
print('--- GUI vs engine_nominal (solid) diff, %d lines ---' % len(dl))
print('\n'.join(dl[:80]))
print()

# control lines in each
def ctrl(lines):
    return [l.strip() for l in lines if l.strip().startswith('.') and re.match(
        r'\.(tran|options|opt|ic|nodeset|temp|width|op|end|dc|ac|four|step|meas)\b', l.strip(), re.I)]
for name, lines in [('GUI-export', a), ('engine-gui-net', b), ('engine-nominal', c)]:
    print(name, 'control directives:', ctrl(lines))
