source D:/ms_xsp/stage3_acceptance/s0304/L0_plain.cir
begin-scope page Transient Analysis
save $out
tran 1u 5m 0 5m uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/L0_plain.raw"
end-scope
