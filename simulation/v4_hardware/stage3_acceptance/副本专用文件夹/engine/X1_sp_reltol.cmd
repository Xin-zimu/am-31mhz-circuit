source D:/ms_xsp/stage3_acceptance/s0304/X1_sp_reltol.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set reltol = 0.01
tran 2n 2u 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/X1_sp_reltol.raw"
end-scope
