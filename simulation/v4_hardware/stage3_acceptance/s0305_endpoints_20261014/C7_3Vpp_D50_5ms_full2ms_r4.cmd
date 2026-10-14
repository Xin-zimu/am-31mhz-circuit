source D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014/C7_3Vpp_D50_5ms_full2ms_r4.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 2n 2m 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014/C7_3Vpp_D50_5ms_full2ms_r4.raw"
end-scope
