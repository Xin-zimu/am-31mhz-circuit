"""Hash all deliverables, excluding this manifest and disposable Python caches."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[2]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
sources=[PROJECT/'电子线路实验评分标准-学生.docx',PROJECT/'性能指标要求_N31_M50.md',
 ROOT.parent/'repair_20261011/final_actual.cir',
 ROOT.parent/'stage4_rf_oscillator/AM01_2N3904_20261113/scripts/am01_lib.py']
(ROOT/'sources/original_input_hashes.json').write_text(json.dumps(
    [dict(path=str(x),sha256=sha(x)) for x in sources],ensure_ascii=False,indent=2),encoding='utf8')
files=sorted(x for x in ROOT.rglob('*') if x.is_file() and '__pycache__' not in x.parts
             and x.name!='SHA256SUMS.txt')
lines=[sha(x)+'  '+x.relative_to(ROOT).as_posix() for x in files]
(ROOT/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
print('Hashed artifacts:',len(files))
