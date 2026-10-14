source D:/ms_xsp/stage3_acceptance/s0304/M_1n_1008p.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 1n 2u 0 1.008e-9 uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/M_1n_1008p.raw"
end-scope
