"""Read-only S05-05 audit; results are written only into S05-06."""
from run_gain import *

def main():
    init()
    root=STAGE.parents[2]
    paths=[STAGE/'S05_R2_candidate.cir',STAGE/'S05_05_R2邻近阻塞诊断与AB决策.md']
    paths+=list(p for p in PREV.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    snap=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),files=[dict(path=str(p),sha256=sha(p)) for p in paths])
    fixed(HERE/'baseline_snapshot.json',json.dumps(snap,indent=2).encode())
    for p in [root/'README.md',root/'项目管理/02_当前阶段目标.md',root/'项目管理/03_当前实现状态.md']:
        fixed(HERE/'records_before'/p.name,p.read_bytes())
    names=['R2_clean','R2_29_3','R2_29_4','R2_33_3','R2_33_4',
           'A2M_r1M_clean','A2M_r1M_29_40','A2M_r1M_29_50','A2M_r1M_29_60',
           'A2M_r1M_33_40','A2M_r1M_33_50','A2M_r1M_33_60',
           'A2M_r1M_clean_h025','A2M_r1M_29_50_h025']
    rows=[]
    for n in names:
        r=json.loads((PREV/'results'/(n+'.json')).read_text())
        paths=[(PREV/'netlists'/(n+'.cir'),'net_sha256'),(PREV/'results'/(n+'.log'),'log_sha256'),(Path(r['raw_path']),'raw_sha256')]
        ok=all(sha(p)==r[k] for p,k in paths)
        raw=d.readraw(Path(r['raw_path']));t=raw['time'];y=raw['v(out)']
        z=2*np.trapezoid(y*np.exp(-2j*np.pi*20000*t),t)/(t[-1]-t[0])
        ref=r['metrics']['nodes']['out']['spectral_peak']['20000']
        rows.append(dict(name=n,hash_pass=ok,peak20=float(abs(z)),reported_peak20=ref,relative_error=float(abs(z)/ref-1),config=r['config']))
    lookup={r['name']:r for r in rows}
    for r in rows:
        n=r['name'];base='R2_clean' if n.startswith('R2') else 'A2M_r1M_clean'+('_h025' if n.endswith('_h025') else '')
        r['delta_db']=float(20*np.log10(r['peak20']/lookup[base]['peak20']))
    result=dict(definition='20log10(20 kHz Fourier amplitude blocked / same candidate clean); sine AM m=.5 Ac=10mV source peak, Rs=50ohm; not Vpp and not square-wave boundary',
        rows=rows,passed=all(x['hash_pass'] and abs(x['relative_error'])<.001 for x in rows),limitations=['two-cycle original windows','phase zero single CW','nominal Q50/Cp1p/50ohm only','29MHz 50mV point is near -1dB'])
    fixed(HERE/'previous_audit.json',json.dumps(result,indent=2).encode())
    print(json.dumps({'passed':result['passed'],'rows':[{k:r[k] for k in ['name','delta_db','relative_error']} for r in rows]},indent=2))

if __name__=='__main__':main()
