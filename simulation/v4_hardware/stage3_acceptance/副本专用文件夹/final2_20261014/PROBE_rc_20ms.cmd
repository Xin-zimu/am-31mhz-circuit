source D:/ms_xsp/stage3_acceptance/s0304_final2_20261014/PROBE_rc_20ms.cir
begin-scope page Transient Analysis
save $out
iplot $out
tran 1u 20m 0 1u uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304_final2_20261014/PROBE_rc_20ms.raw"
end-scope
