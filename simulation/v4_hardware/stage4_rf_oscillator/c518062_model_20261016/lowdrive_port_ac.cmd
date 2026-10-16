source D:/ms_xsp/s04_c518062_20261016/lowdrive_port_ac.cir
begin-scope page AC Analysis
save $base
iplot $base
ac lin 4001 30.98meg 31.02meg
write-and-destroy-iplot "D:/ms_xsp/s04_c518062_20261016/lowdrive_port_ac.raw"
end-scope
