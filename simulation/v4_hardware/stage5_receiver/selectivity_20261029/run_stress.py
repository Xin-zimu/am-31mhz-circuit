from run_selectivity import ac,tran
from run_validation import R1,B

def main():
    for a in [.0001,.0003,.001,.003]:
        tran(f'R1_low_{a*1e6:g}u',**R1,blocker_a=a)
    for f in [29e6,33e6]:
        for a in [.001,.003,.006]:
            tran(f'B_near_{f/1e6:g}M_{a*1e3:g}m',**B,blocker_f=f,blocker_a=a)
    tran('B_low_1V',**B,blocker_a=1)
    for tag,kw in [('q20',dict(q=20)),('q100',dict(q=100)),
        ('lminus20',dict(lscale=.8)),('lplus20',dict(lscale=1.2)),
        ('cminus5',dict(cscale=.95)),('cplus5',dict(cscale=1.05)),
        ('cp2',dict(cp=2)),('rs200',dict(rs=200))]:
        ac('B_tol_'+tag,**B,**kw)
    for tag,kw in [('q20',dict(q=20)),('rs200',dict(rs=200)),
        ('load47k',dict(load=47000)),('load1meg',dict(load=1000000)),
        ('in5m',dict(ac=.005)),('in20m',dict(ac=.02)),('in40m',dict(ac=.04)),
        ('m0125',dict(m=.125)),('m090',dict(m=.9)),
        ('square30',dict(wave='square',duty=.3)),('square50',dict(wave='square',duty=.5)),
        ('step025',dict(step=.25)),('long',dict(start=400,stop=650)),
        ('block025',dict(step=.25,blocker_f=29e6,blocker_a=.01))]:
        tran('B_check_'+tag,**B,**kw)

if __name__=='__main__': main()
