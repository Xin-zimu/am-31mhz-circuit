source D:/ms_xsp/s04_c518062_20261016/lowdrive_2ms_retry.cir
begin-scope page Transient Analysis
save $vcc $base $emit $isupply $imotional
iplot $vcc $base $emit $isupply $imotional
tran 0.25n 2000.0u 1900.0u 0.25n uic
write-and-destroy-iplot "D:/ms_xsp/s04_c518062_20261016/lowdrive_2ms_retry.raw"
end-scope
