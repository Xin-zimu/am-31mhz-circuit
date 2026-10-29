"""Scientific figures from raw arrays; no synthesized output waveforms."""
from run_gain import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def rec(n,previous=False):
    p=(PREV if previous else HERE)/'results'/(n+'.json')
    r=json.loads(p.read_text());return r,d.readraw(Path(r['raw_path']))

def wave(ax,n,label,previous=False,color=None):
    r,x=rec(n,previous);stop=r['config']['stop']*1e-6
    t=stop-50e-6+np.arange(5000)*10e-9
    y=np.interp(t,x['time'],x['v(final)'])
    ax.plot((t-(stop-50e-6))*1e6,y,label=label,color=color,lw=1.4)

def main():
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.22,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    fig,aa=plt.subplots(2,2,figsize=(11,7),sharex=True)
    for j,duty in enumerate([10,50]):
        wave(aa[0,j],f'F_A2M_square{duty}','A, G=11.2 (S05-05)',True,'#8996a7')
        wave(aa[0,j],f'F22_sq{duty}_sixcycles','A, G=22',color='#176baf')
        aa[0,j].set_title(f'Ac = 10 mV; duty = {duty}%')
        aa[0,j].axhline(9,color='#b64b4b',ls=':',lw=1)
        aa[0,j].legend(fontsize=8,loc='upper right');aa[0,j].set_ylabel('Final output (V)')
        n=f'F22_sq{duty}_Ac20'
        if not (HERE/'results'/(n+'.json')).exists():n+='_gear'
        wave(aa[1,j],n,'G=22, clipping',color='#bb3f3f')
        wave(aa[1,j],f'F11p2_sq{duty}_Ac20','G=11.2, separate range',color='#278657')
        aa[1,j].axhline(9,color='#b64b4b',ls=':',lw=1);aa[1,j].axhline(0,color='#b64b4b',ls=':',lw=1)
        aa[1,j].set_title(f'Ac = 20 mV; duty = {duty}%');aa[1,j].legend(fontsize=8,loc='upper right')
        aa[1,j].set_xlabel('Time within final period (us)');aa[1,j].set_ylabel('Final output (V)')
    fig.suptitle('Actual TI OPA197 integrated results, 9 V supply; warm operating condition')
    fig.tight_layout();fig.savefig(HERE/'plots/output_waveforms.png');plt.close(fig)
    fig,aa=plt.subplots(1,2,figsize=(11,4.1))
    for ax,f in zip(aa,[29,33]):
        old=[]
        for a in [0,3,4,6,10]:
            n='R2_clean' if a==0 else f'R2_{f}_{a}'
            r,_=rec(n,True);old.append(r['metrics']['nodes']['out']['spectral_peak']['20000'])
        ax.plot([0,3,4,6,10],20*np.log10(np.array(old)/old[0]),'o-',color='#8996a7',label='Original R2 detector')
        orig=[]
        for a in [0,10,20,30,40,50,60]:
            r,_=rec('A2M_r1M_clean' if a==0 else f'A2M_r1M_{f}_{a}',True);orig.append(r['metrics']['nodes']['out']['spectral_peak']['20000'])
        ax.plot([0,10,20,30,40,50,60],20*np.log10(np.array(orig)/orig[0]),'o-',label='S05-05 A detector',color='#d09426')
        amps=[0,10,50,60] if f==29 else [0,10,40,50]
        new=[]
        for a in amps:
            r,_=rec('F22_sine_clean_gear' if a==0 else f'F22_sine_{f}_{a}_gear');new.append(r['metrics']['final']['peak20'])
        ax.plot(amps,20*np.log10(np.array(new)/new[0]),'s--',label='A + actual OPA G=22',color='#176baf')
        ax.axhline(-1,ls=':',color='#bb3f3f');ax.set_title(f'{f} MHz CW');ax.set_xlabel('CW source peak (mV)');ax.set_ylabel('Useful 20 kHz change (dB)');ax.set_ylim(-2.1,.1);ax.legend(fontsize=8)
    fig.suptitle('Sine AM: Ac = 10 mV, m = 0.5; each curve normalized to its own clean case')
    fig.tight_layout();fig.savefig(HERE/'plots/blocking.png');plt.close(fig)
    fig,aa=plt.subplots(1,2,figsize=(11,4.1))
    for n,label in [('Q50','Q50 nominal'),('Q40','Q40'),('Q30','Q30'),('Q20','Q20')]:
        r,x=rec('C_'+n);aa[0].plot(x['frequency'].real/1e6,20*np.log10(abs(x['v(rf)'])),label=label)
    for n,label in [('Q50','Nominal'),('Lboth0p95','L -5%, untuned'),('Lboth1p05','L +5%, untuned'),('retuneL0p95','L -5%, retuned'),('retuneL1p05','L +5%, retuned')]:
        r,x=rec('C_'+n);aa[1].plot(x['frequency'].real/1e6,20*np.log10(abs(x['v(rf)'])),label=label,ls='--' if 'retune' in n else '-')
    for ax in aa:
        ax.set_xlim(27,35);ax.set_ylim(5,35);ax.set_xlabel('Frequency (MHz)');ax.set_ylabel('Source-to-RF voltage gain (dB)');ax.legend(fontsize=8)
        for f in [29,31,33]:ax.axvline(f,color='gray',ls=':',lw=.6)
    aa[0].set_title('Inductor Q at 31 MHz');aa[1].set_title('Tolerance and independent capacitor retuning')
    fig.tight_layout();fig.savefig(HERE/'plots/component_response.png');plt.close(fig)

if __name__=='__main__':main()
