"""Collect all attempts, check immutable S03 inputs, and draw measured model evidence."""
from pathlib import Path
import json
import shutil
import sys
import numpy as np
from verify_oscillator import OUT, WORK, HERE, sha

# Matplotlib installed in a task-local runtime, without changing the bundled Python.
sys.path.insert(0, 'D:/ms_xsp/s04_plot_runtime')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    # Include failed attempts as first-class records; never fabricate missing waves.
    attempts=[]
    for p in sorted(OUT.glob('*.input.json')):
        name=p.name.removesuffix('.input.json')
        for ext in ('log','status.json'):
            source=WORK/(name+'.'+ext)
            if source.exists(): shutil.copy2(source,OUT/source.name)
        status_path=OUT/(name+'.status.json')
        result_path=OUT/(name+'.result.json')
        status=json.loads(status_path.read_text(encoding='utf-8-sig')) if status_path.exists() else None
        result=json.loads(result_path.read_text()) if result_path.exists() else None
        attempts.append(dict(name=name,input=json.loads(p.read_text()),status=status,
                             measured=result is not None,
                             steady_window_passed=bool(result and result.get('steady_window_screen',{}).get('passed')),
                             raw_exists=(OUT/(name+'.raw')).exists()))
    frozen={HERE.parent/'AM_20k_31MHz_V4_3_REPAIRED.ms14':'99dffd203eb501498e8884ce02005a977b9f295d380ad3c7afea227f26296394',
            HERE.parent/'repair_20261011/final_actual.cir':'d9aba8eff74e679f709bc6a680bf569e6dab87a00303b6ff138f19d4964ccaaf'}
    for path,digest in frozen.items(): assert sha(path)==digest,(path,sha(path))
    manifest=dict(date='2026-10-17',c518062_qualified=False,
        scope='C518062 public parameter check and independent oscillator only',
        frozen_inputs_unchanged={str(p):v for p,v in frozen.items()},
        attempts=attempts,
        source_hashes={p.name:sha(p) for p in [OUT/'C518062_parameters.json',OUT/'domestic_page.html',OUT/'C518062_domestic_attachment.pdf',OUT/'BFR93A_SPICE.prm']},
        tool_hashes={p.name:sha(p) for p in [HERE/'verify_oscillator.py',HERE/'verify_oscillator_ac.py',HERE/'run_s04.ps1']})
    (OUT/'evidence_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.grid':True,'grid.alpha':.18})
    fig,axes=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
    colors={'nominal_500us':'#a54836','lowdrive_500us_tail':'#177a94','lowdrive_1ms_tail':'#177a94'}
    for name,color in colors.items():
        r=json.loads((OUT/(name+'.result.json')).read_text())
        env=r['envelope_5us']
        # Drop the power-on bias transition, which is not an RF envelope.
        env=[e for e in env if e['start_us']>=5]
        label='RE = 1k' if name=='nominal_500us' else ('RE = 4.7k' if name=='lowdrive_500us_tail' else None)
        axes[0].plot([e['start_us']+2.5 for e in env],[e['emit_vpp'] for e in env],color=color,label=label)
    axes[0].set(xlabel='Time after 5 V ramp starts (us)',ylabel='Emitter Vpp (V)',title='Recorded envelope segments')
    axes[0].legend(frameon=False)
    axes[0].text(.43,.75,'Gaps contain no saved data',transform=axes[0].transAxes,fontsize=8,color='#666666')
    r=json.loads((OUT/'lowdrive_1ms_tail.result.json').read_text())
    windows=r['tail_10us_windows']
    axes[1].plot([w['start_us']+5 for w in windows],[w['vpp'] for w in windows],marker='o',color='#177a94')
    axes[1].set(xlabel='Time (us)',ylabel='Emitter Vpp (V)',title='RE = 4.7k: still growing at 1 ms')
    axes[1].text(.05,.90,f"Span = {100*r['steady_window_screen']['vpp_relative_span']:.2f}%  (limit <1%)",transform=axes[1].transAxes)
    d=np.load(OUT/'lowdrive_1ms_tail.plot.npz',allow_pickle=True)
    axes[2].plot(d['t_us']*1000,d['base'],label='Base / crystal terminal',color='#865fb1')
    axes[2].plot(d['t_us']*1000,d['emit'],label='Emitter',color='#177a94')
    axes[2].set(xlabel='Time relative to 1 ms (ns)',ylabel='Voltage (V)',title='Last 250 ns (not steady-state qualified)')
    axes[2].legend(frameon=False,loc='lower left',fontsize=8)
    fig.suptitle('Independent 5 V oscillator | Assumed BVD values | C518062 is NOT qualified',fontsize=13,fontweight='bold')
    fig.savefig(OUT/'oscillator_evidence.png',dpi=180)
    fig.savefig(OUT/'oscillator_evidence.svg')
    print(json.dumps({'attempts':len(attempts),'measured':sum(x['measured'] for x in attempts),'baseline_unchanged':True}))


if __name__=='__main__': main()
