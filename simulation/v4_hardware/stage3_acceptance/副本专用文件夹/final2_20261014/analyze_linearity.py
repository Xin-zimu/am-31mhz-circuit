"""Read-only: 2 Vpp vs 4 Vpp linearity, same method as the accepted S03-03 baseline.

Uses measure_stage3.py's crossing function, 2 ns uniform interpolation,
robust amplitude P98-P2, trapezoid time-weighted mean, last five complete cycles.

No simulator calls.
"""
from pathlib import Path
import sys
import ast
import json
import hashlib
import numpy as np

K = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
S = K.parent
RUN = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(K))
from mmraw import read_raw  # noqa: E402

src = S / 'measure_stage3.py'
syn = ast.parse(src.read_text(encoding='utf-8'))
fn = next(n for n in syn.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(src), 'exec'))

TWO = RUN / 'LIN_2Vpp_tail.raw'
FOUR = RUN / 'REF_4Vpp_tail.raw'
ACCEPTED = S / 'nominal_5ms.npz'          # the accepted S03-03 precharged baseline


def measure(t, cols, names, n_last=5):
    def col(nm):
        return cols[:, names.index(nm)]

    uni = np.arange(t[-1] - 3e-4, t[-1], 2e-9)
    vin = np.interp(uni, t, col('V(v1)'))
    thr = np.mean(np.percentile(vin, [2, 98]))
    up, down = crossings(t, col('V(v1)'), thr)
    rows = []
    for a, b in list(zip(up[:-1], up[1:]))[-n_last:]:
        g = np.arange(a, b, 2e-9)
        falls = down[(down > a) & (down < b)]
        r = {'period_us': (b - a) * 1e6, 'freq_hz': 1 / (b - a),
             'duty_pct': 100 * (falls[0] - a) / (b - a) if len(falls) == 1 else None}
        for nm in ['V(v1)', 'V(bb_in)', 'V(bbo)', 'V(v2)']:
            y = np.interp(g, t, col(nm))
            lo, hi = np.percentile(y, [2, 98])
            r[nm] = {'mean': float(np.trapezoid(y, g) / (g[-1] - g[0])),
                     'vpp': float(hi - lo), 'raw_vpp': float(np.ptp(y))}
        rows.append(r)
    out = {}
    for nm in ['V(v1)', 'V(bb_in)', 'V(bbo)', 'V(v2)']:
        out[nm + '_vpp'] = float(np.mean([r[nm]['vpp'] for r in rows]))
        out[nm + '_mean'] = float(np.mean([r[nm]['mean'] for r in rows]))
    out['freq_hz'] = float(np.mean([r['freq_hz'] for r in rows]))
    out['duty_pct'] = float(np.mean([r['duty_pct'] for r in rows if r['duty_pct']]))
    out['period_us'] = float(np.mean([r['period_us'] for r in rows]))
    out['rows'] = rows
    return out


def load_raw(p):
    n, v = read_raw(p)
    return v[:, 0], v, n


print('=' * 100)
print('INPUTS')
print('=' * 100)
res = {}
for label, path in [('4 Vpp ref (REF_4Vpp_tail)', FOUR), ('2 Vpp (LIN_2Vpp_tail)', TWO)]:
    if not path.exists():
        print(f'  MISSING: {path}')
        continue
    t, v, n = load_raw(path)
    print(f'  {label}')
    print(f'    {path.name}  {path.stat().st_size/1e6:.2f} MB  sha256='
          f'{hashlib.sha256(path.read_bytes()).hexdigest()[:16]}')
    print(f'    points={len(t)}  start={t[0]*1e6:.6f} us  end={t[-1]*1e6:.6f} us')
    print(f'    step median={np.median(np.diff(t))*1e12:.3f} ps  '
          f'max={np.diff(t).max()*1e12:.3f} ps')
    m = measure(t, v, n)
    res[label] = m

print()
print('=' * 100)
print('MEASUREMENT  (last five complete cycles)')
print('=' * 100)
hdr = f'  {"case":26s} {"V2 vpp":>12s} {"V2 mean":>12s} {"freq (Hz)":>12s} {"duty %":>9s} {"Vin vpp":>10s}'
print(hdr)
print('  ' + '-' * (len(hdr) - 2))
for label, m in res.items():
    print(f'  {label:26s} {m["V(v2)_vpp"]:12.6f} {m["V(v2)_mean"]:12.6f} '
          f'{m["freq_hz"]:12.3f} {m["duty_pct"]:9.5f} {m["V(v1)_vpp"]:10.6f}')

print()
print('=' * 100)
print('AGAINST THE ACCEPTED S03-03 BASELINE (from nominal_5ms.npz)')
print('=' * 100)
with np.load(ACCEPTED, allow_pickle=True) as z:
    a = z['data']
    na = z['names'].tolist()
ma = measure(a[:, 0], a, na)
print(f'  {"source":26s} {"V2 vpp":>12s} {"V2 mean":>12s} {"freq (Hz)":>12s} {"duty %":>9s}')
print(f'  {"accepted nominal_5ms":26s} {ma["V(v2)_vpp"]:12.6f} {ma["V(v2)_mean"]:12.6f} '
      f'{ma["freq_hz"]:12.3f} {ma["duty_pct"]:9.5f}')
for label, m in res.items():
    print(f'  {label:26s} {m["V(v2)_vpp"]:12.6f} {m["V(v2)_mean"]:12.6f} '
          f'{m["freq_hz"]:12.3f} {m["duty_pct"]:9.5f}')

print()
print('=' * 100)
print('LINEARITY  (normalised gain, 4 Vpp reference = 1.0000)')
print('=' * 100)
# Input amplitude proxy: V(v1) robust vpp. Output: V(v2) robust vpp.
# Normalised gain = (Vout/Vin) / (Vout/Vin at 4 Vpp)
pairs = []
for label, m in [('accepted 4 Vpp', ma)] + list(res.items()):
    pairs.append((label, m['V(v1)_vpp'], m['V(v2)_vpp']))

base = None
for label, vin, vout in pairs:
    if '4 Vpp' in label and base is None:
        base = vout / vin
print(f'  reference gain taken from: {[l for l, _, _ in pairs if "4 Vpp" in l][0]}')
print()
print(f'  {"case":26s} {"Vin (Vpp)":>11s} {"Vout (Vpp)":>12s} {"gain":>11s} '
      f'{"norm gain":>11s} {"error %":>10s}')
for label, vin, vout in pairs:
    g = vout / vin
    ng = g / base
    print(f'  {label:26s} {vin:11.4f} {vout:12.6f} {g:11.4f} {ng:11.5f} '
          f'{(ng-1)*100:+10.4f}')

print()
print('  NOTE: V(v1) is the circuit input node. Confirm from the netlist that it is')
print('  the true input-amplitude sense point before quoting the gain figure;')
print('  V(v2) is the demodulated output.')

json.dump({k: {kk: vv for kk, vv in v.items() if kk != 'rows'} for k, v in res.items()},
          (OUT / 'lin_results.json').open('w', encoding='utf-8'),
          ensure_ascii=False, indent=2, default=float)
print()
print(f'written: {OUT / "lin_results.json"}')
