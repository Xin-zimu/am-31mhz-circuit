source D:/ms_xsp/stage3_acceptance/s0304/S2_opt_tight.cir
begin-scope page Transient Analysis
save $out
tran 1u 200u 0 10u uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/S2_opt_tight.raw"
end-scope
