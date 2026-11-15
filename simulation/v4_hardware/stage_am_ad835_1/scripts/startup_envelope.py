"""Re-measure the start-up envelope with a window that is an integer number of
carrier cycles, so the peak-to-peak estimate is not quantised by the window.

The first pass used a fixed 0.25 us window. At 30.99 MHz (32.27 ns period) that
is 7.75 cycles, so each window catches a different fraction of a half-cycle and
the measured Vpp jitters by roughly 1/7.75 = 13 %.  Any "overshoot" smaller than
that jitter is a measurement artefact, not a circuit behaviour.
"""
from pathlib import Path
import json
import numpy as np
import rf_study as L

ROOT = L.ROOT
EXTRA = ROOT / 'results' / 'extra'
EXTRA.mkdir(exist_ok=True)

CYCLES_PER_WINDOW = 200          # long enough that quantisation is < 0.5 %
CASES = [('su_2k_10p', 'original C4 (2k // 10p)'),
         ('su_470_680', 'A470 (470/680)'),
         ('su_C_B', 'C_B (330/1000)')]


def envelope(t, y, period):
    win = CYCLES_PER_WINDOW * period
    idx = ((t - t[0]) / win).astype(np.int64)
    n = idx[-1] + 1
    hi = np.full(n, -np.inf)
    lo = np.full(n, np.inf)
    np.maximum.at(hi, idx, y)
    np.minimum.at(lo, idx, y)
    return t[0] + (np.arange(n) + 0.5) * win, hi - lo, win


def analyse(name, label):
    d = L.read_raw(ROOT / 'results' / f'{name}.raw')
    t, y = d['time'], d['v(out)']
    # carrier period from the last settled window
    m = t > t[-1] - 20e-6
    t1, y1 = t[m], y[m]
    z = np.mean(y1)
    k = np.where((y1[:-1] < z) & (y1[1:] >= z))[0]
    period = float(np.mean(np.diff(t1[k])))
    grid, env, win = envelope(t, y, period)
    final = float(np.median(env[-20:]))
    peak = float(np.max(env))
    # steady-state ripple of the envelope over the last 20 windows
    steady = env[-20:]
    res = dict(name=name, label=label, carrier_period_s=period, envelope_window_s=win,
               cycles_per_window=CYCLES_PER_WINDOW,
               quantisation_bound_pct=100.0 / CYCLES_PER_WINDOW,
               final_envelope_vpp=final, peak_envelope_vpp=peak,
               overshoot_pct=100 * (peak / final - 1),
               steady_state_envelope_spread_pct=100 * (np.max(steady) - np.min(steady)) / final,
               run_seconds=float(t[-1]),
               status='STARTUP_ENVELOPE_CYCLE_ALIGNED_NO_AD835_MODEL')
    (EXTRA / f'{name}_env.json').write_text(json.dumps(res, indent=2), encoding='utf8')
    print(f'{name:12s} T={period*1e9:6.2f}ns win={win*1e6:6.2f}us final={final:7.4f} '
          f'peak={peak:7.4f} overshoot={res["overshoot_pct"]:+6.2f}% '
          f'spread={res["steady_state_envelope_spread_pct"]:5.2f}%')


if __name__ == '__main__':
    for n, lab in CASES:
        if (ROOT / 'results' / f'{n}.raw').exists():
            analyse(n, lab)
