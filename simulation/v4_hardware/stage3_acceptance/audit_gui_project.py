"""Read-only comparison of saved native component blocks and analysis settings."""
from pathlib import Path
import re, json, hashlib
HERE = Path(__file__).resolve().parent
a = (HERE/'gui_baseline_audit.xml').read_text(encoding='ascii')
b = (HERE/'gui_saved_settings.xml').read_text(encoding='ascii')
pattern = r'<CiComponent Class="CiComponent".*?</CiComponent>'
ca, cb = re.findall(pattern,a,re.S), re.findall(pattern,b,re.S)
assert ca and len(ca)==len(cb)
changed = [i for i,(x,y) in enumerate(zip(ca,cb)) if x!=y]
def without_runtime_ids(s):
    return re.sub(r'\b(SymCompID|Circuit|CiID|Model)="[0-9]+"', r'\1="RUNTIME_ID"', s)
parameter_changes = [i for i,(x,y) in enumerate(zip(ca,cb))
                     if without_runtime_ids(x)!=without_runtime_ids(y)]
def digest(name):
    p = HERE/name
    return {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
start = b.index('TRAN:list{')
an = b.index('ANALYSIS:list{',start)
result = {'baseline':digest('S03_BASELINE_V4_3.ms14'),
          'gui_working_copy':digest('S03_GUI_5ms_V4_3.ms14'),
          'component_count':len(ca), 'changed_component_indexes':changed,
          'component_blocks_identical':not changed,
          'component_content_identical_ignoring_runtime_ids':not parameter_changes,
          'changed_component_content_indexes':parameter_changes,
          'runtime_id_note':'Native save regenerates SymCompID, Circuit, CiID, Model numeric references; this comparison alone does not verify wire topology or referenced external models.',
          'saved_transient_analysis':b[an:an+1200]}
(HERE/'gui_project_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
