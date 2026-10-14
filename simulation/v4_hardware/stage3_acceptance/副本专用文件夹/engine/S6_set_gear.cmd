source D:/ms_xsp/stage3_acceptance/s0304/S6_set_gear.cir
begin-scope page Transient Analysis
save $out
set method = gear
tran 1u 200u 0 10u uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/s0304/S6_set_gear.raw"
end-scope
