source D:/ms_xsp/stage3_acceptance/s0304/L_7ms_1ns.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 7m 0 1n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/L_7ms_1ns.raw"
end-scope
