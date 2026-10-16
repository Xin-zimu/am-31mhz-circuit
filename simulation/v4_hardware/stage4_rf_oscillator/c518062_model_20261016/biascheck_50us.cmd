source D:/ms_xsp/s04_c518062_20261016/biascheck_50us.cir
begin-scope page Transient Analysis
save $vcc $base $emit $isupply $imotional
iplot $vcc $base $emit $isupply $imotional
tran 2.0n 50.0u 0u 2.0n uic
write-and-destroy-iplot "D:/ms_xsp/s04_c518062_20261016/biascheck_50us.raw"
end-scope
