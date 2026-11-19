"""User steering: horizontal counterpoise on an insulating tabletop."""
from run_nec import *
rows=[]
for nr,l in [(4,.25),(4,.5),(8,.25),(8,.5)]:
 for n in [40,80,120]:
  for label,g in [('free','free'),('soil',(13,.005))]:
   d=solve(f'desk_r{nr}_l{l}_n{n}_{label}',model(nr,l,0,h=.83,n=n,ground=g))
   d.update(nrad=nr,length=l,n=n,environment=label);rows.append(d)
for nr,l in [(4,.5),(8,.25)]:
 for h in [.68,.83,1.03]:
  for label,g in [('dry',(5,.001)),('wet',(20,.03))]:
   d=solve(f'desk_r{nr}_l{l}_h{h}_{label}',model(nr,l,0,h=h,n=80,ground=g));rows.append(d)
 for length in [.1,.3,.5]:
  d=solve(f'desk_r{nr}_l{l}_cm{length}',model(nr,l,0,h=.83,n=80,ground=(13,.005),extra=[((0,0,.83),(0,0,.83-length))]));rows.append(d)
 for f in [30.69,30.9,31.1,31.31]:
  c=model(nr,l,0,h=.83,n=80,ground=(13,.005));c=[x.replace('FR 0 1 0 0 31 0',f'FR 0 1 0 0 {f} 0') for x in c]
  d=solve(f'desk_r{nr}_l{l}_f{f}',c);d['frequency_MHz']=f;rows.append(d)
save('tabletop',rows)
for d in rows:print(d['name'],*[round(d[k],4) for k in ['R','X','L_uH','radiated_fraction']],flush=True)
