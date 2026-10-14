source D:/ms_xsp/stage3_acceptance/s0304/S4_set_tight.cir
begin-scope page Transient Analysis
save $out
set reltol = 1e-9
set trtol = 0.1
tran 1u 200u 0 10u uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/S4_set_tight.raw"
end-scope
