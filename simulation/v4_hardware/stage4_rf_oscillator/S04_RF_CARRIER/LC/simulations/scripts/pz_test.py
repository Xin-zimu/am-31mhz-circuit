
# -*- coding: utf-8 -*-
"""S04-LC-02 step 1: does ngspice support .pz (pole-zero)?  That is port-agnostic:
   RHP pole near 31 MHz => the circuit genuinely self-oscillates. No loop breaking needed."""
from pathlib import Path
import subprocess
EXE=Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lc02'); (ROOT/'cir').mkdir(parents=True,exist_ok=True)
WORK=ROOT/'work'; WORK.mkdir(parents=True,exist_ok=True)
MDL=Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage4_rf_oscillator\advance_20261029\2N3904_UNCG.lib').read_text(encoding='ascii').strip()

src=f'''* pz probe: L=1.28uH with Rs, full circuit intact
VSUP vcc 0 5
R1 vcc b 10k
R2 b 0 10k
Q1 vcc b e 2N3904
R3 e 0 4.7k
C1 b e 33p
C2 e 0 33p
CT e 0 0.5p
CBLK b nL 1000p
LR nL n1 0.249
L1 n1 0 1280.07n
C3 vcc 0 100n
C4 vcc 0 10u
{MDL}
.options method=trap maxord=2 reltol=1e-3 trtol=7 temp=27 tnom=27
.control
set filetype=ascii
pz v(nL) vcc 0
echo "=== PZ DONE ==="
quit
.endc
.end
'''
(WORK/'pztest.cir').write_text(src,encoding='ascii')
p=subprocess.run([str(EXE),'-b','-n','-o',str(WORK/'pztest.log'),str(WORK/'pztest.cir')],
                 cwd=WORK,capture_output=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
out=(WORK/'pztest.log').read_text(errors='replace')
print(out[:3000])
