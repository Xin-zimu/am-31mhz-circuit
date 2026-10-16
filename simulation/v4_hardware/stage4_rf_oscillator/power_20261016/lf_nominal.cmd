source D:/ms_xsp/s04_power_20261016/lf_nominal.cir
begin-scope page Transient Analysis
save $v5 $v1 $imon
iplot $v5 $v1 $imon
tran 10n 2m 0 10n uic
write-and-destroy-iplot "D:/ms_xsp/s04_power_20261016/lf_nominal.raw"
end-scope
