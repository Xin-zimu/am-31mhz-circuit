"""Sizing scan for the passive candidate (scheme A) and the TP2 load.

Goal: find the resistor pair that puts the AD835 Y peak at the target while
staying inside the +/-1 V differential range, and find the external load that
makes TP2 itself deliver that amplitude.

Still a Y/Z R/C + current fixture. NOT an AD835 model.
"""
from pathlib import Path
import concurrent.futures as cf, json
import rf_study as L

ROOT = L.ROOT


def interface_pair(rs, rp, iy, iz):
    net = f'RS tp a {rs}\nRP a 0 {rp}\nVY a y 0\nVZ a z 0\n'
    net += ('* INPUT FIXTURE ONLY: not an AD835 macro-model\n'
            'RY y 0 100k\nCY y 0 2p\nRZ z 0 60k\nCZ z 0 2p\n'
            f'IY y 0 {iy}\nIZ z 0 {iz}\n')
    return net


def build(name, rs, rp, iy=10e-6, iz=50e-6):
    import re
    s = L.SRC.read_text(encoding='utf8').split('.control')[0]
    s = re.sub(r'RLOADG out 0 .*\nCLOADG out 0 .*\n', 'VSENSE out tp 0\n', s)
    s += interface_pair(rs, rp, iy, iz) + f'''
.control
set filetype=binary
set num_threads=1
save v(out) v(y) v(z) v(e) v(b) v(bf) v(ef) v(bg) v(eg) v(cg) i(vsup) i(vsense)
tran 0.5n 2.5m 2.45m 0.25n uic
write {name}.raw
quit
.endc
.end
'''
    return s


def job(name, rs, rp, iy=10e-6, iz=50e-6):
    d = L.run(name, build(name, rs, rp, iy, iz))
    return L.measure(name, d, dict(rs=rs, rp=rp, iy=iy, iz=iz))


if __name__ == '__main__':
    # scheme A attenuator sizing: keep Y peak near 0.99 V, the value needed for
    # exactly 2.0/1.2 Vpp under ideal X = 0.105*Vm - 0.42
    pairs = [(330, 620), (390, 680), (390, 620), (430, 680),
             (470, 620), (510, 680), (560, 680)]
    jobs = [(f'SA_{rs}_{rp}', dict(rs=rs, rp=rp)) for rs, rp in pairs]
    # TP2 load fine sweep around the point where TP2 itself reaches ~1.99 Vpp
    for r in (600, 700, 800, 900):
        jobs.append((f'load_{r}_4p', dict(_load=(r, 4e-12))))
    with cf.ThreadPoolExecutor(6) as pool:
        fs = {}
        for name, kw in jobs:
            if '_load' in kw:
                r, c = kw['_load']
                fs[pool.submit(L.job, name, top='load', r=r, c=c)] = name
            else:
                fs[pool.submit(job, name, **kw)] = name
        for f in cf.as_completed(fs):
            f.result()
    print('done')
