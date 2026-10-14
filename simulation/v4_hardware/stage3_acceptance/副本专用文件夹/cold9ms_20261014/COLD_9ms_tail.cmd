source D:/ms_xsp/stage3_acceptance/s0304_cold9ms_20261014/COLD_9ms_tail.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 9m 8.5m 1n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304_cold9ms_20261014/COLD_9ms_tail.raw"
end-scope
