source D:/ms_xsp/stage3_acceptance/s0304/R5_set_tmax.cir
begin-scope page Transient Analysis
save $out
set tmax = 1e-6
tran 1u 200u 0 10u uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/R5_set_tmax.raw"
end-scope
