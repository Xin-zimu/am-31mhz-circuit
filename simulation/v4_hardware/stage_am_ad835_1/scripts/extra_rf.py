"""Stage AM-AD835.1 extra carrier-interface runs (no AD835 model exists).

Adds what the first pass did not cover:
  * a denser TP2 external-load sweep written to CSV,
  * autonomous start-up runs (oscillation build-up, not just steady state),
  * a deliberate DC-floating case for the existing COUTG = 10 nF,
  * scheme B with a real 0.6x Z tap on the AD835 side of the buffer.

Every Y/Z "load" is still an R/C + signed-current fixture, never a device model.
"""
from pathlib import Path
import concurrent.futures as cf, csv, json, re, subprocess
import numpy as np
import rf_study as L

ROOT = L.ROOT
EXTRA = ROOT / 'results' / 'extra'
EXTRA.mkdir(exist_ok=True)

# --------------------------------------------------------------------------- #
# start-up: run from t = 0 and watch the envelope build
# --------------------------------------------------------------------------- #
def startup_run(name, top, iy=10e-6, iz=50e-6, r=2000, c=10e-12, stop=5.0, step=0.5):
    s = L.SRC.read_text(encoding='utf8').split('.control')[0]
    s = re.sub(r'RLOADG out 0 .*\nCLOADG out 0 .*\n', 'VSENSE out tp 0\n', s)
    net, _ = L.interface(top, iy, iz, r, c)
    net = re.sub(r'\bout\b', 'tp', net)
    s += net + f'''
.control
set filetype=binary
set num_threads=1
save v(out) v(tp) v(e) i(vsup) i(vsense)
tran {step}n {stop}m 0 {step}n uic
write {name}.raw
quit
.endc
.end
'''
    return L.run(name, s)

def startup_measure(name, d, settings):
    t = d['time']; y = d['v(out)']
    # 0.25 us envelope grid over the whole run
    dt = 0.25e-6
    grid = np.arange(t[0], t[-1], dt)
    env = np.array([np.ptp(y[(t >= a) & (t < a + dt)]) if np.any((t >= a) & (t < a + dt)) else np.nan
                    for a in grid])
    ok = ~np.isnan(env)
    grid, env = grid[ok], env[ok]
    final = float(np.median(env[-40:]))            # last 10 us of envelope
    # first time the envelope stays inside +/-10 % of the final value
    inside = np.abs(env - final) <= 0.10 * final
    t_build = None
    for k in range(len(inside)):
        if inside[k:].all():
            t_build = float(grid[k]); break
    peak = float(np.nanmax(env))
    res = dict(name=name, **settings, run_seconds=float(t[-1]),
               envelope_grid_s=dt, final_envelope_vpp=final,
               peak_envelope_vpp=peak, overshoot_ratio=peak / final if final else None,
               build_time_to_10pct_band_s=t_build,
               monotonic_after_build=bool(np.all(np.diff(env[grid >= (t_build or 0)]) <=
                                                 0.02 * max(final, 1e-12))),
               converged=bool(t_build is not None and t_build < 0.8 * t[-1]),
               supply_mw=float(-5000 * L.mean(t, d['i(vsup)'])),
               status='AUTONOMOUS_STARTUP_C4_PLUS_RC_FIXTURE_NO_AD835_MODEL')
    path = EXTRA / f'{name}.json'
    path.write_text(json.dumps(res, indent=2), encoding='utf8')
    print(f"{name:22s} final={final:.4f} peak={peak:.4f} t90={t_build} mW={res['supply_mw']:.3f}", flush=True)
    return res

def startup_job(name, top, **kw):
    d = startup_run(name, top, **kw)
    return startup_measure(name, d, dict(top=top, **kw))

# --------------------------------------------------------------------------- #
if __name__ == '__main__':
    # (function, name, kwargs)
    jobs = []
    # 1. denser external-load sweep (first pass already covered 1k/2k/10k/37.5k)
    for name, r, c in (('load_500_4p', 500, 4e-12), ('load_3k3_4p', 3300, 4e-12),
                       ('load_50k_4p', 50000, 4e-12), ('load_100k_4p', 100000, 4e-12)):
        jobs.append((L.job, name, dict(top='load', r=r, c=c)))
    # 2. DC-floating demonstration of the existing COUTG = 10 nF
    jobs.append((L.job, 'float_10n', dict(top='CAP_ONLY', iy=10e-6, iz=50e-6, stop=5, start=4.5))) 
    jobs.append((L.job, 'float_10n_1k', dict(top='CAP_1K', iy=10e-6, iz=50e-6, stop=5, start=4.5)))
    # 3. scheme B with a real 0.6x Z tap after the buffer (Y = Vc, Z = 0.6 Vc)
    jobs.append((L.job, 'B_Z06_nom', dict(top='B_Z06', iy=10e-6, iz=50e-6)))
    jobs.append((L.job, 'B_Z06_stress_pp', dict(top='B_Z06', iy=27e-6, iz=100e-6)))
    jobs.append((L.job, 'B_Z06_stress_nn', dict(top='B_Z06', iy=-27e-6, iz=-100e-6)))
    # 4. autonomous start-up from t = 0
    jobs.append((startup_job, 'su_2k_10p', dict(top='load', r=2000, c=10e-12)))
    jobs.append((startup_job, 'su_470_680', dict(top='A470')))
    jobs.append((startup_job, 'su_C_B', dict(top='C_B')))
    with cf.ThreadPoolExecutor(8) as pool:
        fs = [pool.submit(fn, name, **kw) for fn, name, kw in jobs]
        for f in cf.as_completed(fs):
            f.result()
    print('done')
