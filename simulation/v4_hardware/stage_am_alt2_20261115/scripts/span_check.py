"""Upper end of the v1 adjustment range on the actual RF-loaded chain.

`range_high_d10` measured the ceiling on the DC-only fixture (4.2488 Vpp).
This run repeats it with the real C4 + LM393 + modulator loading, so the
report can state the true headroom above the 4 Vpp setpoint instead of
quoting the unloaded fixture.
"""
from alt2 import ROOT, run
from edges import assess

if __name__ == '__main__':
    r = run('full_span_max_d10', amp=4, duty=.1, pot=1,
            split=10000, cap=47e-12, full=True)
    assess(r['name'])
    print('v1 ceiling on RF-loaded chain:', r['v1']['vpp'])
