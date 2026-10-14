source D:/ms_xsp/stage3_acceptance/s0304/M_1n_10n.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 2u 0 10n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/M_1n_10n.raw"
end-scope
