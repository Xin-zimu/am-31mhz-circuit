source D:/ms_xsp/stage3_acceptance/s0304/T6_opt_rshunt1.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 2n 500n 0 100n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/T6_opt_rshunt1.raw"
end-scope
