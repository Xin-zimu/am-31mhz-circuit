"""S05-08: purchasable-part LC models for the A + G22 receiver.

Every electrical parameter carries an evidence tag:
  'datasheet' - printed in the manufacturer document archived in sources/
  'derived'   - arithmetic on datasheet values (formula stated)
  'assumed'   - engineering assumption, NOT a manufacturer guarantee
  'fitted'    - fitted to a manufacturer model (1008CS only)

Amplifier/port extraction is reused unchanged from S05-07 (run_lc.py), which
itself reuses the archived C_Q50 raw. No historical file is rewritten.
"""
from pathlib import Path
import json, sys
import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
sys.path.insert(0, str(STAGE/'lc_realization_20261030'))
import run_lc as L                      # noqa: E402  (validated node solver)

LoadedNetwork = L.LoadedNetwork
metrics = L.metrics
FGRID = np.linspace(20e6, 44e6, 2401)   # same grid as the S05-07 AC sweeps
F_REF = 31e6

# ---------------------------------------------------------------- part data
# Coilcraft 132-17L, Document 114 (rev 10/29/13), archived as sources/coilcraft_132.pdf
#   row: 132-17L | L 460 nH +-5% | Qmin 66 @ test freq 25 MHz | SRFmin 340 MHz
#        DCRmax 43.1 mOhm | Irms 2.5 A | 17.5 turns AWG26 | A = 0.156 in
# Vishay IRF-24 (sources/vishay_irf24.pdf): 0.47 uH +-20%, Q>=40 @25.2 MHz,
#   SRF>=200 MHz, DCR<=0.17 Ohm.  Historical reference part.
PARTS = {
    '132-17L': dict(
        label='Coilcraft 132-17L', l_nh=460.0, tol=0.05, q_ref=66.0, f_ref=25.0e6,
        srf_mhz=340.0, dcr_ohm=0.0431,
        evidence=dict(
            l_nh='datasheet', tol='datasheet', q_ref='datasheet', f_ref='datasheet',
            srf_mhz='datasheet', dcr_ohm='datasheet',
            srf_to_cp='derived: Cp = 1/((2*pi*SRF)^2*L); upper bound, SRF is a minimum',
            q_law='assumed: R(f) = R25*(f/25MHz)**beta, beta in [0,1]',
            q31='derived: Q31 = 2*pi*31MHz*L/R(31MHz)',
            dcr_use='datasheet DCR is NOT used as RF loss: R(f) already comes from Q'),
        source='https://www.coilcraft.com/en-us/products/rf/air-core-inductors/maxi-spring/132/132-17/'),
    'IRF-24': dict(
        label='Vishay IRF-24 0.47 uH', l_nh=470.0, tol=0.20, q_ref=40.0, f_ref=25.2e6,
        srf_mhz=200.0, dcr_ohm=0.17,
        evidence=dict(l_nh='datasheet', tol='datasheet', q_ref='datasheet',
                      f_ref='datasheet', srf_mhz='datasheet', dcr_ohm='datasheet'),
        source='https://www.vishay.com/docs/34056/irf24.pdf'),
}

# Vishay BFC2 809 05.. film trimmer, Document 28529 rev 06-Sep-2024.
#   BFC280905003 = 2/18 pF: tan d <= 25e-4 at Cmax/100 MHz, min fres 360 MHz at
#   Cmax, TC -250 +-350 ppm/K, max 10 full 180 deg cycles.
#   Q at 31 MHz is NOT published; 1/tan d = 400 at 100 MHz is a floor there.
CT_MODEL = dict(
    cmin_pf=2.0, cmax_pf=18.0, q_range=(400.0, 1290.0),
    q_law='assumed: constant series R from tan d=25e-4 at 100 MHz -> Q in [400,1290] at 31 MHz',
    evidence=dict(cmin_pf='datasheet', cmax_pf='datasheet',
                  tand='datasheet: <= 25e-4 at Cmax, 100 MHz',
                  srf='datasheet: >= 360 MHz at Cmax (one trimmer alone)',
                  life='datasheet: max 10 full 180 deg cycles'),
    source='https://www.vishay.com/docs/28529/bfc280905.pdf')

# --------------------------------------------------------------- coil model
def coil_r(key, f, beta):
    """Series RF loss resistance from the datasheet Q at the datasheet test freq."""
    p = PARTS[key]
    r_ref = 2*np.pi*p['f_ref']*p['l_nh']*1e-9/p['q_ref']
    return r_ref*(np.asarray(f, dtype=float)/p['f_ref'])**beta


def coil_cp_pf(key):
    """Parallel self-capacitance implied by the datasheet SRF minimum (upper bound)."""
    p = PARTS[key]
    return 1/((2*np.pi*p['srf_mhz']*1e6)**2*p['l_nh']*1e-9)*1e12


def coil_z(f, key, L_nh, beta, q_force=None, cp_pf=None):
    """Series (R + jwL) in parallel with Cp.  Beta is ignored when q_force is set."""
    f = np.asarray(f, dtype=float)
    w = 2*np.pi*f
    L = L_nh*1e-9
    r = (coil_r(key, f, beta) if q_force is None
         else 2*np.pi*F_REF*L/q_force*np.ones_like(f))
    cp = (coil_cp_pf(key) if cp_pf is None else cp_pf)*1e-12
    return 1/(1/(r + 1j*w*L) + 1j*w*cp)


def series_r(f, p, i):
    """Series loss used for tank i: explicit Q31 override, else the beta law."""
    L = p[f'l{i}']*1e-9
    if p['q31'] is not None:
        return 2*np.pi*F_REF*L/p['q31']*np.ones_like(np.asarray(f, dtype=float))
    return coil_r(p['part'], f, p['beta'])


def q_at(f, key, L_nh, beta, q_force=None):
    z = coil_z(f, key, L_nh, beta, q_force)
    return float(np.imag(z)/np.real(z))


# ------------------------------------------------------- network with parts
def default_params(**kw):
    """S05-07 standard-value fixture restated as a physically buildable board."""
    p = dict(l1=460.0, l2=460.0, cs=15.0, co=11.0, ck=2.4,
             ct1=40.37920912906399, ct2=46.31557312225309,
             part='132-17L', beta=0.5, q31=None,
             board1=1.0, board2=1.0, cp1=None, cp2=None,
             ct_q=None, rs=50.0)
    p.update(kw)
    return p


def _ct_admittance(w, c_pf, q):
    """Trimmer as a lossy capacitor: same series-loss convention as the coil."""
    if q is None or c_pf <= 0:
        return 1j*w*c_pf*1e-12
    c = c_pf*1e-12
    r = 1/(2*np.pi*F_REF*c*q)
    return 1/(r + 1/(1j*w*c))


def response(n, p, f=None, k=0.0, frozen_r=True):
    """Modified nodal analysis, two coupled tanks plus the amplifier port.

    frozen_r=True  : tank series R held at its 31 MHz value across the sweep.
                     This is what every ngspice fixture in this stage does, so
                     analytic and SPICE results are then directly comparable.
    frozen_r=False : R follows the beta law across the sweep (analytic id only).

    k=0 with frozen_r=False reproduces run_lc's four-node solve (see audit).
    """
    f = FGRID if f is None else np.asarray(f, dtype=float)
    w = 2*np.pi*f
    yl = np.interp(f, n.f, n.yload)
    ha = np.interp(f, n.f, n.amp)
    N = 8
    y = np.zeros((len(f), N, N), dtype=complex)
    b = np.zeros((len(f), N), dtype=complex)
    y[:, 0, 0] += 1/p['rs']; b[:, 0] = 1/p['rs']

    def cap(a, c, cv):
        v = 1j*w*cv*1e-12
        y[:, a, a] += v; y[:, c, c] += v; y[:, a, c] -= v; y[:, c, a] -= v

    cap(0, 1, p['cs']); cap(1, 2, p['ck']); cap(2, 3, p['co'])
    L, R = [], []
    for i in (1, 2):
        Li = p[f'l{i}']*1e-9
        L.append(Li)
        R.append(series_r(F_REF if frozen_r else f, p, i))
        cp = coil_cp_pf(p['part']) if p.get(f'cp{i}') is None else p[f'cp{i}']
        y[:, i, i] += 1j*w*cp*1e-12
        y[:, i, i] += _ct_admittance(w, p[f'ct{i}']+p[f'board{i}'], p['ct_q'])
    y[:, 3, 3] += yl
    M = k*np.sqrt(L[0]*L[1])
    for i, (node, ln) in enumerate([(1, 4), (2, 5)]):
        g = 1/R[i]
        y[:, node, node] += g; y[:, ln, ln] += g
        y[:, node, ln] -= g; y[:, ln, node] -= g
    y[:, 4, 6] += 1; y[:, 6, 4] += 1
    y[:, 5, 7] += 1; y[:, 7, 5] += 1
    jw = 1j*w
    y[:, 6, 6] -= jw*L[0]; y[:, 6, 7] -= jw*M
    y[:, 7, 7] -= jw*L[1]; y[:, 7, 6] -= jw*M
    v = np.linalg.solve(y, b[..., None])[..., 0]
    z = p['rs']*v[:, 0]/(1-v[:, 0])
    return v[:, 3]*ha, z
