from pathlib import Path
import xml.etree.ElementTree as ET
import re, hashlib, json
HERE=Path(__file__).resolve().parent
records=[]
for path in HERE.glob('AM_*.verified.xml'):
    if 'quick200us' in path.name:continue
    text=path.read_text(encoding='ascii')
    root=ET.fromstring(text)
    parts={c.get('LocalName'):c for c in root.iter('CiComponent')}
    def params(name):
        return [float(e.get('Value')) for e in parts['&ASC'+name].find('.//CiaParamList/doubles')]
    p=params('V6'); gain=params('V1')[1]
    amp=int(re.search(r'_A(\d)V',path.name)[1]); duty=int(re.search(r'_D(\d+)',path.name)[1])
    assert p[3]==amp and abs(p[11]-duty*.5e-6)<1e-15 and p[13]==50e-6
    assert gain==16.3511 and params('V5')[5]==31e6
    models=[e.get('String') for e in root.iter('CiaCString') if '.model DIODE__' in e.get('String','')]
    assert len(models)==1 and 'Is=20n N=1.06 Rs=2 Cjo=2p' in models[0]
    assert 'TSTOP:double{0.005}\nTSTART:double{0}\nTMAX:double{2e-09}' in text
    i=text.index('ANALYSIS_ID:long{3}')
    assert 'MAX_POINTS:long{8000000}' in text[i:i+200]
    assert 'method:string{trapezoidal}' in text
    records.append({'file':path.name.replace('.verified.xml','.ms14'),'amplitude':amp,'nominal_duty':duty,'period_s':p[13],'gain':gain,'model':models[0]})
assert len(records)==5
source=HERE.parent/'system/AM_22k_D50_A4V_debug.ms14'
assert hashlib.sha256(source.read_bytes()).hexdigest()==(HERE/'source_sha256.txt').read_text().strip()
(HERE/'native_verification.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('PASS: all five Multisim-resaved projects retain pulse, gain, diode model and transient settings; source unchanged.')
