source D:/ms_xsp/stage3_acceptance/cold_engine_without_opa.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set trtol = 1
set reltol = 0.0001
set itl4 = 500
set method = gear
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 2n 20u 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/cold_engine_without_opa.raw"
end-scope
