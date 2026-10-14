source D:/ms_xsp/stage3_acceptance/s0304/C_tight.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
set suposc
set trtol = 0.5
set reltol = 1e-06
set itl4 = 500
set method = gear
tran 2n 20u 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/C_tight.raw"
end-scope
