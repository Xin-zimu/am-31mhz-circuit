from run_selectivity import ac,tran
from run_validation import B

if __name__=='__main__':
    for scale,cts in [(.8,[25,30,35]),(1.2,[3,5,7])]:
        for ct in cts:
            c={**B,'ct':ct,'lscale':scale}
            ac(f'B_trim_l{round(scale*100)}_ct{ct}',**c)
    for tag,kw in [('temp0',dict(temp=0)),('temp60',dict(temp=60)),
                   ('supply8',dict(supply=8)),('supply10',dict(supply=10))]:
        tran('B_check_'+tag,**B,**kw)

