"""Exercise cache reuse and configuration guards without new simulations."""
import json
from run_selectivity import HERE,sha,ac,tran
from run_baseband import run

if __name__=='__main__':
    for name,fn in [('B_final_ac',ac),('B_clean',tran),('B_output_square50',run)]:
        r=json.loads((HERE/'results'/(name+'.json')).read_text())
        fn(name,**r['config'])
    protected=[HERE/'netlists/B_clean.cir',HERE/'netlists/B_output_square50_source.cir']
    before={str(p):sha(p) for p in protected};rejected=[]
    for name,fn,change in [('B_clean',tran,dict(ac=.011)),('B_output_square50',run,dict(feedback=103000))]:
        c=json.loads((HERE/'results'/(name+'.json')).read_text())['config'];c.update(change)
        try:fn(name,**c)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Changed configuration was reused: '+name)
    assert before=={str(p):sha(p) for p in protected}
    assert len(rejected)==2
    print(json.dumps(dict(cache_reuse=3,changed_configs_rejected=rejected,protected_files_unchanged=True)))
