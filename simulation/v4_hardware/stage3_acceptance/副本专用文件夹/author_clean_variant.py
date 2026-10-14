"""Cleanest single-source variant: GEAR500UIC with ONLY TSTEP and TMAX set to 1 ns."""
from pathlib import Path
import hashlib, json
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
work = KEEP/'工作副本'
src = KEEP/'decoded_GEAR500_UIC_20us.xml'
raw = src.read_bytes()
old = b'TSTEP:double{2e-09}\nTSTOP:double{2e-05}\nTSTART:double{0}\nTMAX:double{2e-09}'
new = b'TSTEP:double{1e-09}\nTSTOP:double{2e-05}\nTSTART:double{0}\nTMAX:double{1e-09}'
assert raw.count(old) == 1, raw.count(old)
out = raw.replace(old, new)
p = work/'W_1n_1n_from_GEAR500UIC.xml'
p.write_bytes(out)
# byte diff summary
d = [i for i in range(len(raw)) if raw[i] != out[i]] if len(raw) == len(out) else None
print('bytes:', len(raw), '->', len(out), 'delta', len(out)-len(raw))
print('differing positions (same length):', len(d) if d is not None else 'length changed')
info = {'name': 'W_1n_1n_from_GEAR500UIC',
        'source': 'decoded_GEAR500_UIC_20us.xml (the failing project)',
        'change': 'TSTEP 2e-09 -> 1e-09 ; TMAX 2e-09 -> 1e-09 ; nothing else',
        'differing_bytes': len(d) if d is not None else None,
        'sha256': hashlib.sha256(out).hexdigest()[:16]}
(work/'manifest_clean_variant.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(info, ensure_ascii=False, indent=1))
