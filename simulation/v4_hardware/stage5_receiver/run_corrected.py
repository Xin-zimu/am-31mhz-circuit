"""Corrected fixture with defined DC return; v1 failed cases remain immutable."""
from run_s05 import prepare, transient

def run(name,**c): return transient('v2_'+name,dc_return='direct',**c)

if __name__=='__main__':
    prepare()
    for a in [.01,.03,.05,.1,.2,.3,.5,.8,1.2,2]: run('a'+str(a).replace('.','p'),ac=a)
    for cd in [47,220,470]: run('cd'+str(cd),cd=cd)
    for load in [10000,1000000]: run('load'+str(load),load=load)
    for rs in [200,1000]:run('rs'+str(rs),rs=rs)
    for m in [.125,.25,.75,.9]: run('m'+str(m).replace('.','p'),m=m)
    for a in [.1,.5,1.2]:
        for duty in [.1,.3,.5]:run(f'square_a{a}_d{duty}'.replace('.','p'),ac=a,wave='square',duty=duty)
    run('converge_025ns',step_ns=.25)
    run('square_converge_025ns',wave='square',duty=.1,step_ns=.25)
