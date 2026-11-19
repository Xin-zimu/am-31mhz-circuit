from run_nec import *
import hashlib

rows=json.loads((ROOT/'tabletop.json').read_text())
selected=next(d for d in rows if d['name']=='desk_r8_l0.5_n120_soil')
env=[]
for h in [.68,.83,1.03]:
 for label,g in [('dry',(5,.001)),('nom',(13,.005)),('wet',(20,.03))]:
  d=solve(f'selected_h{h}_{label}',model(8,.5,0,h=h,n=80,ground=g));env.append(d)
for length in [.1,.3,.5]:
 env.append(solve(f'selected_cm{length}',model(8,.5,0,h=.83,n=80,ground=(13,.005),extra=[((0,0,.83),(0,0,.83-length))])))
for f in [30.69,30.9,31.1,31.31]:
 c=model(8,.5,0,h=.83,n=80,ground=(13,.005))
 c=[x.replace('FR 0 1 0 0 31 0',f'FR 0 1 0 0 {f} 0') for x in c]
 d=solve(f'selected_f{f}',c);d['frequency_MHz']=f;env.append(d)
save('selected_environment',env)

w=2*math.pi*31e6
scan=[]
for case in rows[:24]:
 for q in [30,60,100]:
  for l in np.linspace(2,5,301):
   z=complex(case['R']+10+w*l*1e-6/q,case['X']+w*l*1e-6)
   scan.append(dict(case=case['name'],Q=q,L_uH=float(l),R_ohm=z.real,X_ohm=z.imag,
      I_mA_per_100mVrms=100/abs(z),radiated_efficiency_with_sense=case['R_radiated']/z.real))
with (ROOT/'tuning_scan.csv').open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=scan[0]);writer.writeheader();writer.writerows(scan)

summary=[]
for q in [30,60,100]:
 rcoil=-selected['X']/q;r=selected['R']+rcoil
 summary.append(dict(Q=q,R_coil=rcoil,R_tuned_without_sense=r,R_tuned_with_sense=r+10,
   eta_without_sense=selected['R_radiated']/r,eta_with_sense=selected['R_radiated']/(r+10),
   I_mA_per_100mVrms=100/(r+10)))
save('selected_efficiency',summary)

# Mechanical winding estimate. Q is an effective series-terminal Q at 31 MHz.
coils=[]
for n in [12,14,16,18]:
 for length in [25,30,35,40,45,50,60]:
  r=12.5/25.4;b=length/25.4;l=r*r*n*n/(9*r+10*b)
  coils.append(dict(turns=n,centre_diameter_mm=25,length_mm=length,L_low_frequency_uH=l,
    wire_length_m=math.hypot(math.pi*.025*n,length/1000)+.04))
save('coil_geometry',coils)

# Independent lumped sensitivity, not a NEC dielectric-board solution.
sensitivity=[]
za=complex(selected['R'],selected['X'])
for cp in [0,.25,.5,1,2]:
 z=1/(1/za+1j*w*cp*1e-12)
 for cc in [0,.5,1,2]:
  leff=-z.imag/w
  l0=leff/(1+w*w*leff*cc*1e-12)
  sensitivity.append(dict(installation_parallel_C_pF=cp,coil_self_C_pF=cc,
     L_effective_31MHz_uH=leff*1e6,L_winding_low_frequency_uH=l0*1e6))
save('parasitic_sensitivity',sensitivity)

# A port-mounted series impedance has an exact circuit combination at one frequency.
# Verify against NEC loading instead of assuming the sweep arithmetic is wired correctly.
checks=[]
for q in [30,60,100]:
 c=model(8,.5,0,h=.83,n=120,ground=(13,.005))
 c.insert(c.index('FR 0 1 0 0 31 0'),'LD 0 1 1 1 %.12g %.12g 0'%(10-selected['X']/q,selected['L_uH']*1e-6))
 d=solve(f'selected_loaded_q{q}',c)
 expect=selected['R']+10-selected['X']/q
 d['expected_R']=expect;d['R_error']=d['R']-expect
 checks.append(d)
 assert abs(d['R_error'])<.01 and abs(d['X'])<.02
save('loaded_crosscheck',checks)
print(json.dumps(dict(selected={k:v for k,v in selected.items() if k!='pattern'},efficiency=summary),indent=2),flush=True)
