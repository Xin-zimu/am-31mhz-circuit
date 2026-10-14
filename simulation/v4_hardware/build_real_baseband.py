from pathlib import Path
import re,sys
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent))
from build_simulation import run_spice,read_raw
MODEL=(H/'models/OPA197_TI/OPAx197.LIB').read_text()
BB='''* OPA197 non-inverting baseband amplifier, +9 V / 0 V supply.
* 10k gain resistor, 150k + 3.511k trim feedback = gain 16.3511.
XUBB BB_IN BB_FB VCC 0 AMP_IDEAL OPAx197
RG_BB BB_FB VREF 10k
RF_BB AMP_IDEAL FB_TRIM 150k
RV_BB FB_TRIM BB_FB 3.511k
CBB_DECOUPLE VCC 0 100n
'''
if __name__=='__main__':
    t=(H/'AM_20k_31MHz_V4_Hardware.cir').read_text()
    assert 'EBB AMP_IDEAL VREF BB_IN VREF' in t
    t=re.sub(r'^EBB .*$',BB,t,flags=re.M)
    t=re.sub(r'^\.save .*$', '',t,flags=re.M)
    t=re.sub(r'^\.tran .*$', '.save V(V1) V(TP3) V(TP6) V(BB_IN) V(AMP_IDEAL) V(V2)\n.options method=gear plotwinsize=0\n.tran 2n 200u 0 2n uic',t,flags=re.M)
    t=t.replace('.end',MODEL+'\n.end') if '.end' in t else t+'\n'+MODEL+'\n.end\n'
    p=H/'AM_20k_31MHz_V4_1_OPA197.cir';p.write_text(t,encoding='ascii')
    print(p,flush=True);run_spice(p);print(p.with_suffix('.log').read_text(errors='replace')[-1800:])
