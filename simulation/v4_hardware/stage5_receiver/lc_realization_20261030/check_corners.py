"""48 design-envelope corners, each individually re-tuned; not a yield estimate."""
from run_lc import *


def main():
    n=LoadedNetwork()
    nominal=json.loads((HERE/'standard_values.json').read_text())['parameters']
    rows=[]
    for i,(s1,s2,q,board,ck) in enumerate(itertools.product([.95,1.05],[.95,1.05],[40.,50.,80.],[.5,2.],[2.3,2.5])):
        p={**nominal,'l1':460*s1,'l2':460*s2,'q1':q,'q2':q,
           'board1':board,'board2':board,'ck':ck}
        p,opt=tune(n,p);h,z=n.response(p)
        rows.append(dict(name=f'corner_{i:02d}',parameters=p,metrics=metrics(n.f,h,z),optimization=opt))
    # The three distinct worst metrics drive independent solver confirmation.
    selected=set()
    selected.add(min(rows,key=lambda r:r['metrics']['gain31_v_v'])['name'])
    selected.add(max(rows,key=lambda r:max(r['metrics']['relative29_db'],r['metrics']['relative33_db']))['name'])
    selected.add(min(rows,key=lambda r:r['metrics']['return_loss50_db'])['name'])
    for r in rows:
        if r['name'] in selected:r['spice']=spice(r['name'],r['parameters'])
    dump(HERE/'corner_results.json',rows)
    print('Corners:',len(rows),'SPICE selected:',sorted(selected))
    for q in [40,50,80]:
        subset=[r for r in rows if r['parameters']['q1']==q]
        print(q,{k:[min(r['metrics'][k] for r in subset),max(r['metrics'][k] for r in subset)]
                 for k in ['gain31_v_v','bw_mhz','center_edges_mhz','relative29_db','relative33_db']})
    print('CT ranges',[(k,min(r['parameters'][k] for r in rows),max(r['parameters'][k] for r in rows)) for k in ['ct1','ct2']])


if __name__=='__main__':main()
