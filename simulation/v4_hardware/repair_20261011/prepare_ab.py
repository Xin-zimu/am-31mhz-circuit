from pathlib import Path
import re
H=Path(__file__).resolve().parent; W=Path('D:/ms_xsp/repair_20261011');W.mkdir(exist_ok=True)
s=(H/'baseline_actual.cir').read_text('ascii')
# Matched initialization: modify no active models or passive values.
s=s.replace('cC115 TP6 BB_IN 1e-08','cC115 TP6 BB_IN 1e-08 IC=-4.1')
s=s.replace('cC111 TP6 0 4.7e-11','cC111 TP6 0 4.7e-11 IC=0.43')
s=s.replace('cCBB V2_OP 0 1.32629e-10','cCBB V2_OP 0 1.32629e-10 IC=4.5')
for name in ['open_output','connected_output']:
 t=s
 if name=='connected_output':
  assert t.count('U2_OPA197_-EOPABOX_OPEN_7')==1
  t=t.replace('U2_OPA197_-EOPABOX_OPEN_7','BBO')
 (W/(name+'.cir')).write_text(t+'\n.end\n',encoding='ascii')
 signals='$v1 $tp6 $bb_in $bb_fb $bbo $v2'
 cmd=f'''source {W.as_posix()}/{name}.cir
begin-scope page Transient Analysis
checknodes 3
save {signals}
iplot {signals}
set trtol = 1
set reltol = 0.0001
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran -env-options 2n 200u 0 2n user_ic auto_tstep auto_tmax
write-and-destroy-iplot "{W.as_posix()}/{name}.raw"
end-scope
'''
 (W/(name+'.cmd')).write_text(cmd,encoding='ascii')
print(W)
