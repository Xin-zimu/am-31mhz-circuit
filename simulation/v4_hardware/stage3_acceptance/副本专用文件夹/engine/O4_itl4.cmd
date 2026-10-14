source D:/ms_xsp/stage3_acceptance/s0304/O4_itl4.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 2n 2u 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/O4_itl4.raw"
end-scope
