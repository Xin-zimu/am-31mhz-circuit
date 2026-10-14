"""Measure TMAX=1 ns controls without replacing original failed attempts."""
from pathlib import Path
import json
from analyze_cases import measure

HERE = Path(__file__).resolve().parent
RUN = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')
TARGETS = {'C1': (1,10), 'C3': (4,10), 'C4': (4,50), 'C6': (4,30)}
# Fixed before the controls run: same engineering comparison limits already
# used in S03-03 GUI/engine verification, not official scoring tolerances.
LIMITS = {'frequency_relative': .001, 'robust_vpp_relative': .001,
          'duty_absolute_pp': .1, 'mean_absolute_v': .010}


def main():
    variants = json.loads((HERE/'solver_variants.json').read_text('utf-8'))
    results = []
    for variant in variants:
        status = HERE/(variant['tag']+'_status.json')
        if not status.exists() or json.loads(status.read_text('utf-8-sig'))['status'] != 'COMPLETED':
            continue
        amp,duty = TARGETS[variant['case']]
        spec = dict(variant,target_vpp=amp,target_duty_percent=duty,output_key=variant['case']+'_tmax1ns',actual_tran='tran 2n 5m 4.5m 1n uic')
        path = HERE/(spec['output_key']+'_metrics.json')
        if path.exists():
            result = json.loads(path.read_text('utf-8'))
        else:
            result = measure(spec,RUN/(spec['tag']+'.raw'))
            path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        results.append(result)
        print(json.dumps({'case':result['case'],'vout':result['nodes']['V(v2)']['robust_vpp'],'screen':result['repeatability_screen'],
                          'drift_last':result['drift_windows'][-1]['slope_mV_per_ms']},ensure_ascii=True))
    ref = next((r for r in results if r['case']=='C4'),None)
    comparison = None
    if ref:
        original = json.loads((HERE/'C4_metrics.json').read_text('utf-8'))
        differences = {
            'frequency_relative': ref['output_frequency_hz']/original['output_frequency_hz']-1,
            'robust_vpp_relative': ref['nodes']['V(v2)']['robust_vpp']/original['nodes']['V(v2)']['robust_vpp']-1,
            'duty_absolute_pp': ref['output_duty_percent']-original['output_duty_percent'],
            'mean_absolute_v': ref['nodes']['V(v2)']['mean_v']-original['nodes']['V(v2)']['mean_v']}
        comparison = {'limits':LIMITS,'differences':differences,'passes':all(abs(differences[k])<=v for k,v in LIMITS.items())}
        for r in results:
            r['matched_reference_tag'] = ref['tag']
            r['matched_reference_gain_error_percent'] = 100*(r['robust_gain']/ref['robust_gain']-1)
        print(json.dumps({'reference_control':comparison},ensure_ascii=True))
    (HERE/'solver_control_summary.json').write_text(json.dumps({'results':results,'reference_comparison':comparison},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
