"""ALT.3.3 independent screening models, NOT measurements of a catalog whip."""
from pathlib import Path
import json, math, csv
import numpy as np
import nec_support as nec
ROOT=Path(__file__).resolve().parent
nec.EXE=ROOT.parent/'stage_am_alt3_1_20261116/tools/nec2c.exe'
W=2*math.pi*31e6

def cards(length,n=60,radius=.0015,sigma=1.4e6,soil=(13,.005),f=31):
    # Uniform effective-radius proxy. Actual stepped diameters/overlaps are unknown.
    h=.83
    c=[nec.gw(1,n,(0,0,h),(0,0,h+length),radius)]
    for k in range(8):
        a=2*math.pi*k/8
        c.append(nec.gw(k+2,round(n*.5/length),(0,0,h),(.5*math.cos(a),.5*math.sin(a),h)))
    c+=['GE 0']
    if soil: c+=['GN 2 0 0 0 %g %g'%soil]
    c+=['LD 5 1 0 0 %g'%sigma,'LD 5 2 0 0 5.8e7']
    for tag in range(3,10): c+=['LD 5 %d 0 0 5.8e7'%tag]
    c+=['FR 0 1 0 0 %g'%f,'EX 0 1 1 0 1 0','RP 0 %d 73 1000 0 0 5 5'%(19 if soil else 37)]
    return c

def main():
    nec.benchmarks()
    rows=[]
    for length in [.7,.8,.9,1.0]:
        for label,n,r,s,g,f in [
            ('n40',40,.0015,1.4e6,(13,.005),31),
            ('nom',60,.0015,1.4e6,(13,.005),31),
            ('n80',80,.0015,1.4e6,(13,.005),31),
            ('thin',60,.0005,1.4e6,(13,.005),31),
            ('thick',40,.003,1.4e6,(13,.005),31),
            ('copper',60,.0015,5.8e7,(13,.005),31),
            ('dry',60,.0015,1.4e6,(5,.001),31),
            ('wet',60,.0015,1.4e6,(20,.03),31),
            ('free',60,.0015,1.4e6,None,31),
            ('flo',60,.0015,1.4e6,(13,.005),30.9),
            ('fhi',60,.0015,1.4e6,(13,.005),31.1)]:
            d=nec.solve(f'h{round(length*100)}_{label}',cards(length,n,r,s,g,f))
            d.update(length_m=length,label=label,n=n,radius_m=r,sigma_Sm=s,soil=g,f_MHz=f)
            d['Ceq_pF']=-1/(2*math.pi*f*1e6*d['X'])*1e12
            d['L_uH']=-d['X']/(2*math.pi*f)
            rows.append(d)
            print(d['name'],round(d['R'],4),round(d['X'],2),flush=True)
    (ROOT/'antenna_all.json').write_text(json.dumps(rows,indent=2))
    nominal=[]
    for d in rows:
        if d['label']!='nom': continue
        h=d['length_m']; lo=next(x for x in rows if x['length_m']==h and x['label']=='flo'); hi=next(x for x in rows if x['length_m']==h and x['label']=='fhi')
        slope=(hi['X']-lo['X'])/(2*math.pi*.2e6)
        la=(slope+d['X']/W)/2
        ca=1/(W*(W*la-d['X']))
        assert la>0 and ca>0
        d.update(Lant_H=la,Cant_F=ca)
        n80=next(x for x in rows if x['length_m']==h and x['label']=='n80')
        d['mesh_R_relative']=abs(n80['R']/d['R']-1)
        d['mesh_X_relative']=abs(n80['X']/d['X']-1)
        nominal.append(d)
    (ROOT/'antenna_nominal.json').write_text(json.dumps(nominal,indent=2))
    keys=['length_m','R','X','Ceq_pF','L_uH','R_wire','R_radiated','R_ground','radiated_fraction','Lant_H','Cant_F','mesh_R_relative','mesh_X_relative']
    with (ROOT/'length_comparison.csv').open('w',newline='',encoding='utf-8-sig') as out:
        w=csv.DictWriter(out,keys,extrasaction='ignore');w.writeheader();w.writerows(nominal)

if __name__=='__main__': main()
