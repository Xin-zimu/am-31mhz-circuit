source D:/ms_xsp/s04_c518062_20261016/lowdrive_500us_fine_b2.cir
begin-scope page Transient Analysis
save $vcc $base $emit $isupply $imotional
iplot $vcc $base $emit $isupply $imotional
tran 0.125n 500.0u 400.0u 0.125n uic
write-and-destroy-iplot "D:/ms_xsp/s04_c518062_20261016/lowdrive_500us_fine_b2.raw"
end-scope
