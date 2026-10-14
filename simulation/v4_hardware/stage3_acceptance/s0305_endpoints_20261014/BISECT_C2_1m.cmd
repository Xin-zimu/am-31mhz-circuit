source D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014/BISECT_C2_1m.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
tran 2n 1m 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014/BISECT_C2_1m.raw"
end-scope
