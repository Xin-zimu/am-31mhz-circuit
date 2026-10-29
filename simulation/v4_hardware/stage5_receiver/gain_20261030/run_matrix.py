"""Authorized A + original Q1/Q2 matrix; every comparison uses fixed BB gain.

Six-cycle nominal checks have a 150 s compute budget, based on measured
24.5 s / 100 us cost. Most perturbation checks are only 200 us / 90 s.
No failed initialization recipes are rerun by this script.
"""
from run_gain import *
import argparse

def main(batch):
    if batch=='nominal':
        seeded('F22_sq50_sixcycles',wave='square',duty=.5,timeout_s=150)
        seeded('F22_sq10_h025_short',wave='square',duty=.1,start=50,stop=100,step=.25)
    if batch=='blocking':
        seeded('F22_sine_clean',stop=200)
        for f,amps in [(29e6,[.01,.05,.06]),(33e6,[.01,.04,.05])]:
            for a in amps:seeded(f'F22_sine_{f/1e6:g}_{a*1000:g}',stop=200,blockers=[[f,a,0]])
    if batch=='square':
        for duty in [.1,.5]:
            for f in [29e6,33e6]:
                seeded(f'F22_sq{duty*100:g}_{f/1e6:g}_10',wave='square',duty=duty,stop=200,blockers=[[f,.01,0]])
            seeded(f'F22_sq{duty*100:g}_dual10',wave='square',duty=duty,stop=200,blockers=[[29e6,.01,0],[33e6,.01,0]])
    if batch=='dynamic':
        for duty in [.1,.5]:
            seeded(f'F22_sq{duty*100:g}_Ac20',wave='square',duty=duty,stop=200,ac=.02)
            seeded(f'F22_sq{duty*100:g}_m025',wave='square',duty=duty,stop=200,m=.25)
            # Separate manually selected gain range, never folded into G22 pass.
            seeded(f'F11p2_sq{duty*100:g}_Ac20',wave='square',duty=duty,stop=200,ac=.02,feedback=102000)
    if batch=='physical':
        for n,kw in [('Q40',dict(front_file=str(HERE/'filters/Q40.cir'))),('RS200',dict(rs=200))]:
            seeded('F22_sq50_'+n,wave='square',duty=.5,stop=200,**kw)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('batch',choices=['nominal','blocking','square','dynamic','physical']);main(p.parse_args().batch)
