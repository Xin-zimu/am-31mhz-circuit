source D:/ms_xsp/stage3_acceptance/s0304/W_tmax500p_20u.cir
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
set itl4 = 500
set method = gear
tran 500p 20u 0 500p uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/W_tmax500p_20u.raw"
end-scope
