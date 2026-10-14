"""Survey decoded GUI .gra XML traces: point count, end time, first nonzero sample."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np, json

SRC = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')

def survey(name):
    p = SRC / name
    if not p.exists():
        return {'file': name, 'missing': True}
    out = {'file': name, 'bytes': p.stat().st_size, 'traces': {}}
    for trace in ET.parse(p).iter('CTrace'):
        data = trace.find('Data')
        if data is None:
            continue
        label = trace.get('Name').removeprefix('&ASC')
        x = np.frombuffer(bytes.fromhex(data.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(data.get('YData')), dtype='<f8')
        first = int(np.flatnonzero(x > 0)[0]) if np.any(x > 0) else None
        out['traces'][label] = {
            'points': int(len(x)), 'start_s': float(x[0]), 'end_s': float(x[-1]),
            'min_step_s': float(np.min(np.diff(x))) if len(x) > 1 else None,
            'max_step_s': float(np.max(np.diff(x))) if len(x) > 1 else None,
            'first_positive_time_s': float(x[first]) if first is not None else None,
            'first_positive_value_v': float(y[first]) if first is not None else None,
            'last_value_v': float(y[-1])}
    return out

names = ['S03_COLD_ZERO_TRAP500_20us.decoded.xml',
         'S03_COLD_GEAR_page_audit.decoded.xml',
         'S03_COLD_ZERO_GEAR500_REOPEN_20us.decoded.xml',
         'S03_COLD_ZERO_GEAR500_UIC_20us.decoded.xml',
         'S03_COLD_DIAG_20us.decoded.xml']
res = [survey(n) for n in names]
print(json.dumps(res, indent=1, ensure_ascii=False))
(SRC / '副本专用文件夹' / 'step1_gra_survey.json').write_text(json.dumps(res, indent=2), encoding='utf-8')
