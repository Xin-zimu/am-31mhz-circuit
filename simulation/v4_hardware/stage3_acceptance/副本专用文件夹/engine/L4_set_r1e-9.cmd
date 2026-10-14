source D:/ms_xsp/stage3_acceptance/s0304/L4_set_r1e-9.cir
begin-scope page Transient Analysis
save $out
set reltol = 1e-09
tran 1u 5m 0 5m uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/L4_set_r1e-9.raw"
end-scope
