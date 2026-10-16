source D:/ms_xsp/s04_power_20261016/monitor_control.cir
begin-scope page Transient Analysis
save $v5 $imon
iplot $v5 $imon
tran 1n 20n 0 1n
write-and-destroy-iplot "D:/ms_xsp/s04_power_20261016/monitor_control.raw"
end-scope
