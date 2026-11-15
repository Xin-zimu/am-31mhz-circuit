"""Post-process the autonomous start-up RAW files (no re-simulation).

The RAW files hold ~12 M samples each, so the envelope is built with a
vectorised bin reduce rather than a Python loop over windows.
"""
from pathlib import Path
import json
import numpy as np
import rf_study as L

ROOT = L.ROOT
EXTRA = ROOT / 'results' / 'extra'
EXTRA.mkdir(exist_ok=True)

CASES = [('su_2k_10p', dict(top='load', r=2000, c=10e-12)),
         ('su_470_680', dict(top='A470')),
         ('su_C_B', dict(top='C_B'))]
GRID = 0.25e-6          # envelope window


def envelope(t, y):
    idx = ((t - t[0]) / GRID).astype(np.int64)
    n = idx[-1] + 1
    hi = np.full(n, -np.inf)
    lo = np.full(n, np.inf)
    np.maximum.at(hi, idx, y)
    np.minimum.at(lo, idx, y)
    return t[0] + (np.arange(n) + 0.5) * GRID, hi - lo


def analyse(name, settings):
    d = L.read_raw(ROOT / 'results' / f'{name}.raw')
    t, y = d['time'], d['v(out)']
    grid, env = envelope(t, y)
    final = float(np.median(env[-40:]))          # last 10 us
    peak = float(np.max(env))
    inside = np.abs(env - final) <= 0.10 * final
    build = None
    # last index from which the envelope stays inside the +/-10 % band
    if inside.any():
        bad = np.where(~inside)[0]
        build = float(grid[bad[-1] + 1]) if len(bad) and bad[-1] + 1 < len(grid) else 0.0
    tail = env[grid >= (build if build is not None else 0)]
    # Supply power: the whole-run mean includes the PWL ramp inrush into C4/C3
    # (uic starts every node at 0 V), so steady state is taken from the last 1 ms.
    tail_mask = t >= t[-1] - 1e-3
    res = dict(name=name, **settings, run_seconds=float(t[-1]), envelope_window_s=GRID,
               final_envelope_vpp=final, peak_envelope_vpp=peak,
               overshoot_ratio=peak / final if final else None,
               build_time_to_10pct_band_s=build,
               converged=bool(build is not None and build < 0.8 * t[-1]),
               envelope_ripple_after_build=max(0.0, float(np.max(tail) - np.min(tail))) if len(tail) else None,
               supply_mw_steady=float(-5000 * L.mean(t[tail_mask], d['i(vsup)'][tail_mask])),
               supply_mw_whole_run_inrush_included=float(-5000 * L.mean(t, d['i(vsup)'])),
               y_peak_v=max(float(np.max(d['v(tp)'])), float(-np.min(d['v(tp)']))),
               status='AUTONOMOUS_STARTUP_C4_PLUS_RC_FIXTURE_NO_AD835_MODEL')
    (EXTRA / f'{name}.json').write_text(json.dumps(res, indent=2), encoding='utf8')
    print(f'{name:14s} final={final:7.4f} peak={peak:7.4f} build={build} '
          f'mW_ss={res["supply_mw_steady"]:.3f}', flush=True)
    return res


if __name__ == '__main__':
    for name, kw in CASES:
        p = ROOT / 'results' / f'{name}.raw'
        if p.exists():
            analyse(name, kw)
        else:
            print('missing', name)
