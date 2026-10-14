from pathlib import Path
import re,shutil
HERE=Path(__file__).resolve().parent
WORK=Path('D:/ms_xsp/v4_lm393');WORK.mkdir(exist_ok=True)
model=(HERE/'models/LM393_TI.lib').read_text()
src=(HERE/'AM_20k_31MHz_V4_Hardware.cir').read_text()
src=re.sub(r'ECOMP1[^\n]*','XU1A HYST RAMP V5 0 OSC LM393_TI',src)
src=re.sub(r'ECOMP2[^\n]*','XU1B DUTY RAMP V5 0 PWM_RAW LM393_TI',src)
src=src.replace('.end',model+'\n.end')
(HERE/'AM_20k_31MHz_V4_Hardware.cir').write_text(src,encoding='ascii')
names=['LM393_20k_D10_A1','LM393_20k_D10_A4','LM393_20k_D50_A1','LM393_20k_D50_A4','AM_20k_31MHz_V4_Hardware']
commands=[]
for name in names:
    src=(HERE/(name+'.cir')).read_text()
    src='* '+src
    src=re.sub(r'^\.(save|tran|options).*\n','',src,flags=re.M|re.I)
    (WORK/(name+'.cir')).write_text(src,encoding='ascii')
    chain=name.startswith('AM_')
    signals='$v1 $ramp $pwm_raw $osc $hyst $duty'+(' $v2 $tp3 $tp6' if chain else '')
    stem=str(WORK/name)
    commands += [f'source {stem}.cir','begin-scope page Transient Analysis','checknodes 3',f'save {signals}',f'iplot {signals}',
      'set trtol = 7','set itl4 = 100','set convlimit','set rshunt = 1e+012','set dynamicdc','set inertialdelay',
      'tran -env-options '+('2n 200u 0 2n' if chain else '50n 1.5m 0 50n')+' auto_ic auto_tstep auto_tmax',
      f'write-and-destroy-iplot "{stem}.raw"','end-scope']
(WORK/'verify.cmd').write_text('\n'.join(commands)+'\n',encoding='ascii')
print(WORK/'verify.cmd')
