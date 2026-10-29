"""Independent ngspice processes, unique evidence paths, two workers maximum.
This does not open Multisim. A failed case is retained and is not retried.
"""
from run_gain import *
from concurrent.futures import ThreadPoolExecutor,as_completed

def cases():
    rows=[]
    for f,amps in [(29e6,[.01,.05,.06]),(33e6,[.01,.04,.05])]:
        for a in amps:rows.append((f'F22_sine_{f/1e6:g}_{a*1000:g}_gear',dict(method='gear',blockers=[[f,a,0]])))
    for duty in [.1,.5]:
        for f in [29e6,33e6]:rows.append((f'F22_sq{duty*100:g}_{f/1e6:g}_10',dict(wave='square',duty=duty,blockers=[[f,.01,0]])))
        rows.append((f'F22_sq{duty*100:g}_dual10',dict(wave='square',duty=duty,blockers=[[29e6,.01,0],[33e6,.01,0]])))
        rows.append((f'F22_sq{duty*100:g}_Ac20',dict(wave='square',duty=duty,ac=.02)))
        rows.append((f'F22_sq{duty*100:g}_m025',dict(wave='square',duty=duty,m=.25)))
        rows.append((f'F11p2_sq{duty*100:g}_Ac20',dict(wave='square',duty=duty,ac=.02,feedback=102000)))
    for n,kw in [('Q40',dict(front_file=str(HERE/'filters/Q40.cir'))),('RS200',dict(rs=200))]:
        rows.append(('F22_sq50_'+n,dict(wave='square',duty=.5,**kw)))
    rows.append(('F22_sine_clean_gear_h025',dict(method='gear',step=.25)))
    rows.append(('F22_sine_29_50_gear_h025',dict(method='gear',step=.25,blockers=[[29e6,.05,0]])))
    return rows

def one(item):
    name,kw=item
    ep=HERE/'matrix_execution.json'
    if ep.exists():
        prior={r['name']:r for r in json.loads(ep.read_text())}
        if name in prior and not prior[name]['completed']:
            print(json.dumps(dict(name=name,retained_failure=True)),flush=True)
            return prior[name]
    try:
        _,r=seeded(name,stop=200,timeout_s=150,**kw)
        return dict(name=name,completed=True)
    except Exception as e:
        print(json.dumps(dict(name=name,error=str(e))),flush=True)
        return dict(name=name,completed=False,error=str(e))

if __name__=='__main__':
    probe('P_G11p2_noic',feedback=102000)
    # Every process is restricted to one ngspice thread and its own files.
    with ThreadPoolExecutor(max_workers=2) as pool:
        result=[f.result() for f in as_completed([pool.submit(one,item) for item in cases()])]
    if not (HERE/'matrix_execution.json').exists():
        fixed(HERE/'matrix_execution.json',json.dumps(result,indent=2).encode())
