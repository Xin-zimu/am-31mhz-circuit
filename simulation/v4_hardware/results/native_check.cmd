source D:\ms_xsp\v4_lm393\native_stage1_export.cir
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
write-and-destroy-iplot "D:\ms_xsp\v4_lm393\native_stage1_export.raw"
end-scope
