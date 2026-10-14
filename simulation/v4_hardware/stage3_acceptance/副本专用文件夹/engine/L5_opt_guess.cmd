source D:/ms_xsp/stage3_acceptance/s0304/L5_opt_guess.cir
begin-scope page Transient Analysis
save $out
set reltol = 1e-2
tran 1u 5m 0 5m uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/L5_opt_guess.raw"
end-scope
