source D:/ms_xsp/stage3_acceptance/s0304/I_chgtol.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
set suposc
set chgtol = 1e-18
set trtol = 1
set reltol = 0.0001
set itl4 = 500
set method = gear
tran 2n 20u 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/I_chgtol.raw"
end-scope
