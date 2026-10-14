source D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014/C3_4Vpp_D10_2ms.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set trtol = 1
set reltol = 0.0001
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 2n 2m 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014/C3_4Vpp_D10_2ms.raw"
end-scope
