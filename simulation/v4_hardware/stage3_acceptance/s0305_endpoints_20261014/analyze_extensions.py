"""Keep longer settling checks separate from the common 5 ms comparison."""
import json
from pathlib import Path
from analyze_cases import measure, digest

HERE = Path(__file__).resolve().parent
RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')


def main():
    specs = json.loads((HERE/'extension_manifest.json').read_text('utf-8'))
    results = []
    for spec in specs:
        state_path = HERE/(spec['tag']+'_status.json')
        if not state_path.exists() or json.loads(state_path.read_text('utf-8-sig'))['status'] != 'COMPLETED':
            continue
        path = HERE/(spec['output_key']+'_metrics.json')
        if path.exists():
            result = json.loads(path.read_text('utf-8'))
        else:
            result = measure(spec, RUNTIME/(spec['tag']+'.raw'))
            path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        earlier = json.loads((HERE/(spec['case']+'_metrics.json')).read_text('utf-8'))
        result['comparison_to_5ms'] = {
            'robust_vpp_change_percent': 100*(result['nodes']['V(v2)']['robust_vpp']/earlier['nodes']['V(v2)']['robust_vpp']-1),
            'mean_change_mV': 1000*(result['nodes']['V(v2)']['mean_v']-earlier['nodes']['V(v2)']['mean_v']),
            'earlier_drift_mV_per_ms': earlier['drift_windows'][-1]['slope_mV_per_ms'],
            'later_drift_mV_per_ms': result['drift_windows'][-1]['slope_mV_per_ms'],
            'earlier_mean_span_percent': earlier['repeatability_screen']['mean_span_percent'],
            'same_netlist_sha256': digest(HERE/(spec['tag']+'.cir')) == digest(HERE/(earlier['tag']+'.cir'))}
        assert result['comparison_to_5ms']['same_netlist_sha256']
        results.append(result)
        print(json.dumps({'case':result['case'],'stop_s':spec['stop_s'],'screen':result['repeatability_screen'],
                          'comparison_to_5ms':result['comparison_to_5ms']},ensure_ascii=True))
    (HERE/'extensions_summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
