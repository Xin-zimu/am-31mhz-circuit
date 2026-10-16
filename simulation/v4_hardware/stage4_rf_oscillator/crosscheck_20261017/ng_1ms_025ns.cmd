set filetype=binary
set num_threads=1
save v(vcc) v(base) v(emit) v(isupply) v(imotional)
tran 0.25n 1000u 900u 0.25n uic
write D:/ms_xsp/s04_crosscheck_20261017/ng_1ms_025ns.raw
quit
