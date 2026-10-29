from run_diagnosis import *
def result(n):return json.loads((HERE/'results'/(n+'.json')).read_text())['metrics']
def amplitude(n,node='out',f=20000):return result(n)['nodes'][node]['spectral_peak'][str(f)]
def db(a,b):return float(20*np.log10(a/b))
if __name__=='__main__':
    for v in ['R2']+list(VARIANTS)[1:]+['A2M','A1M']:
        if not (HERE/'results'/(v+'_clean.json')).exists():continue
        m=result(v+'_clean');clean=amplitude(v+'_clean')
        x=dict(variant=v,clean=clean,clean_db=db(clean,amplitude('R2_clean')),
            rf_gain=amplitude(v+'_clean','rf',31000000)/.01,power=m.get('supply_power_w'))
        for f in [29,33]:
            for a in [3,6,10,20,30]:
                name=f'{v}_{f}_{a}'
                if (HERE/'results'/(name+'.json')).exists():x[f'{f}_{a}']=db(amplitude(name),clean)
        print(json.dumps(x))
    for rs in [0,50]:
        for f in [29,33]:
            print('detector',rs,f,[db(amplitude(f'D_rs{rs}_{f}_{a}'),amplitude(f'D_rs{rs}_clean')) for a in [3,6,10]])
