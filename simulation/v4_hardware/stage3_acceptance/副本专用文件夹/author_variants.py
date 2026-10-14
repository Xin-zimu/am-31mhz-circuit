"""Author TMAX/TSTEP variant projects to isolate the step-control mechanism."""
import re, json, hashlib
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
work = KEEP/'工作副本'; work.mkdir(parents=True, exist_ok=True)
src = KEEP/'decoded_GEAR500_UIC_20us.xml'   # failing project, TSTEP=TMAX=2ns, TSTOP=20us
raw = src.read_bytes()
needle = b'TSTEP:double{2e-09}\nTSTOP:double{2e-05}\nTSTART:double{0}\nTMAX:double{2e-09}'
assert raw.count(needle) == 1, raw.count(needle)

VARIANTS = {
 # name: (tstep, tstop, tmax)
 'V_tstep2n_tmax2n': ('2e-09','2e-05','2e-09'),   # known failing reference
 'V_tstep1n_tmax1n': ('1e-09','2e-05','1e-09'),   # known passing
 'V_tstep2n_tmax1n': ('2e-09','2e-05','1e-09'),   # only TMAX changes
 'V_tstep1n_tmax2n': ('1e-09','2e-05','2e-09'),   # only TSTEP changes
 'V_tstep2n_tmax1_5n': ('2e-09','2e-05','1.5e-09'),
 'V_tstep2n_tmax1_05n': ('2e-09','2e-05','1.05e-09'),
}
man = {'source': 'decoded_GEAR500_UIC_20us.xml (TSTEP=TMAX=2ns, TSTOP=20us, IC=uic)',
       'changed': 'only the TSTEP/TSTOP/TMAX quadruple', 'variants': {}}
for name, (ts, tstop, tm) in VARIANTS.items():
    rep = b'TSTEP:double{' + ts.encode() + b'}\nTSTOP:double{' + tstop.encode() + b'}\nTSTART:double{0}\nTMAX:double{' + tm.encode() + b'}'
    new = raw.replace(needle, rep)
    assert new != raw or (ts, tstop, tm) == ('2e-09','2e-05','2e-09')
    x = work/f'{name}.xml'; x.write_bytes(new)
    man['variants'][name] = {'tstep': ts, 'tstop': tstop, 'tmax': tm,
                             'xml_sha256': hashlib.sha256(new).hexdigest()[:16],
                             'bytes': len(new)}
(work/'manifest_variants.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(man['variants'], indent=1))
