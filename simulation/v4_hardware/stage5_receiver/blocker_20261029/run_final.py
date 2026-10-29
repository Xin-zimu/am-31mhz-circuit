"""Full BAT85 + original TI OPA197 checks, explicitly prebiased.
No cold start, no AGC; fixed feedback within every paired comparison.
"""
from run_diagnosis import *
from run_baseband import bb,MODEL

def run(name,**kw):
    c=config(**kw);c.update(feedback=kw.get('feedback',102000),bb_load=1e6,bb_cap=100)
    dc_kw={k:v for k,v in kw.items() if k!='feedback'};dc_kw['load']=1e15
    _,r0=tran(name+'_open',**dc_kw)
    c['prebias']=r0['metrics']['nodes']['out']['dc']
    fixed(HERE/'sources/OPAx197.LIB',MODEL.read_bytes())
    fixed(WORK/'OPAx197.LIB',MODEL.read_bytes())
    net=circuit(c,source(c))+old.old.detector(dict(dc_return='direct',rd=4700,cd=100,rf=4700,cf=100,load=1e15))+old.old.models()
    net+=bb(c)+f".ic v(out)={c['prebias']:.15g} v(bbin)=3 v(ref)=3\n"
    if c.get('output_nodeset'):
        net+='.nodeset v(bbo)=3 v(neg)=3\n'
    if c.get('output_ic'):
        net+='.ic v(bbo)=3 v(neg)=3\n'
    net+=f'.include "{(WORK/"OPAx197.LIB").as_posix()}"\n.options method=trap reltol=1e-4 trtol=3 temp=27\n.end\n'
    src=HERE/'netlists'/(name+'_source.cir');fixed(src,net.encode());fixed(WORK/src.name,src.read_bytes())
    wrapper=f'''* Integrated RF+BAT85+OPA197, normal operating condition only.
* source_sha256={sha(src)}
* model_sha256={sha(MODEL)}
.control
set ngbehavior=ps
source {(WORK/src.name).as_posix()}
set filetype=binary
set num_threads=1
save {SAVES} v(bbin) v(ref) v(bbo) v(final)
tran {c['step']}n {c['stop']}u {c['start']}u {c['step']}n
write @RAW@
quit
.endc
.end
'''
    d,r=execute(name,wrapper,c);r['metrics']=measure(d,c)
    r['dependencies']=dict(source_sha256=sha(src),model_sha256=sha(MODEL))
    save(r);print(json.dumps(dict(name=name,final=r['metrics']['nodes']['final'])),flush=True)

def main():
    # Original full chain: prove the final op-amp is not the small-blocker cause.
    run('F_R2_clean')
    for f in [29e6,33e6]:run(f'F_R2_{int(f/1e6)}_10',blockers=[[f,.01,0]])
    for duty in [.1,.5]:
        run(f'F_B_E1_square{duty*100:g}',variant='B_E1',wave='square',duty=duty)
    kw=dict(front_file=str(HERE/'filters/A2M_r1M.cir'))
    for duty in [.1,.5]:
        run(f'F_A2M_square{duty*100:g}',**kw,wave='square',duty=duty)
    # G=22 exploratory attempts did not establish the intended normal bias.
    # Their arrays/logs remain archived; main deliberately does not retry them.

if __name__=='__main__':main()
