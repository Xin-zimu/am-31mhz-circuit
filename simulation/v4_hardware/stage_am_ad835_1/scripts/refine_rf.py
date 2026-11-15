"""Focused interface refinement and signed-current sensitivity, not full AM."""
import rf_study as L
import concurrent.futures as cf
jobs=[('A470_nom',dict(top='A470',iy=10e-6,iz=50e-6)),
 ('A560_nom',dict(top='A560',iy=10e-6,iz=50e-6)),
 ('A470_AMB',dict(top='A470_AMB',iy=10e-6,iz=50e-6)),
 ('A470_stress_pp',dict(top='A470',iy=27e-6,iz=100e-6)),
 ('A470_stress_nn',dict(top='A470',iy=-27e-6,iz=-100e-6)),
 ('C_B_stress_pn',dict(top='C_B',iy=27e-6,iz=-100e-6)),
 ('C_B_stress_np',dict(top='C_B',iy=-27e-6,iz=100e-6))]
with cf.ThreadPoolExecutor(3) as pool:
    fs=[pool.submit(L.job,n,**k) for n,k in jobs]
    for f in cf.as_completed(fs):f.result()
