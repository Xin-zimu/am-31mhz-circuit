source D:/ms_xsp/stage3_acceptance/s0304_final2_20261014/COLD_12ms_clean.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 12m 11.5m 1n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304_final2_20261014/COLD_12ms_clean.raw"
end-scope
