set filetype=binary
set num_threads=1
save v(vcc) v(base) v(emit) v(isupply) v(imotional)
tran 0.03125n 3000.0u 2900.0u 0.03125n uic
write D:/ms_xsp/s04_crosscheck_20261017/ng_3ms_003125ns.raw
quit
