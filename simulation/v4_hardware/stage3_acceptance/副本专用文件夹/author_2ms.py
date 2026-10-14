"""Author the 2 ms probe with byte-exact XML handling (no newline translation)."""
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
work = KEEP/'工作副本'
work.mkdir(parents=True, exist_ok=True)

src = KEEP/'decoded_TMAX1ns.xml'
raw = src.read_bytes()
print('source bytes:', len(raw), 'newlines:', raw.count(b'\n'), 'CR:', raw.count(b'\r'))

needle = b'TSTEP:double{1e-09}\nTSTOP:double{2e-05}'
assert raw.count(needle) == 1, raw.count(needle)
new = raw.replace(needle, b'TSTEP:double{1e-09}\nTSTOP:double{0.002}')
print('after bytes:', len(new), 'delta:', len(new)-len(raw))

out = work/'S03_COLD_ZERO_GEAR500_UIC_TMAX1ns_2ms.xml'
out.write_bytes(new)
import hashlib
print('xml sha256:', hashlib.sha256(new).hexdigest()[:16])
