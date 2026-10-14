"""Find how the saved transient analysis is structured in the decoded project."""
import re
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
t = (KEEP/'decoded_TMAX1ns.xml').read_text(encoding='ascii', errors='replace')
for m in re.finditer(r'(?<![A-Za-z])TSTEP:\w+\{1e-09\}', t):
    a = max(0, m.start()-700)
    print('='*70, 'at', m.start())
    print(t[a:m.start()+500].replace('\n', ' | ')[:1300])
    print()
