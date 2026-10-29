"""S05 discrete receiver amplifier: AC/noise then loaded nonlinear AM runs."""
import json
import numpy as np
from run_s05 import HERE, models, prepare, amplifier, run_net, save_result, transient

def small_signal(name, **kw):
    c=dict(stages=2,rc=1000,reu=47,load=2000,cload=10,rs=50);c.update(kw)
    circuit=f'''* Discrete RX amplifier; 9 V ideal bench supply; explicit AC test load
VIN src 0 DC 0 AC 1
RSOURCE src port {c['rs']}
{amplifier(c)}
RTEST rf 0 {c['load']}
CTEST rf 0 {c['cload']}p
{models()}
.options temp=27 tnom=27
'''
    net=circuit+'''.control
set filetype=binary
save all
ac dec 200 100k 1G
write @RAW@
quit
.endc
.end
'''
    d,r=run_net(name,net,c)
    f=d['frequency'].real; v=d['v(rf)']; gain=np.abs(v)
    g31=float(np.interp(31e6,f,gain)); peak=float(gain.max()); valid=f[gain>=peak/np.sqrt(2)]
    r['metrics']=dict(gain_31mhz=g31,gain_db_31mhz=20*np.log10(g31),
       peak_gain=peak,peak_frequency_hz=float(f[np.argmax(gain)]),
       minus3db_low_sample_hz=float(valid.min()),minus3db_high_sample_hz=float(valid.max()),
       gain_30p8mhz=float(np.interp(30.8e6,f,gain)),gain_31p2mhz=float(np.interp(31.2e6,f,gain)),
       note='AC about DC operating point with 2k||10p load, not driven nonlinear diode impedance')
    save_result(r)
    print(json.dumps(dict(name=name,**r['metrics'])),flush=True)
    net=circuit+'''.control
set filetype=binary
noise v(rf) VIN lin 501 30.5meg 31.5meg
setplot noise1
write @RAW@ all
quit
.endc
.end
'''
    d,r=run_net(name+'_noise',net,c)
    f=d['frequency']; en=d['inoise_spectrum']; on=d['onoise_spectrum']
    k=1.380649e-23;t=300.15
    r['metrics']=dict(input_noise_v_rt_hz_31mhz=float(np.interp(31e6,f,en)),
        output_noise_v_rt_hz_31mhz=float(np.interp(31e6,f,on)),
        integrated_input_noise_v_rms_1mhz=float(np.sqrt(np.trapezoid(en**2,f))),
        integrated_output_noise_v_rms_1mhz=float(np.sqrt(np.trapezoid(on**2,f))),
        noise_factor_db_31mhz=float(10*np.log10(np.interp(31e6,f,en)**2/(4*k*t*c['rs']))),
        note='Linearized model noise incl. source resistor; not demodulated SNR/sensitivity, external noise omitted')
    save_result(r);print(json.dumps(dict(name=r['name'],**r['metrics'])),flush=True)

if __name__=='__main__':
    prepare()
    small_signal('rx_ac')
    for a in [.0001,.001,.003,.005,.01,.02,.04,.08]:
        transient('rx_a'+str(a).replace('.','p'),amp=True,ac=a)
    for duty in [.1,.3,.5]:
        transient('rx_square_d'+str(duty).replace('.','p'),amp=True,ac=.01,wave='square',duty=duty)
    for m in [.125,.25,.75,.9]:
        transient('rx_m'+str(m).replace('.','p'),amp=True,ac=.01,m=m)
    transient('rx_converge_025ns',amp=True,ac=.01,step_ns=.25)
