"""Verify each project variant differs from its source only in the TSTEP/TSTOP/TSTART/TMAX quadruple."""
from pathlib import Path
KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
work = KEEP/'工作副本'

pairs = [
    ('TMAX1ns source vs V_1n_1n', KEEP/'decoded_TMAX1ns.xml', work/'V_tstep1n_tmax1n.xml'),
    ('GEAR500UIC source vs V_2n_2n', KEEP/'decoded_GEAR500_UIC_20us.xml', work/'V_tstep2n_tmax2n.xml'),
    ('GEAR500UIC source vs V_2n_1n', KEEP/'decoded_GEAR500_UIC_20us.xml', work/'V_tstep2n_tmax1n.xml'),
]
for label, a, b in pairs:
    x = a.read_bytes(); y = b.read_bytes()
    print('=' * 70)
    print(label)
    print('  bytes: %d vs %d  (delta %d)' % (len(x), len(y), len(y)-len(x)))
    if len(x) == len(y):
        diff = [i for i in range(len(x)) if x[i] != y[i]]
        print('  differing byte positions:', len(diff))
        if diff:
            lo, hi = diff[0], diff[-1]
            print('  span: %d..%d' % (lo, hi))
            print('  before:', repr(x[max(0,lo-90):lo+60]))
            print('  after :', repr(y[max(0,lo-90):lo+60]))
    else:
        # find first divergence
        n = min(len(x), len(y))
        i = next((k for k in range(n) if x[k] != y[k]), n)
        print('  first divergence at byte', i)
        print('  before:', repr(x[max(0,i-90):i+60]))
        print('  after :', repr(y[max(0,i-90):i+60]))
