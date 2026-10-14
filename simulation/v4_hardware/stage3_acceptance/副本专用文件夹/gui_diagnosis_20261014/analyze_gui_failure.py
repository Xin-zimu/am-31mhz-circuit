"""Read-only diagnosis: where and how the native GUI transient run dies.

No simulator is started. All inputs are existing archived artifacts.
"""
from pathlib import Path
import sys
import json
import xml.etree.ElementTree as ET
import numpy as np

KEEP = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance\副本专用文件夹')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(KEEP))
from mmraw import read_raw  # noqa: E402

TMAX_CAP = 1.0080645161290323e-09   # observed cap when TSTEP=TMAX=2 ns requested


def gui_traces(path):
    root = ET.parse(path).getroot()
    out = {}
    for trace in root.iter('CTrace'):
        data = trace.find('Data')
        if data is None:
            continue
        name = trace.get('Name').removeprefix('&ASC')
        x = np.frombuffer(bytes.fromhex(data.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(data.get('YData')), dtype='<f8')
        out[name] = (x, y)
    return out


def describe(label, t, series):
    dt = np.diff(t)
    print(f'--- {label} ---')
    print(f'  points={len(t)}  end={t[-1]:.9e} s  span={t[-1]*1e9:.6f} ns')
    print(f'  dt min={dt.min():.6e}  max={dt.max():.6e}  median={np.median(dt):.6e}')
    print(f'  dt max / 1ns = {dt.max()/1e-9:.9f}   dt max / 1.0080645161290323ns = {dt.max()/TMAX_CAP:.9f}')
    for thr in (1.0, .5, .1, .01, .001, 1e-6):
        print(f'  dt < {thr:>9g} * 1ns : {int((dt < thr*1e-9).sum()):5d}')
    return dt


def tail(label, t, series, n=22):
    print(f'--- {label}: last {n} accepted steps ---')
    print('   k |        t (s) |       dt (s) |   dt/1ns | '
          + ' | '.join(f'{k:>11s}' for k in series))
    for k in range(len(t) - n, len(t)):
        d = t[k] - t[k-1]
        vals = ' | '.join(f'{series[name][k]:11.6f}' for name in series)
        print(f'{k:4d} | {t[k]:.6e} | {d:.4e} | {d/1e-9:8.5f} | {vals}')


def main():
    report = {}

    gui = gui_traces(OUT.parent / 'gui_evidence_20261014' / 'S03_GUI_COLD_20us_gra.xml')
    order = ['V(v1)', 'V(bb_in)', 'V(bbo)', 'V(v2)']
    gt = gui['V(v1)'][0]
    gser = {name: gui[name][1] for name in order}
    gdt = describe('GUI native transient, TSTEP=TMAX=1 ns, TSTOP=20 us (FAILED)', gt, gser)
    print()
    tail('GUI', gt, gser)
    print()

    # Where is the step smallest, and what does the step profile do near the end?
    kmin = int(np.argmin(gdt)) + 1
    print(f'  smallest step at k={kmin}  t={gt[kmin]:.9e} s  dt={gdt[kmin-1]:.4e} s')
    print(f'  steps in the final 5 ns: {int((gt > gt[-1]-5e-9).sum())}')
    print()

    # slope of each trace near the end (per ns), to spot an event
    print('--- GUI per-step change near the end (|dV| per accepted step) ---')
    for name in order:
        y = gser[name]
        d = np.abs(np.diff(y))
        print(f'  {name:>10s}: max|dV|={d.max():.6e} V at k={int(np.argmax(d))+1} '
              f'(t={gt[int(np.argmax(d))+1]:.6e} s); last-step |dV|={d[-1]:.6e} V')
    print()

    # engine reference on the same netlist, same requested 2 ns cap
    eng_ref = Path(r'D:\ms_xsp\stage3_acceptance\cold_engine_gui_net.raw')
    eng_2n = Path(r'D:\ms_xsp\stage3_acceptance\s0304\M_2n_2n.raw')
    eng_2n_2n = Path(r'D:\ms_xsp\stage3_acceptance\s0304\M_2n_2n.raw')
    for label, path in [('ENGINE source+tran, same netlist, TSTEP=TMAX=2 ns',
                         eng_2n_2n)]:
        if not path.exists():
            print(f'  (missing {path})')
            continue
        names, v = read_raw(path)
        et = v[:, 0]
        edt = np.diff(et)
        print(f'--- {label} ---')
        print(f'  points={len(et)}  end={et[-1]:.9e} s')
        print(f'  dt min={edt.min():.6e}  max={edt.max():.6e}  median={np.median(edt):.6e}')
        print(f'  dt max / 1.0080645161290323ns = {edt.max()/TMAX_CAP:.9f}')
        n_at_cap = int(np.sum(np.isclose(edt, TMAX_CAP, rtol=0, atol=1e-18)))
        print(f'  steps exactly at that cap: {n_at_cap} / {len(edt)}')
        print(f'  steps in the range 200-260 ns: {int(((et > 200e-9) & (et < 260e-9)).sum())}')
        print()

        # GUI vs engine at common accepted times up to the GUI end
        m = et <= gt[-1]
        common = np.intersect1d(np.round(gt, 15), np.round(et[m], 15))
        print(f'  common exact timepoints with the GUI trace: {len(common)}')
        report['engine_points'] = int(len(et))
        report['engine_end_s'] = float(et[-1])
        report['engine_dt_max_s'] = float(edt.max())
        report['engine_steps_200_260ns'] = int(((et > 200e-9) & (et < 260e-9)).sum())

    report['gui_points'] = int(len(gt))
    report['gui_end_s'] = float(gt[-1])
    report['gui_dt_min_s'] = float(gdt.min())
    report['gui_dt_max_s'] = float(gdt.max())
    report['gui_smallest_step_time_s'] = float(gt[kmin])
    (OUT / 'gui_failure_analysis.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
