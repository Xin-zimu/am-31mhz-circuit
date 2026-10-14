"""Read-only audits of the GUI failure and the archived 7 ms startup data.

No simulator calls. All outputs remain beside this script. Cycle measurements
follow measure_stage3.py (2 ns uniform interpolation, P98-P2, trapezoid mean).
"""
from pathlib import Path
import hashlib
import json
import re
import ast
import xml.etree.ElementTree as ET
import numpy as np

OUT = Path(__file__).resolve().parent
KEEP = OUT.parent
BASE = KEEP.parent
# Load only the existing crossing function; the reporting module imports a
# plotting dependency which is unnecessary for this numerical audit.
measurement_source = BASE / 'measure_stage3.py'
syntax = ast.parse(measurement_source.read_text(encoding='utf-8'))
function = next(n for n in syntax.body if isinstance(n, ast.FunctionDef) and n.name == 'crossings')
exec(compile(ast.Module(body=[function], type_ignores=[]), str(measurement_source), 'exec'))


def digest(path):
    with path.open('rb') as stream:
        return {'path': str(path), 'bytes': path.stat().st_size,
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def cycle_review(path):
    with np.load(path, allow_pickle=True) as z:
        a = z['data']
        names = z['names'].tolist()
    t = a[:, 0]
    assert np.isfinite(a).all() and (np.diff(t) >= 0).all()
    window = t >= t[-1] - .0003
    uniform = np.arange(t[window][0], t[-1], 2e-9)
    vin = np.interp(uniform, t, a[:, names.index('V(v1)')])
    threshold = np.mean(np.percentile(vin, [2, 98]))
    up, down = crossings(t, a[:, names.index('V(v1)')], threshold)
    rows = []
    for begin, end in list(zip(up[:-1], up[1:]))[-5:]:
        grid = np.arange(begin, end, 2e-9)
        falls = down[(down > begin) & (down < end)]
        row = {'start_s': float(begin), 'end_s': float(end),
               'period_s': float(end - begin), 'frequency_hz': float(1 / (end - begin)),
               'input_falling_crossings': len(falls),
               'input_duty_percent': float(100 * (falls[0] - begin) / (end - begin)) if len(falls) == 1 else None}
        left, right = np.searchsorted(t, begin, side='left'), np.searchsorted(t, end, side='right')
        for name in ['V(v1)', 'V(bb_in)', 'V(bbo)', 'V(v2)']:
            col = a[:, names.index(name)]
            y = np.interp(grid, t, col)
            lo, hi = np.percentile(y, [2, 98])
            # The existing definition integrates the 2 ns resampled grid.
            row[name] = {'mean_v': float(np.trapezoid(y, grid) / (grid[-1] - grid[0])),
                         'robust_vpp': float(hi - lo), 'raw_vpp': float(np.ptp(col[left:right]))}
            # Supplemental exact-endpoint time integral, explicitly separate.
            interior = t[(t > begin) & (t < end)]
            full_t = np.concatenate(([begin], interior, [end]))
            full_y = np.interp(full_t, t, col)
            row[name]['endpoint_integral_mean_v'] = float(np.trapezoid(full_y, full_t) / (end - begin))
        rows.append(row)
    assert len(rows) == 5
    amp = float(np.mean([r['V(v2)']['robust_vpp'] for r in rows]))
    mean_span = float(np.ptp([r['V(v2)']['mean_v'] for r in rows]))
    amp_span = float(np.ptp([r['V(v2)']['robust_vpp'] for r in rows]))
    periods = np.array([r['period_s'] for r in rows])
    period_span = float(np.ptp(periods) / np.mean(periods))
    return {'source': digest(path), 'solver_entry': 'command-line engine source + tran; not native GUI Run',
            'points': len(t), 'end_s': float(t[-1]), 'names': names, 'last_five_cycles': rows,
            'method': 'Existing S03 2 ns uniform interpolation; P98-P2; time integral mean. Exact-endpoint integral is supplemental.',
            'summary': {'V2_robust_vpp': amp, 'V2_mean_v': float(np.mean([r['V(v2)']['mean_v'] for r in rows])),
                        'V2_mean_span_v': mean_span, 'V2_mean_span_fraction_of_amplitude': mean_span / amp,
                        'V2_robust_vpp_span_v': amp_span, 'period_relative_span': period_span,
                        'threshold_fraction': .001,
                        'temporary_repeatability_passes': bool(mean_span / amp < .001 and amp_span / amp < .001 and period_span < .001)}}


def gui_review():
    root = ET.parse(OUT / 'S03_GUI_COLD_20us_gra.xml').getroot()
    pages = []
    for i, page in enumerate(root.iter('CGraphPage')):
        traces = {}
        for trace in page.iter('CTrace'):
            data = trace.find('Data')
            x = np.frombuffer(bytes.fromhex(data.get('XData')), dtype='<f8')
            y = np.frombuffer(bytes.fromhex(data.get('YData')), dtype='<f8')
            assert len(x) == len(y) and np.isfinite(x).all() and np.isfinite(y).all()
            assert (np.diff(x) >= 0).all()
            first = np.flatnonzero(x > 0)[0]
            traces[trace.get('Name')] = {'points': len(x), 'start_s': float(x[0]), 'end_s': float(x[-1]),
                'first_positive_time_s': float(x[first]), 'first_positive_value_v': float(y[first]),
                'last_value_v': float(y[-1])}
        labels = [{k: v for k, v in elem.attrib.items() if k in ['Text', 'Name', 'Title', 'Label']}
                  for elem in page.iter() if any('S03_GUI_COLD_20us' in v for v in elem.attrib.values())]
        pages.append({'index_zero_based': i, 'attributes': page.attrib, 'project_labels': labels, 'traces': traces})
    assert len(pages) == 1 and len(pages[0]['traces']) == 4
    assert pages[0]['project_labels'], 'Missing project label in saved graph'
    assert all(v['end_s'] < 20e-6 for v in pages[0]['traces'].values())
    saved = (OUT / 'S03_GUI_COLD_20us_saved.xml').read_text(encoding='utf-8')
    start = saved.index('ANALYSIS:list{', saved.index('TRAN:list{'))
    section = saved[start:start+4000]
    settings = {key: re.search(r'\b'+key+r':\w+\{([^}]+)\}', section).group(1)
                for key in ['TSTEP', 'TSTOP', 'TSTART', 'TMAX', 'IC']}
    requested = {key: {'enabled': m.group(1) == '1', 'value': m.group(2)}
                 for key in ['itl4', 'method', 'reltol', 'trtol']
                 if (m := re.search(r'IsEnabled:long\{([01])\}\s+'+key+r':\w+\{([^}]+)\}', section))}
    netbytes = (OUT / 'S03_GUI_COLD_20us_actual.cir').read_bytes()
    net = netbytes.decode('utf-16') if netbytes.startswith((b'\xff\xfe', b'\xfe\xff')) else netbytes.decode('utf-8-sig', errors='replace')
    cap_lines = [line.strip() for line in net.splitlines() if re.match(r'^cC(?:111|115|BB)\s', line.strip(), re.I)]
    assert len(cap_lines) == 3, cap_lines
    assert all(float(re.search(r'\bIC\s*=\s*([^\s]+)', line, re.I).group(1)) == 0 for line in cap_lines), cap_lines
    input_files = [OUT/'S03_GUI_COLD_20us_input.ms14', KEEP/'工作副本/W_1n_1n_from_GEAR500UIC.ms14',
                   KEEP/'工作副本/V_tstep1n_tmax1n.ms14', Path('D:/ms_xsp/stage3_acceptance/proj/V_1n_1n.ms14')]
    hashes = [digest(p) for p in input_files]
    assert len({h['sha256'] for h in hashes}) == 1
    return {'date': '2026-10-14', 'request_id': 'ce2adca9-0487-493f-a701-528d635c486c',
        'solver_entry': 'Multisim 14.3 native GUI: Analyses and Simulation > Transient > Run',
        'status': 'FAIL_BEFORE_20US', 'passed': False,
        'error': 'Unable to converge during transient analysis. Consider increasing the ABSTOL, VNTOL, and RELTOL options. Simulation canceled.',
        'settings_saved': settings, 'requested_gui_options': requested, 'effective_solver_options_proven_equal_to_engine': False,
        'initial_conditions': 'User-defined UIC with C111/C115/CBB explicitly zero; ideal supplies, no supply ramp',
        'capacitor_netlist_lines': cap_lines, 'netlist_export_entry': 'Native GUI SPICE netlist viewer Save after run. Separate COM ReportNetlist is only a connectivity report.',
        'pages': pages, 'input_project_matches_com_matrix_byte_for_byte': True, 'input_project_hashes': hashes,
        'artifacts': [digest(OUT/name) for name in ['S03_GUI_COLD_20us.ms14','S03_GUI_COLD_20us.gra','S03_GUI_COLD_20us_actual.cir','saved_project_netlist.txt']],
        'next_steps_gated': ['TSTART short-window comparison not run', '7 ms tail-only native GUI run not run', '2 Vpp/50% linearity not run'],
        'scope': 'No solver-internals investigation; no settings tuning after GUI failure.'}


def main():
    cold = cycle_review(KEEP/'cold_7ms_1ns.npz')
    nominal = cycle_review(BASE/'nominal_5ms.npz')
    write('weighted_7ms_review.json', {'cold': cold, 'precharged_nominal': nominal})
    gui = gui_review()
    write('gui_20us_audit.json', gui)
    refs = []
    for p in sorted((KEEP/'原始只读引用').iterdir()):
        if p.suffix not in ['.ms14', '.cir']:
            continue
        src = BASE/p.name
        source, backup = digest(src), digest(p)
        refs.append({'source': source, 'reference': backup, 'equal': source['sha256'] == backup['sha256']})
    assert len(refs) == 11 and all(r['equal'] for r in refs)
    write('source_hash_verification.json', refs)
    print(json.dumps({'cold': cold['summary'], 'nominal': nominal['summary'], 'gui': gui['pages'],
                      'settings': gui['settings_saved'], 'capacitors': gui['capacitor_netlist_lines'],
                      'eleven_sources_unchanged': True}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
