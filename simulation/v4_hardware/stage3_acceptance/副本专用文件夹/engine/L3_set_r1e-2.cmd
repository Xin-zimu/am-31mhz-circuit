source D:/ms_xsp/stage3_acceptance/s0304/L3_set_r1e-2.cir
begin-scope page Transient Analysis
save $out
set reltol = 0.01
tran 1u 5m 0 5m uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/L3_set_r1e-2.raw"
end-scope
