from run_selectivity import tran
from run_validation import B
from run_baseband import run

if __name__=='__main__':
    for tag,kw in [('halfm',dict(m=.25)),('overload20m',dict(ac=.02))]:
        r=tran('B_open_'+tag,**B,wave='square',duty=.5,load=1e15,**kw)
        run('B_output_'+tag,wave='square',duty=.5,prebias=r['metrics']['out_dc'],**kw)
