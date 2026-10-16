source D:/ms_xsp/s04_poly_20261016/verified/rf_refined.cir
begin-scope page Transient Analysis
save $c $ch $m $y $yh
iplot $c $ch $m $y $yh
tran .25n 50u 0 .25n
write-and-destroy-iplot "D:/ms_xsp/s04_poly_20261016/verified/rf_refined.raw"
end-scope
