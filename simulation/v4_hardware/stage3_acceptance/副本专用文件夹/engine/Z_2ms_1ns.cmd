source D:/ms_xsp/stage3_acceptance/s0304/Z_2ms_1ns.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
set suposc
set trtol = 1
set reltol = 0.0001
set itl4 = 100
tran 1n 2m 0 1n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/Z_2ms_1ns.raw"
end-scope
