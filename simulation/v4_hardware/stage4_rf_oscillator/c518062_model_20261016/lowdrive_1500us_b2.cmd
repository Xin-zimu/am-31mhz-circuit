source D:/ms_xsp/s04_c518062_20261016/lowdrive_1500us_b2.cir
begin-scope page Transient Analysis
save $vcc $base $emit $isupply $imotional
iplot $vcc $base $emit $isupply $imotional
tran 0.25n 1500.0u 1400.0u 0.25n uic
write-and-destroy-iplot "D:/ms_xsp/s04_c518062_20261016/lowdrive_1500us_b2.raw"
end-scope
