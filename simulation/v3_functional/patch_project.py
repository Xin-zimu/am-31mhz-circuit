"""Change only pulse parameters, baseband gain and transient window in a copy."""
from pathlib import Path
import re, sys, json, hashlib

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent/'system/AM_22k_D50_A4V_debug.ms14'
TEXT = Path('D:/ewbwork/v3_source.xml').read_bytes().decode('ascii')

def replace_once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)

def component(text, local_name, pairs):
    pattern = rf'<CiComponent Class="CiComponent" LocalName="&amp;ASC{local_name}".*?</CiComponent>'
    found = list(re.finditer(pattern, text, re.S))
    assert len(found) == 1
    m = found[0]
    part = m.group()
    for old, new in pairs:
        part = replace_once(part, old, new)
    return text[:m.start()] + part + text[m.end():]

def make(amp, gain, duty=50):
    name = f'AM_20k_D{duty:02d}_A{amp}V_V3'
    pw = duty*0.5  # us; 20 ns edges add 0.04 percentage point at half-height.
    text = component(TEXT, 'V6', [
        ('<Item Value="2.27072727273e-05"/>', f'<Item Value="{pw*1e-6:.12g}"/>'),
        ('<Item Value="4.54545454545e-05"/>', '<Item Value="5e-05"/>'),
        ('<Item Value="&amp;ASC22.7073u"/>', f'<Item Value="&amp;ASC{pw:g}u"/>'),
        ('<Item Value="&amp;ASC45.4545u"/>', '<Item Value="&amp;ASC50u"/>'),
        ('<Item Value="4"/>', f'<Item Value="{amp}"/>'),
        ('<Item Value="&amp;ASC4"/>', f'<Item Value="&amp;ASC{amp}"/>')])
    text = component(text, 'V1', [
        ('<Item Value="15"/>', f'<Item Value="{gain:.9g}"/>'),
        ('<Item Value="&amp;ASC15"/>', f'<Item Value="&amp;ASC{gain:.9g}"/>')])
    # Restore the engineering model from the original .cir; this is NOT a BAT85S vendor model.
    model = 'D(Is=20n N=1.06 Rs=2 Cjo=2p M=0.33 Vj=0.35 Bv=70 Ibv=10u)'
    text = replace_once(text, '.model DIODE__DIODES_VIRTUAL__1  D"',
                        '.model DIODE__DIODES_VIRTUAL__1  '+model+'"')
    text = replace_once(text, '.model DIODE  D"', '.model DIODE  '+model+'"')
    # Keep TSTART=0: retaining from a nonzero start is abnormally slow in this engine.
    text = replace_once(text, 'TSTOP:double{0.0002}\nTSTART:double{0}',
                        'TSTOP:double{0.005}\nTSTART:double{0}')
    text = replace_once(text, 'MAX_POINTS:long{2000000}', 'MAX_POINTS:long{8000000}')
    text = text.replace('AM_22k_D50_A4V_debug', name)
    out = HERE/(name+'.xml')
    out.write_bytes(text.encode('ascii'))
    return out

if __name__ == '__main__':
    gain = float(sys.argv[1])
    for amp in [1,2,3,4]:
        print(make(amp, gain))
    print(make(4, gain,10))
    (HERE/'source_sha256.txt').write_text(hashlib.sha256(SOURCE.read_bytes()).hexdigest()+'\n',encoding='ascii')
