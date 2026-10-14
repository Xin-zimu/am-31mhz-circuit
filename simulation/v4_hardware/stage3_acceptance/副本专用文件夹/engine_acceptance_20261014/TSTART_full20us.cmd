source D:/ms_xsp/stage3_acceptance/s0304_acceptance_20261014/TSTART_full20us.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 20u 0 1n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304_acceptance_20261014/TSTART_full20us.raw"
end-scope
