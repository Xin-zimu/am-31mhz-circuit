"""Check whether Multisim's 900000-byte chunk boundaries fall on line breaks."""
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
t = (KEEP/'decoded_TMAX1ns.xml').read_bytes()
print('xml bytes:', len(t))
for off in [900000, 1800000, 2700000]:
    if off >= len(t): continue
    seg = t[off-40:off+40]
    print('offset %d:' % off)
    print('   before:', repr(seg[:40]))
    print('   after :', repr(seg[40:]))
    print('   boundary is newline:', t[off-1:off+1] in (b'\n', b'\r\n'))
