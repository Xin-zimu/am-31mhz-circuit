"""Read-only solver evidence audit; never starts a simulation or rewrites history."""
from run_diagnosis import *
import re

def main():
    records=[];errors=[];warnings=[];results=list((HERE/'results').glob('*.json'))
    for p in results:
        r=json.loads(p.read_text());n=r['name'];src=HERE/'netlists'/(n+'.cir');raw=Path(r['raw_path']);log=HERE/'results'/(n+'.log')
        for path,key in [(src,'net_sha256'),(raw,'raw_sha256'),(log,'log_sha256')]:
            ok=path.exists() and sha(path)==r[key]
            if not ok:errors.append(str(path)+' hash mismatch')
            records.append(dict(path=str(path),sha256=sha(path) if path.exists() else None,ok=ok))
        if r['simulator_sha256']!=sha(EXE):errors.append(n+' simulator changed')
        if 'dependencies' in r:
            for path,key in [(HERE/'netlists'/(n+'_source.cir'),'source_sha256'),(HERE/'sources/OPAx197.LIB','model_sha256')]:
                if sha(path)!=r['dependencies'][key]:errors.append(n+' dependency changed')
        logtext=log.read_text(errors='replace')
        if any(s in logtext for s in ['singular matrix','stepping failed','aborted']):warnings.append(n)
        if 'nodes' in r['metrics']:
            d=readraw(raw);t=d['time'];c=r['config'];a=c['start']*1e-6;b=c['stop']*1e-6
            if t[-1]<b-1e-12 or t[0]>a+1e-9:errors.append(n+' incomplete analysis window')
            # Independent time-weighted Fourier integration of raw adaptive samples.
            # Includes only saved endpoints; difference from uniform interpolation
            # is expected to be tiny at 20kHz, not exactly bit-identical.
            y=d['v(out)'];z=2*np.trapezoid(y*np.exp(-2j*np.pi*20e3*t),t)/(t[-1]-t[0])
            ref=r['metrics']['nodes']['out']['spectral_peak']['20000']
            error=abs(abs(z)/ref-1)
            if error>.001:errors.append(n+f' independent 20k Fourier error {error:.4g}')
    snap=json.loads((HERE/'baseline_snapshot.json').read_text(encoding='utf-8'));root=PARENT.parents[2]
    # Management entry points are deliberately updated; historical evidence stays fixed.
    for r in snap['files'][3:]:
        p=root/r['path']
        if sha(p)!=r['sha256']:errors.append(r['path']+' historical evidence changed')
    historic=[]
    for name in ['B_clean','B_near_29M_6m','B_near_33M_6m','B_output_square10','B_output_square50']:
        rp=PARENT/'selectivity_20261029/results'/(name+'.json');r=json.loads(rp.read_text())
        raw=Path(r['raw_path']);net=PARENT/'selectivity_20261029/netlists'/(name+'.cir')
        ok=sha(raw)==r['raw_sha256'] and sha(net)==r['net_sha256']
        if not ok:errors.append('historical '+name+' hash mismatch')
        historic.append(dict(name=name,ok=ok))
    completed={p.stem for p in results}
    abandoned=[]
    for p in (HERE/'netlists').glob('*.cir'):
        if p.stem in completed or p.stem.endswith('_source'):continue
        files=[p,WORK/p.name,WORK/(p.stem+'.log'),WORK/(p.stem+'.raw')]
        abandoned.append(dict(case=p.stem,files=[dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size) for f in files if f.exists()]))
    report=dict(date='2026-10-30',result_count=len(results),all_hashes_and_independent_fourier_pass=not errors,
        errors=errors,numerical_warning_cases=warnings,historical_baselines=historic,
        failed_or_interrupted_cases=abandoned,
        note='Warnings and failed cases are retained, not silently accepted. A floating-port runs and G22 fallback-initialized runs are excluded from steady/prebiased conclusions.')
    (HERE/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # Bind small artifacts too; manifest/audit themselves excluded to avoid recursion.
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or path.name in ['evidence_manifest.json','audit.json'] or '__pycache__' in path.parts or path.suffix in ['.raw','.npz']:continue
        records.append(dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size))
    (HERE/'evidence_manifest.json').write_text(json.dumps(dict(files=records,report_sha256=sha(PARENT/'S05_05_R2邻近阻塞诊断与AB决策.md')),indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    assert not errors,errors

if __name__=='__main__':main()
