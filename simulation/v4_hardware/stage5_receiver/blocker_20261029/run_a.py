"""Standalone physical-LC candidates; original R2 file is never edited."""
from run_diagnosis import *

def main():
    for tag in ['A2M_r1M','A1M_r1M']:
        kw=dict(front_file=str(HERE/'filters'/(tag+'.cir')))
        ac(tag+'_ac',**kw);tran(tag+'_clean',**kw)
        for f in [29e6,33e6]:
            for a in [.003,.006,.01,.02,.03]:
                tran(f'{tag}_{int(f/1e6)}_{a*1000:g}',**kw,blockers=[[f,a,0]])
        tran(tag+'_dual_10',**kw,blockers=[[29e6,.01,0],[33e6,.01,0]])
        for duty in [.1,.5]:tran(f'{tag}_square{duty*100:g}',**kw,wave='square',duty=duty)
    for tag in ['R2','B_E1']:
        for duty in [.1,.5]:tran(f'{tag}_square{duty*100:g}',variant=tag,wave='square',duty=duty)
    # Best screened B remains a costed comparison, not an accepted optimization.
    for f in [29e6,33e6]:
        for a in [.003,.01]:tran(f'B_E1_{int(f/1e6)}_{a*1000:g}',variant='B_E1',blockers=[[f,a,0]])

if __name__=='__main__':main()
