"""Generate comparisons from completed cross-solver runs without changing evidence."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from crosscheck_oscillator import OUT, WORK, SOURCE, EXE, read_ngraw


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((OUT/(name+'.result.json')).read_text())


def difference(a,b):
    # Relative change from a to b; unlike a device error, the denominator is a's result.
    return {'frequency_delta_hz':b['frequency_hz']-a['frequency_hz'],
            'frequency_delta_ppm':(b['frequency_hz']/a['frequency_hz']-1)*1e6,
            'vpp_change_percent':(b['output_vpp']/a['output_vpp']-1)*100,
            'crystal_power_change_percent':(b['crystal_motional_power_w']/a['crystal_motional_power_w']-1)*100,
            'rail_power_change_percent':(b['mean_5v_rail_power_w']/a['mean_5v_rail_power_w']-1)*100}


def main():
    results={}
    for path in sorted(OUT.glob('ng_*.result.json')):
        r=json.loads(path.read_text()); name=r['name']
        p=json.loads((OUT/(name+'.input.json')).read_text())
        for ext,digest in r['sha256'].items():
            assert sha(OUT/(name+'.'+ext))==digest,(name,ext)
        assert r['c518062_qualified'] is False
        # The complete DUT prefix must remain exactly the archived circuit.
        dut=SOURCE.read_text(encoding='ascii').rsplit('.end',1)[0]
        assert (OUT/(name+'.cir')).read_text(encoding='ascii').split('.options',1)[0]==dut
        results[name]={'result':r,'input':p,'status':json.loads((OUT/(name+'.status.json')).read_text())}
    original=json.loads(SOURCE.with_suffix('.result.json').read_text())
    cross=difference(original,results['ng_1ms_025ns']['result'])
    sweep=sorted([v for v in results.values() if v['input']['stop_us']==2000],key=lambda x:-x['input']['step_ns'])
    pairs=[]
    for a,b in zip(sweep,sweep[1:]):
        d=difference(a['result'],b['result'])
        pairs.append({'from':a['result']['name'],'to':b['result']['name'],**d,
            'numerical_screen_passed':abs(d['frequency_delta_ppm'])<10 and abs(d['vpp_change_percent'])<1 and abs(d['crystal_power_change_percent'])<1})
    duration=None
    if 'ng_2ms_003125ns' in results and 'ng_3ms_003125ns' in results:
        duration=difference(results['ng_2ms_003125ns']['result'],results['ng_3ms_003125ns']['result'])
    summary={'date':'2026-10-17','c518062_qualified':False,'crystal_parameters_still_assumed':True,
        'no_component_or_model_parameter_changes':True,'cross_solver_1ms':cross,
        'step_comparisons':pairs,'duration_2ms_to_3ms':duration,
        'cases':{name:{'step_ns':v['input']['step_ns'],'stop_us':v['input']['stop_us'],
            **{key:v['result'][key] for key in ('output_vpp','output_dc_v','frequency_hz','crystal_motional_power_w','mean_5v_rail_power_w','steady_window_screen')}} for name,v in results.items()}}
    (OUT/'comparison.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    runtime={'name':'ngspice-47 64-bit console','source':'https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/',
        'archive_url':'https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/47/ngspice-47_64.7z',
        'archive_sha256':sha(WORK/'ngspice47_verified.7z'),
        'published_archive_sha256':'59225971bd68cdd1199443649aa4615a9e6d684933f205ab49006a3942518f5a',
        'executable_path':str(EXE),'executable_sha256':sha(EXE),
        'actual_solver':'SPARSE 1.3 (from run log), not KLU despite KLU support in this build',
        'options':'trap, maxord=2, reltol=1e-3, trtol=7, TEMP=TNOM=27 C; num_threads=1; -n; binary raw',
        'install_scope':'portable task-local directory; no system PATH or user init-file changes'}
    assert runtime['archive_sha256']==runtime['published_archive_sha256']
    (OUT/'runtime_provenance.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
    files=[p for p in OUT.iterdir() if p.is_file() and p.name not in ('evidence_manifest.json',) and p.suffix not in ('.png','.svg','.npz')]
    manifest={'date':'2026-10-17','files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files},
        'scripts':{p.name:sha(p) for p in [Path(__file__),Path(__file__).with_name('crosscheck_oscillator.py'),Path(__file__).with_name('verify_oscillator.py')]}}
    (OUT/'evidence_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(results),'cross_solver':cross,'step_comparisons':pairs,'duration':duration},indent=2))
    sys.path.insert(0,'D:/ms_xsp/s04_plot_runtime')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.grid':True,'grid.alpha':.2})
    fig,axes=plt.subplots(1,3,figsize=(13.5,4.5),layout='constrained')
    for name,label in [('ng_1ms_025ns','0.9-1.0 ms'),('ng_2ms_025ns','1.9-2.0 ms')]:
        r=results[name]['result']; rows=r['tail_10us_windows']
        axes[0].plot(np.arange(10)*10+5,[row['vpp'] for row in rows],marker='o',label=label)
    axes[0].set(xlabel='Position within last 100 us',ylabel='Output Vpp (V)',title='Longer simulation reaches a plateau')
    axes[0].legend(frameon=False)
    dt=np.array([r['input']['step_ns'] for r in sweep]); fs=np.array([r['result']['frequency_hz'] for r in sweep])
    axes[1].plot(dt,(fs-31e6)/31e6*1e6,marker='o',color='#8c529c')
    axes[1].set(xlabel='Maximum timestep (ns)',ylabel='Offset from 31 MHz (ppm)',title='Frequency is sensitive to timestep')
    chosen='ng_3ms_003125ns' if 'ng_3ms_003125ns' in results else sweep[-1]['result']['name']
    data=np.load(OUT/(chosen+'.plot.npz'),allow_pickle=True)
    axes[2].plot(data['t_us']*1000,data['emit'],color='#197f96')
    axes[2].set(xlabel='Time relative to end (ns)',ylabel='Emitter voltage (V)',title=chosen.replace('ng_','').replace('_',' / '))
    fig.suptitle('Unchanged 5 V oscillator | ngspice cross-check | Crystal parameters remain assumptions',fontsize=13,fontweight='bold')
    fig.savefig(OUT/'crosscheck_evidence.png',dpi=170)
    fig.savefig(OUT/'crosscheck_evidence.svg')


if __name__=='__main__': main()
