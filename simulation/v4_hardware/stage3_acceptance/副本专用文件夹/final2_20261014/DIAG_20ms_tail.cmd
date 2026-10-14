source D:/ms_xsp/stage3_acceptance/s0304_final2_20261014/DIAG_20ms_tail.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 20m 19.5m 1n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304_final2_20261014/DIAG_20ms_tail.raw"
end-scope
