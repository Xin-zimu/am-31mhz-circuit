source D:/ms_xsp/stage3_acceptance/s0304/T4_set_loose.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set reltol = 0.1
tran 2n 500n 0 100n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/T4_set_loose.raw"
end-scope
