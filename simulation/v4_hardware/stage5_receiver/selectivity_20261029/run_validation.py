"""Frozen second-batch candidates and predeclared blocker sweep.

1 dB useful-baseband fundamental change is an engineering boundary marker,
not the course acceptance criterion. No wireless sensitivity claim.
"""
from run_selectivity import ac,noise,tran

R1=dict(kind='R1')
A=dict(kind='A',lp=470,cs=22,ct=15)
B=dict(kind='B',lp=470,cs=27,ct=15,ceb=330,reu=33,inter=100)
CANDIDATES={'R1':R1,'A':A,'B':B}

def initial():
    for name,c in CANDIDATES.items():
        ac(name+'_final_ac',**c);noise(name+'_noise',**c)
        tran(name+'_clean',**c)
        tran(name+'_square10',**c,wave='square',duty=.1)

def blockers():
    for name,c in CANDIDATES.items():
        for f in [1.6e6,29e6,33e6]:
            for a in [.01,.03,.1]:
                tran(f'{name}_blk_{f/1e6:g}M_{a*1000:g}m'.replace('.','p'),**c,blocker_f=f,blocker_a=a)

if __name__=='__main__':
    initial();blockers()
