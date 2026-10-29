"""Selected R1 circuit: two degenerated CE stages, follower, BAT85 reference, F1 filter."""
from run_s05 import prepare,transient

def run(name,**c):
    cfg=dict(amp=True,reu=22,rreturn=1000,dc_return='direct',ac=.01,
             rd=4700,cd=100,rf=4700,cf=100)
    cfg.update(c)
    return transient('r1_'+name,**cfg)

if __name__=='__main__':
    prepare()
    for a in [.0001,.001,.003,.005,.01,.015,.02,.04,.08]:run('a'+str(a).replace('.','p'),ac=a)
    for duty in [.1,.3,.5]:run('d'+str(duty).replace('.','p'),wave='square',duty=duty)
    for m in [.125,.25,.75,.9]:run('m'+str(m).replace('.','p'),m=m)
    for temp in [0,50]:run('temp'+str(temp),temp=temp)
    run('diode_stress',diode_stress=True)
    run('load10k',load=10000)
    run('rs200',rs=200)
    run('converge025',step_ns=.25)
    run('square_converge025',wave='square',duty=.1,step_ns=.25)
    run('tail600us',stop_us=600,start_us=400)
