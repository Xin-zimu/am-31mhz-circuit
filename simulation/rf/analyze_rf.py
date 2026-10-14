from pathlib import Path
import numpy as np,re,json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def read_raw(p):
 data=Path(p).read_bytes();mark='Binary:\n'.encode('utf-16le');k=data.find(mark)
 if k<0:mark='Binary:\r\n'.encode('utf-16le');k=data.find(mark)
 header=data[:k].decode('utf-16le');nv=int(re.search(r'No. Variables:\s*(\d+)',header).group(1));n=int(re.search(r'No. Points:\s*(\d+)',header).group(1))
 names=re.findall(r'^\s*\d+\s+(\S+)\s+\S+',header,re.M)
 arr=np.frombuffer(data,dtype=np.dtype([('time','<f8'),('v','<f4',(nv-1,))]),count=n,offset=k+len(mark))
 return {'time':arr['time'],**{nm:arr['v'][:,i] for i,nm in enumerate(names[1:])}}

def analyze(name):
 d=read_raw(ROOT/(name+'.raw'));print(name,{k:(float(v.min()),float(v.max())) for k,v in d.items()})
 t=d['time'];s=t>150e-6
 result={k:float(np.ptp(v[s])) for k,v in d.items() if k!='time'}
 edges=(np.arange(0,251)*1e-6);bins=np.searchsorted(t,edges);tm=(edges[1:]+edges[:-1])/2
 plt.rcParams['font.family']='DejaVu Sans'
 if 'V(v1)' in d:
  fig,ax=plt.subplots(4,1,figsize=(12,10),sharex=True)
  ax[0].plot(t[::60]*1e6,d['V(v1)'][::60],color='#147d92');ax[0].set_ylabel('TP1 V1 (V)')
  for a,node in zip(ax[1:3],['V(am_rf)','V(ant_tx)']):
   lo=[];hi=[]
   for l,r in zip(bins[:-1],bins[1:]):
    vv=d[node][l:r];lo.append(float(vv.min()) if len(vv) else np.nan);hi.append(float(vv.max()) if len(vv) else np.nan)
   a.fill_between(tm*1e6,lo,hi,alpha=.7,color='#815ac0');a.set_ylabel(node+' (V)')
  ax[3].plot(t[::60]*1e6,d['V(det_env)'][::60],color='#d66b20');ax[3].set_ylabel('TP6 envelope (V)');ax[3].set_xlabel('Time (us)')
  for a in ax:a.grid(alpha=.2)
  fig.suptitle(name+' | transistor-level simulation, assumed fixed channel loss');fig.tight_layout();fig.savefig(ROOT/(name+'.png'),dpi=170);plt.close(fig)
 else:
  fig,ax=plt.subplots(2,1,figsize=(11,6))
  ax[0].plot(t[::25]*1e6,d['V(osc_c)'][::25]);ax[0].set_xlabel('Time (us)');ax[0].set_ylabel('OSC_C (V)')
  s=(t>28e-6)&(t<28.3e-6);ax[1].plot(t[s]*1e9,d['V(osc_c)'][s]);ax[1].set_xlabel('Time (ns)');ax[1].set_ylabel('OSC_C (V)');fig.tight_layout();fig.savefig(ROOT/(name+'.png'),dpi=170);plt.close(fig)
 (ROOT/(name+'_measured.json')).write_text(json.dumps(result,indent=2))
if __name__=='__main__':analyze(sys.argv[1] if len(sys.argv)>1 else 'rf_chain')
