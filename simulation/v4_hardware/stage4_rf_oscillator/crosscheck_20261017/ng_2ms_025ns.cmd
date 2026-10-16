set filetype=binary
set num_threads=1
save v(vcc) v(base) v(emit) v(isupply) v(imotional)
tran 0.25n 2000.0u 1800.0u 0.25n uic
write D:/ms_xsp/s04_crosscheck_20261017/ng_2ms_025ns.raw
quit
