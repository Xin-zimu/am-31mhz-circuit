source D:/ms_xsp/s04_c518062_20261016/reproduce_1ms_20261017_a.cir
begin-scope page Transient Analysis
save $vcc $base $emit $isupply $imotional
iplot $vcc $base $emit $isupply $imotional
tran 0.25n 1000.0u 900.0u 0.25n uic
write-and-destroy-iplot "D:/ms_xsp/s04_c518062_20261016/reproduce_1ms_20261017_a.raw"
end-scope
