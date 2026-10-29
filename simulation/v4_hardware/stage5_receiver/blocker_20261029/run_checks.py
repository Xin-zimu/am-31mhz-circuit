"""Targeted convergence, boundary brackets and phase controls; no startup reruns."""
from run_diagnosis import *

def main():
    for f in [29e6,33e6]:
        for a in [.004,.005]:tran(f'R2_{int(f/1e6)}_{a*1000:g}',blockers=[[f,a,0]])
    tran('R2_33_10_h025',blockers=[[33e6,.01,0]],step=.25)
    tran('B_E1_29_6_h025',variant='B_E1',blockers=[[29e6,.006,0]],step=.25)
    tran('B_E1_33_5',variant='B_E1',blockers=[[33e6,.005,0]])
    kw=dict(front_file=str(HERE/'filters/A2M_r1M.cir'))
    for f in [29e6,33e6]:
        for a in [.04,.05,.06]:tran(f'A2M_r1M_{int(f/1e6)}_{a*1000:g}',**kw,blockers=[[f,a,0]])
    tran('A2M_r1M_33_10_h025',**kw,blockers=[[33e6,.01,0]],step=.25)
    tran('A2M_r1M_square10_h025',**kw,wave='square',duty=.1,step=.25)
    tran('A2M_r1M_square10_long',**kw,wave='square',duty=.1,start=250,stop=350)
    tran('R2_dual_10_phase90',blockers=[[29e6,.01,0],[33e6,.01,np.pi/2]])
    tran('A2M_r1M_dual_10_phase90',**kw,blockers=[[29e6,.01,0],[33e6,.01,np.pi/2]])
    tran('B_E1_clean_h025',variant='B_E1',step=.25)
    tran('A2M_r1M_clean_h025',**kw,step=.25)
    tran('A2M_r1M_29_50_h025',**kw,blockers=[[29e6,.05,0]],step=.25)
    for variant in ['R2','B_E1','A2M_r1M']:
        option=dict(front_file=str(HERE/'filters/A2M_r1M.cir')) if variant=='A2M_r1M' else dict(variant=variant)
        for duty in [.1,.5]:
            tran(f'{variant}_square{duty*100:g}_33_10',**option,wave='square',duty=duty,blockers=[[33e6,.01,0]])

if __name__=='__main__':main()
