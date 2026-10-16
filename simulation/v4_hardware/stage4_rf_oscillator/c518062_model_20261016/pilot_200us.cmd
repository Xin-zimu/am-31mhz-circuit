source D:/ms_xsp/s04_c518062_20261016/pilot_200us.cir
begin-scope page Transient Analysis
save $vcc $base $emit $isupply $imotional
iplot $vcc $base $emit $isupply $imotional
tran 0.5n 200u 0 0.5n uic
write-and-destroy-iplot "D:/ms_xsp/s04_c518062_20261016/pilot_200us.raw"
end-scope
