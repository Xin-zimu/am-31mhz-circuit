from pathlib import Path
import re
HERE=Path(__file__).resolve().parent
t=(HERE/'stage1_layout.cir').read_text().split('.tran')[0]
base=(HERE.parents[1]/'debug/xsp_kit_ascii/net_am.cir').read_text()
base='\n'.join(base.splitlines()[1:])
base=re.sub(r'^VINPUT[^\n]*\n','',base,flags=re.M)
base=base.replace('EBB AMP_IDEAL VREF BB_IN VREF 15','EBB AMP_IDEAL VREF BB_IN VREF 16.3511')
base=base.replace('.end','')
(HERE/'AM_20k_31MHz_V4_Hardware.cir').write_text(t+base+'\n.tran 2n 200u 0 2n\n.end\n',encoding='ascii')
print('Prepared full chain with actual resistor/PWM circuit; comparator templates must be installed after native import.')
