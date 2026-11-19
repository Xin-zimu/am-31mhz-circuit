from run_nec import *

def run():
 rows=[]
 for length in [.5,.75]:
  for n in [40,80,120]:
   for ground in ['free',(13,.005)]:
    name=f'final_l{length}_n{n}_'+('free' if ground=='free' else 'soil')
    d=solve(name,model(4,length,30,h=1.2,n=n,ground=ground)); d.update(length=length,n=n);rows.append(d)
 for h in [.8,1.2,1.6]:
  for label,g in [('dry',(5,.001)),('nom',(13,.005)),('wet',(20,.03))]:
   name=f'final_h{h}_{label}'
   d=solve(name,model(4,.5,30,h=h,n=80,ground=g));d.update(height=h,soil=label);rows.append(d)
 # Common-mode stress: unwanted conductor bonded to radial hub.
 for length in [.1,.3,.5]:
  d=solve(f'common_mode_{length}',model(4,.5,30,h=1.2,n=80,ground=(13,.005),extra=[((0,0,1.2),(0,0,1.2-length))]));rows.append(d)
 # A floating vertical metal object, same wire radius, 0.5 m away.
 rows.append(solve('nearby_metal',model(4,.5,30,h=1.2,n=80,ground=(13,.005),extra=[((.5,.1,.5),(.5,.1,1.5))])))
 save('final_cases',rows)
 for d in rows: print(d['name'],*[round(d[k],4) for k in ['R','X','L_uH','radiated_fraction','R_ground']],flush=True)

if __name__=='__main__':run()
