import json
from run_selectivity import tran,HERE
from run_validation import B
from run_baseband import run

def main():
    for tag,wave,duty in [('sine','sine',.5),('square10','square',.1),('square30','square',.3),('square50','square',.5)]:
        r=tran('B_open_'+tag,**B,wave=wave,duty=duty,load=1e15)
        prebias=r['metrics']['out_dc']
        run('B_output_'+tag,wave=wave,duty=duty,prebias=prebias)
    # Same gain and explicit starting bias; load current and cable capacitance.
    r=json.loads((HERE/'results/B_open_square50.json').read_text())
    run('B_output_load10k1n',wave='square',duty=.5,
        prebias=r['metrics']['out_dc'],bb_load=10000,bb_cap=1000)

if __name__=='__main__': main()
