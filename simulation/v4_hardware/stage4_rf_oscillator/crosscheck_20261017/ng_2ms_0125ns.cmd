set filetype=binary
set num_threads=1
save v(vcc) v(base) v(emit) v(isupply) v(imotional)
tran 0.125n 2000.0u 1900.0u 0.125n uic
write D:/ms_xsp/s04_crosscheck_20261017/ng_2ms_0125ns.raw
quit
