from run_nec import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import difflib, hashlib

data=json.loads((ROOT/'tabletop.json').read_text())
sel=next(x for x in data if x['name']=='desk_r8_l0.5_n120_soil')
eff=json.loads((ROOT/'selected_efficiency.json').read_text())
fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
base=[x for x in data if x.get('n')==120 and x.get('environment')=='soil']
labels=[f"{x['nrad']} x {x['length']:.2f} m" for x in base]
ax[0,0].bar(labels,[x['L_uH'] for x in base],color=['#a3aab7','#6387bc','#6387bc','#1b9e77'])
ax[0,0].axhspan(2,5,alpha=.08,color='green');ax[0,0].axhline(5,color='red',ls='--');ax[0,0].set(ylabel='Required effective L at 31 MHz (uH)',title='Horizontal radial comparison')
ax[0,1].plot([x['Q'] for x in eff],[100*x['eta_without_sense'] for x in eff],'o-',label='Without 10 ohm sense')
ax[0,1].plot([x['Q'] for x in eff],[100*x['eta_with_sense'] for x in eff],'o-',label='With frozen 10 ohm sense')
ax[0,1].set(xlabel='Effective coil Q at 31 MHz',ylabel='Upper-space radiation / input (%)',title='Specified lossy-ground scenario');ax[0,1].legend()
pp=np.array(sel['pattern']); cut=pp[pp[:,1]==0]
ax[1,0].plot(90-cut[:,0],cut[:,4]);ax[1,0].set(xlabel='Elevation (degrees)',ylabel='Bare antenna power gain (dBi)',title='Pattern: soil er=13, sigma=0.005 S/m');ax[1,0].set_ylim(-35,3)
for q in [30,60,100]:
 l=np.linspace(2,5,601);z=sel['R']+10+2*np.pi*31*l/q+1j*(sel['X']+2*np.pi*31*l)
 ax[1,1].plot(l,100/abs(z),label=f'Q={q}')
ax[1,1].set(xlabel='Effective series inductance (uH)',ylabel='Current per 100 mV RMS (mA)',title='Fixed-voltage sweep, not driver prediction');ax[1,1].legend()
for a in ax.flat:a.grid(alpha=.2)
fig.savefig(ROOT/'simulation_summary.png',dpi=170);plt.close(fig)

fig,ax=plt.subplots(1,2,figsize=(11,5),layout='constrained')
for a in np.arange(8)*np.pi/4:
 ax[0].plot([0,.5*np.cos(a)],[0,.5*np.sin(a)],color='#b87333',lw=2)
ax[0].scatter([0],[0],color='#194e80',s=60);ax[0].set(xlim=(-.55,.55),ylim=(-.55,.55),xlabel='m',ylabel='m',title='Top: 8 x 0.50 m, 45-degree spacing',aspect='equal')
ax[1].plot([-.55,.55],[0,0],lw=5,color='#bd9568');ax[1].plot([0,0],[.03,1.03],color='#b87333',lw=3)
ax[1].plot([-.5,.5],[.03,.03],color='#b87333',lw=2)
ax[1].scatter([0],[.03],s=65,facecolor='white',edgecolor='#194e80',zorder=5)
ax[1].plot([-.45,0,.45],[0,1.01,0],ls='--',color='gray')
ax[1].annotate('1.00 m conductor',(.01,.6));ax[1].annotate('30 mm clearance',(-.5,.05));ax[1].annotate('Nonconductive guy lines',(-.52,.9))
ax[1].set(xlim=(-.6,.65),ylim=(-.08,1.12),xlabel='m',ylabel='Height above tabletop (m)',title='Side: insulating desk; coil at base',aspect='equal')
fig.suptitle('Mechanical layout only: radiator feed is insulated from radial hub',fontsize=12)
fig.savefig(ROOT/'tabletop_structure.png',dpi=170);plt.close(fig)

up=ROOT/'tools/nec2c-1.3.1';win=ROOT/'tools/nec2c-win';diff=[]
for name in ['nec2c.h','main.c','misc.c']:
 diff+=difflib.unified_diff((up/name).read_text().splitlines(True),(win/name).read_text().splitlines(True),fromfile='upstream/'+name,tofile='windows/'+name)
(ROOT/'tools/windows_portability.patch').write_text(''.join(diff))
print('Figures and portability diff written')
