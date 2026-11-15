"""Where in time does the start-up envelope peak actually occur?

If the maximum sits in the first few microseconds it is the uic power-on
transient, not an oscillator overshoot, and must not be reported as one.
"""
import json
import numpy as np
import rf_study as L

ROOT = L.ROOT
CYCLES = 200
CASES = ['su_2k_10p', 'su_470_680', 'su_C_B']


def profile(name):
    d = L.read_raw(ROOT / 'results' / f'{name}.raw')
    t, y = d['time'], d['v(out)']
    m = t > t[-1] - 20e-6
    t1, y1 = t[m], y[m]
    z = np.mean(y1)
    k = np.where((y1[:-1] < z) & (y1[1:] >= z))[0]
    period = float(np.mean(np.diff(t1[k])))
    win = CYCLES * period
    idx = ((t - t[0]) / win).astype(np.int64)
    n = idx[-1] + 1
    hi = np.full(n, -np.inf); lo = np.full(n, np.inf)
    np.maximum.at(hi, idx, y); np.minimum.at(lo, idx, y)
    grid = t[0] + (np.arange(n) + .5) * win
    env = hi - lo
    final = float(np.median(env[-20:]))
    pk = int(np.argmax(env))
    print(f'\n{name}: final={final:.4f}  peak={env[pk]:.4f} at t={grid[pk]*1e3:.4f} ms '
          f'(window {pk} of {n})')
    print('  first 12 windows: ' + ' '.join(f'{v:.3f}' for v in env[:12]))
    print('  windows 12-30  : ' + ' '.join(f'{v:.3f}' for v in env[12:30]))
    # envelope after the supply has settled (t > 50 us)
    mask = grid > 50e-6
    late_peak = float(np.max(env[mask]))
    print(f'  peak after t>50us = {late_peak:.4f}  -> real overshoot '
          f'{100*(late_peak/final-1):+.2f} %')
    # when does it first reach within 2 % of final and stay there
    inside = np.abs(env - final) <= 0.02 * final
    settled = None
    for i in range(len(inside)):
        if inside[i:].all():
            settled = grid[i]; break
    print(f'  settles to 2% band at {settled*1e3:.3f} ms')
    return dict(name=name, final=final, peak=float(env[pk]), peak_time_s=float(grid[pk]),
                peak_after_50us=late_peak,
                overshoot_after_50us_pct=100*(late_peak/final-1),
                settles_2pct_s=settled, carrier_period_s=period)


if __name__ == '__main__':
    out = [profile(n) for n in CASES]
    (ROOT / 'results' / 'extra' / 'startup_timing.json').write_text(
        json.dumps(out, indent=2), encoding='utf8')
