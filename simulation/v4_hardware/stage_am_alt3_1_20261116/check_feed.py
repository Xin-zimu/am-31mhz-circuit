from run_nec import *
rows=[]
for n in [40,80,120]:
 for nr in [4,8]:
  for a in [0,45]:
   c=model(nr,.5,a,n=n)
   c[0]=gw(1,3,(0,0,1),(0,0,1.03))
   c.insert(1,gw(99,n,(0,0,1.03),(0,0,2)))
   c=[x.replace('EX 0 1 1 0 1 0','EX 0 1 2 0 1 0') for x in c]
   d=solve(f'feed_r{nr}_a{a}_n{n}',c); rows.append(d)
   print(d['name'],d['R'],d['X'],d['radiated_fraction'],d['loss_fraction'],flush=True)
save('feed_checks',rows)
