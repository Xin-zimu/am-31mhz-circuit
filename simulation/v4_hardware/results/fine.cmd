source D:\ms_xsp\v4_lm393\LM393_20k_D10_A1.cir
begin-scope page Transient Analysis
set reltol = 0.0001
checknodes 3
save $v1 $ramp $pwm_raw $osc $hyst $duty
iplot $v1 $ramp $pwm_raw $osc $hyst $duty
set trtol = 1
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 50n 1.5m 0 50n
write-and-destroy-iplot "D:\ms_xsp\v4_lm393\LM393_20k_D10_A1.raw"
end-scope
source D:\ms_xsp\v4_lm393\LM393_20k_D10_A4.cir
begin-scope page Transient Analysis
set reltol = 0.0001
checknodes 3
save $v1 $ramp $pwm_raw $osc $hyst $duty
iplot $v1 $ramp $pwm_raw $osc $hyst $duty
set trtol = 1
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 50n 1.5m 0 50n
write-and-destroy-iplot "D:\ms_xsp\v4_lm393\LM393_20k_D10_A4.raw"
end-scope
source D:\ms_xsp\v4_lm393\LM393_20k_D50_A1.cir
begin-scope page Transient Analysis
set reltol = 0.0001
checknodes 3
save $v1 $ramp $pwm_raw $osc $hyst $duty
iplot $v1 $ramp $pwm_raw $osc $hyst $duty
set trtol = 1
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 50n 1.5m 0 50n
write-and-destroy-iplot "D:\ms_xsp\v4_lm393\LM393_20k_D50_A1.raw"
end-scope
source D:\ms_xsp\v4_lm393\LM393_20k_D50_A4.cir
begin-scope page Transient Analysis
set reltol = 0.0001
checknodes 3
save $v1 $ramp $pwm_raw $osc $hyst $duty
iplot $v1 $ramp $pwm_raw $osc $hyst $duty
set trtol = 1
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 50n 1.5m 0 50n
write-and-destroy-iplot "D:\ms_xsp\v4_lm393\LM393_20k_D50_A4.raw"
end-scope
source D:\ms_xsp\v4_lm393\AM_20k_31MHz_V4_Hardware.cir
begin-scope page Transient Analysis
set reltol = 0.0001
checknodes 3
save $v1 $ramp $pwm_raw $osc $hyst $duty $v2 $tp3 $tp6
iplot $v1 $ramp $pwm_raw $osc $hyst $duty $v2 $tp3 $tp6
set trtol = 1
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 2n 200u 0 2n
write-and-destroy-iplot "D:\ms_xsp\v4_lm393\AM_20k_31MHz_V4_Hardware.raw"
end-scope

