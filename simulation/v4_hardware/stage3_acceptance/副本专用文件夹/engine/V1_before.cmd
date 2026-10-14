set reltol = 0.0001
set trtol = 1
set itl4 = 500
set method = gear
source D:/ms_xsp/stage3_acceptance/s0304/V1_before.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 2n 2u 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/V1_before.raw"
end-scope
