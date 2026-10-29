"""Final read-only verification of all registered solver outputs and old evidence."""
from run_gain import *

def main():
    errors=[];rows=[];warnings=[]
    snap=json.loads((HERE/'baseline_snapshot.json').read_text())
    for r in snap['files']:
        if sha(Path(r['path']))!=r['sha256']:errors.append('Historical file changed: '+r['path'])
    for p in sorted((HERE/'results').glob('*.json')):
        r=json.loads(p.read_text())
        if 'raw_path' not in r:continue
        n=r['name'];paths=[(Path(r['raw_path']),'raw_sha256'),(HERE/'netlists'/(n+'.cir'),'net_sha256'),(HERE/'results'/(n+'.log'),'log_sha256')]
        for path,key in paths:
            if sha(path)!=r[key]:errors.append(n+' '+key+' mismatch')
        if 'dependencies' in r:
            for path,key in [(HERE/'netlists'/(n+'_source.cir'),'source_sha256'),(MODEL,'model_sha256')]:
                if sha(path)!=r['dependencies'][key]:errors.append(n+' '+key+' mismatch')
            fp=Path(r['config'].get('front_file') or FILTER)
            if sha(fp)!=r['dependencies']['filter_sha256']:errors.append(n+' filter mismatch')
        log=(HERE/'results'/(n+'.log')).read_text(errors='replace')
        if any(s in log for s in ['stepping failed','singular matrix','aborted','Timestep too small']):warnings.append(n)
        raw=d.readraw(Path(r['raw_path']));err=None
        if 'time' in raw:
            t=raw['time'];c=r['config']
            if t[-1]<c['stop']*1e-6-1e-12:errors.append(n+' incomplete saved window')
            if 'final' in r.get('metrics',{}):
                y=raw['v(final)'];z=2*np.trapezoid(y*np.exp(-2j*np.pi*20000*t),t)/(t[-1]-t[0])
                ref=r['metrics']['final']['peak20'];err=float(abs(z)/ref-1)
                if abs(err)>.002:errors.append(n+' independent Fourier mismatch')
        rows.append(dict(name=n,independent_fourier_relative_error=err))
    completed={r['name'] for r in rows};orphans=[]
    for p in (HERE/'netlists').glob('*.cir'):
        if p.stem.endswith('_source') or p.stem in completed:continue
        files=[p,WORK/(p.stem+'.raw'),WORK/(p.stem+'.log')]
        orphans.append(dict(name=p.stem,files=[dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size) for f in files if f.exists()]))
    out=dict(head_at_start=snap['head'],historical_file_count=len(snap['files']),registered_result_count=len(rows),passed=not errors,errors=errors,numerical_warnings=warnings,checks=rows,unregistered_or_failed=orphans)
    (HERE/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='evidence_manifest.json']
    files += [STAGE/'S05_A2_G22_candidate.cir']
    report=STAGE/'S05_06_A方案基带增益补偿与阻塞复验.md'
    if report.exists():files.append(report)
    external=[Path(json.loads(p.read_text())['raw_path']) for p in (HERE/'results').glob('*.json') if 'raw_path' in json.loads(p.read_text())]
    (HERE/'evidence_manifest.json').write_text(json.dumps(dict(files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in files+external]),indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k!='checks'},indent=2));assert not errors,errors

if __name__=='__main__':main()
