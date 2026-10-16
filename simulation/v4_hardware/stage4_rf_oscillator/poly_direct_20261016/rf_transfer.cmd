source D:/ms_xsp/s04_poly_20261016/rf_transfer.cir
begin-scope page Transient Analysis
save $c $ch $m $y $yh
iplot $c $ch $m $y $yh
tran .5n 50u 0 .5n
write-and-destroy-iplot "D:/ms_xsp/s04_poly_20261016/rf_transfer.raw"
end-scope
