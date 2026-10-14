"""Extract actual GUI Grapher doubles and use the established S03 measurement method."""
from pathlib import Path
import argparse, hashlib, json, sys
import xml.etree.ElementTree as ET
import numpy as np
import measure_stage3 as established

HERE = Path(__file__).resolve().parent

def sha256(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def read_gra_xml(path, expected_end, selected_page=0):
    traces = {}
    t = None
    audit = {}
    page = -1
    for event, elem in ET.iterparse(path, events=('start','end')):
        if event == 'start':
            if elem.tag == 'CGraphPage': page += 1
            continue
        if elem.tag != 'CTrace':
            continue
        if page != selected_page:
            elem.clear()
            continue
        name = elem.get('Name', '').removeprefix('&ASC')
        data = elem.find('Data')
        if data is None:
            continue
        x = np.frombuffer(bytes.fromhex(data.get('XData')), dtype='<f8')
        y = np.frombuffer(bytes.fromhex(data.get('YData')), dtype='<f8')
        assert name not in traces, f'Duplicate trace: {name}'
        assert len(x) == len(y) and len(x) > 1
        assert np.all(np.isfinite(x)) and np.all(np.isfinite(y))
        assert np.all(np.diff(x) >= 0)
        assert abs(x[-1] - expected_end) < 1e-12, (name, x[-1])
        if t is None:
            t = x
        else:
            assert np.array_equal(t, x), 'Trace grids differ'
        traces[name] = y
        audit[name] = {'points':len(x), 'start_s':float(x[0]), 'end_s':float(x[-1]),
                       'finite':True, 'monotonic':True, 'max_step_s':float(np.diff(x).max())}
        elem.clear()
    names = ['time', 'V(bb_in)', 'V(bbo)', 'V(v1)', 'V(v2)']
    assert set(traces) == set(names[1:]), list(traces)
    return names, np.column_stack([t]+[traces[n] for n in names[1:]]), audit

def main():
    p = argparse.ArgumentParser()
    p.add_argument('xml', type=Path)
    p.add_argument('--gra', type=Path, required=True)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--end', type=float, default=.005)
    p.add_argument('--initial', default='User-defined precharged capacitor IC; not cold startup')
    p.add_argument('--page', type=int, default=0, help='Zero-based Grapher page index')
    args = p.parse_args()
    names, a, audit = read_gra_xml(args.xml, args.end, args.page)
    label = args.gra.stem
    # Reuse the exact earlier cycle, percentile, crossing, and repeatability algorithm.
    established.read_raw = lambda _: (names, a)
    sys.argv = ['measure_stage3.py', str(HERE / (label+'.raw')), '--solver',
                'Multisim 14.3 native GUI; original .gra', '--initial', args.initial]
    established.main()
    path = HERE / (label+'_metrics.json')
    d = json.loads(path.read_text(encoding='utf-8'))
    d.update(solver='Multisim 14.3 native GUI Run; saved/reopened ms14; original .gra',
             initial_condition=args.initial, grapher_page_index=args.page, trace_integrity=audit,
             source_files={str(v):{'sha256':sha256(v),'bytes':v.stat().st_size}
                           for v in [args.gra, args.project]})
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    tail = d['last_five_cycles']; out = d['output_cycles_in_last_300us']
    summary = {'run':label,'points':len(a),'t_end_s':float(a[-1,0]),
        'V1_frequency_hz':float(np.mean([r['frequency_hz'] for r in tail])),
        'V1_duty_percent':float(np.mean([r['input_duty_percent'] for r in tail])),
        'V2_frequency_hz':float(np.mean([r['frequency_hz'] for r in out])),
        'V2_duty_percent':float(np.mean([r['duty_percent'] for r in out])),
        'repeatability_screen':d['repeatability_screen']}
    for n in names[1:]:
        summary[n] = {k:float(np.mean([r[n][k] for r in tail]))
                      for k in ['mean_v','raw_vpp','robust_vpp']}
    (HERE/(label+'_summary.json')).write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__ == '__main__':
    main()
