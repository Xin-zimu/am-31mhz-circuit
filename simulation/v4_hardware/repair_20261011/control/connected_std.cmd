source D:/ms_xsp/repair_20261011/connected_output.cir
begin-scope page Transient Analysis
checknodes 3
save $v1 $tp6 $bb_in $bb_fb $bbo $v2
iplot $v1 $tp6 $bb_in $bb_fb $bbo $v2
set trtol = 1
set reltol = 0.0001
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 2n 200u 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/repair_20261011/connected_output.raw"
end-scope
