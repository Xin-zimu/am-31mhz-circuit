source D:/ms_xsp/stage3_acceptance/s0304/R3_set_loose.cir
begin-scope page Transient Analysis
save $out
set reltol = 0.1
set trtol = 20
tran 1u 200u 0 10u uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/R3_set_loose.raw"
end-scope
