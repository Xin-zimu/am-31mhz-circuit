from pathlib import Path
import sys, re, json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_simulation import run_spice, read_raw
from measure import measurements
HERE=Path(__file__).resolve().parent
base=Path('D:/ms_xsp/v3_20k/baseline_A4.cir').read_text()
# Use --generic to reproduce the imported file's lost diode model for diagnosis.
# The final project restores the original engineering Schottky approximation.
generic = '--generic' in sys.argv
if generic:
    base=re.sub(r'\.model SCHOTTKY_EST[^\n]+','.model SCHOTTKY_EST D',base)
base=base.replace('SIN(0 1 31meg)','SIN(0 1.000001953296563 31meg)')
base=base.replace('.end','.options plotwinsize=0 reltol=0.001\n.save V(V1) V(V2) V(TP6) V(TP3) V(TP2)\n.tran 2n 5m 4.8m 2n\n.end')
gain=float(sys.argv[1]) if len(sys.argv)>1 else 15
rows=[]
for amp,duty in ([(4,50)] if len(sys.argv)==1 else [(1,50),(2,50),(3,50),(4,50),(4,10)]):
    net=base.replace('PULSE(0 4 10u 20n 20n 25u 50u)',f'PULSE(0 {amp} 10u 20n 20n {duty*.5:g}u 50u)')
    net=net.replace('BB_IN VREF 15',f'BB_IN VREF {gain:.9g}')
    path=HERE/f'LT_{"generic" if generic else "schottky"}_A{amp}_D{duty}_G{gain:.6g}.cir'
    path.write_text(net,encoding='ascii')
    run_spice(path)
    d=read_raw(path.with_suffix('.raw'))
    result={'amplitude':amp,'duty':duty,'gain':gain,'file':str(path),'metrics':measurements(d)}
    rows.append(result)
    print(json.dumps(result),flush=True)
(HERE/f'lt_results_{"generic" if generic else "schottky"}_G{gain:.6g}.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
