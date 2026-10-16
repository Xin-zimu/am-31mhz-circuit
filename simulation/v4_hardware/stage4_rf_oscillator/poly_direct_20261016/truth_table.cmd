source D:/ms_xsp/s04_poly_20261016/truth_table.cir
begin-scope page Transient Analysis
save $y0 $y1 $y2 $y3 $y4 $y5 $y6 $y7 $y8 $y9 $y10 $y11 $p2 $p6 $yf
iplot $y0 $y1 $y2 $y3 $y4 $y5 $y6 $y7 $y8 $y9 $y10 $y11 $p2 $p6 $yf
tran 1n 20n 0 1n
write-and-destroy-iplot "D:/ms_xsp/s04_poly_20261016/truth_table.raw"
end-scope
