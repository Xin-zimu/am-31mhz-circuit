# -*- coding: utf-8 -*-
"""C3 step 4: RLC reference circuits with exact analytic solutions.

Purpose: measure the *integrator's own* frequency error and numerical damping,
free of any active-device nonlinearity, at the same 31 MHz / high-Q operating
point as the crystal oscillator.

Two circuits, both linear, both with closed-form answers:

  A1 ring-down  parallel RLC, C pre-charged to V0, no source.
                v(t) = V0 e^(-a t) [cos(wd t) + (a/wd) sin(wd t)]
                a  = 1/(2RC),  w0 = 1/sqrt(LC),  wd = sqrt(w0^2 - a^2)
                -> frequency error from crossings, damping error from envelope

  A2 driven     same tank driven by a current source at exactly f0.
                At resonance the tank impedance is purely R, so the exact
                steady-state amplitude is I*R with zero phase.  Numerical
                damping shows up directly as a smaller steady-state amplitude,
                which is the linear analogue of the oscillator's amplitude error.

Nothing here is fitted: every reference number is computed from the element
values in closed form and cross-checked against a dense numerical solution of
the same ODE.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import c3lib as L

F0 = 30.992622e6          # crystal series resonance, same operating point as C2
W0 = 2 * np.pi * F0

CASES = [("Q50", 50.0), ("Q200", 200.0), ("Q1000", 1000.0)]
C_FIX = 100e-12


def tank(Q):
    """Return (L, R) for a parallel tank at F0 with capacitance C_FIX."""
    w0 = W0
    Lh = 1.0 / (w0 * w0 * C_FIX)
    R = Q / (w0 * C_FIX)
    return Lh, R


def exact_ringdown(Q, V0=1.0, t=None):
    Lh, R = tank(Q)
    a = 1.0 / (2 * R * C_FIX)
    w0 = 1.0 / np.sqrt(Lh * C_FIX)
    wd = np.sqrt(w0 * w0 - a * a)
    if t is None:
        return dict(a=a, w0=w0, wd=wd, f=wd / (2 * np.pi), L=Lh, R=R)
    # C pre-charged to V0 with i_L(0)=0  =>  v'(0) = -V0/(R C) = -2 a V0
    v = V0 * np.exp(-a * t) * (np.cos(wd * t) - (a / wd) * np.sin(wd * t))
    return v


def check_analytic():
    """Cross-check the closed form against a dense RK45 integration."""
    from scipy.integrate import solve_ivp
    out = []
    for nm, Q in CASES:
        Lh, R = tank(Q)
        e = exact_ringdown(Q)
        # state: v (voltage on C), i (current through L, downward)
        def rhs(t, y):
            v, i = y
            # node equation: C dv/dt + v/R + i = 0 ;  L di/dt = v
            return [(-v / R - i) / C_FIX, v / Lh]
        sol = solve_ivp(rhs, [0, 5e-6], [1.0, 0.0], rtol=1e-12, atol=1e-14,
                        method="DOP853", dense_output=True, max_step=1e-10)
        ts = np.linspace(0, 5e-6, 50001)
        vref = sol.sol(ts)[0]
        vclosed = exact_ringdown(Q, 1.0, ts)
        out.append(dict(case=nm, L_H=Lh, R_ohm=R, C_F=C_FIX,
                        f_exact_MHz=e["f"] / 1e6, alpha=e["a"], Q=Q,
                        max_abs_dev_V=float(np.max(np.abs(vref - vclosed)))))
    return out


def net_ringdown(name, Q, method, maxord, reltol, tmax, tstop, tstep=None, raw=None):
    Lh, R = tank(Q)
    tstep = tstep or tmax
    raw = raw or (name + ".raw")
    return "\n".join([
        "* C3 RLC reference A1: parallel tank ring-down, Q=" + str(Q),
        "* analytic: v(t)=V0 e^-at [cos(wd t)-(a/wd) sin(wd t)], v'(0)=-V0/(RC)",
        "C1 1 0 " + repr(C_FIX) + " ic=1",
        "L1 1 0 " + repr(Lh),
        "R1 1 0 " + repr(R),
        ".options method=" + method + " maxord=" + str(maxord) + " reltol=" + reltol +
        " trtol=7 temp=27 tnom=27",
        ".control",
        "set filetype=binary",
        "set num_threads=1",
        "save v(1)",
        "tran " + tstep + " " + tstop + " 0 " + tmax + " uic",
        "write " + raw,
        "quit",
        ".endc",
        ".end", ""])


def net_driven(name, Q, method, maxord, reltol, tmax, tstop, tstep=None, amp=10e-6, raw=None):
    Lh, R = tank(Q)
    tstep = tstep or tmax
    raw = raw or (name + ".raw")
    tdelay = 0.0
    return "\n".join([
        "* C3 RLC reference A2: parallel tank driven at f0 by a current source",
        "* analytic steady state at resonance: |v| = I*R, phase 0",
        "I1 0 1 SIN(0 " + repr(amp) + " " + repr(F0) + " 0 0 0)",
        "C1 1 0 " + repr(C_FIX),
        "L1 1 0 " + repr(Lh),
        "R1 1 0 " + repr(R),
        ".options method=" + method + " maxord=" + str(maxord) + " reltol=" + reltol +
        " trtol=7 temp=27 tnom=27",
        ".control",
        "set filetype=binary",
        "set num_threads=1",
        "save v(1)",
        "tran " + tstep + " " + tstop + " 0 " + tmax,
        "write " + raw,
        "quit",
        ".endc",
        ".end", ""])


def analyse_ringdown(path, Q):
    d = L.read_raw(path)
    t, v = d["time"], d["v(1)"]
    e = exact_ringdown(Q)
    # frequency from rising crossings at zero (the analytic curve crosses 0 too)
    tc = L.crossings(t, v, 0.0)
    f_sim, resid = L.fit_frequency(tc)
    # envelope: peak of each half cycle, fitted for the decay rate
    d_ = v - 0.0
    idx = np.nonzero((d_[:-1] >= 0) & (d_[1:] < 0))[0]
    if idx.size < 10:
        return dict(ok=False, reason="too few cycles")
    tp = t[idx]
    vp = v[idx]
    m = (tp > 0.15 * t[-1]) & (vp > 0)
    if m.sum() < 8:
        return dict(ok=False, reason="too few peaks in fit window")
    slope = np.polyfit(tp[m], np.log(vp[m]), 1)
    a_sim = -float(slope[0])
    return dict(ok=True, f_sim_MHz=f_sim / 1e6, f_exact_MHz=e["f"] / 1e6,
                df_ppm=(f_sim - e["f"]) / e["f"] * 1e6,
                alpha_sim=a_sim, alpha_exact=e["a"],
                dalpha_pct=(a_sim - e["a"]) / e["a"] * 100.0,
                Q_sim=e["w0"] / (2 * a_sim),
                resid_s=resid, n_peaks=int(m.sum()),
                v_start=float(vp[0]), v_end=float(vp[-1]))


def analyse_driven(path, Q, amp=10e-6):
    """Steady-state amplitude of the driven tank.

    IMPORTANT: the fit frequency must be the SIMULATED frequency, not the
    analytic one.  At Q=17118 a 200 ppm frequency offset accumulates 7 full
    cycles of phase error over a 1.2 ms window, which collapses a fixed-
    frequency least-squares fit to noise and produced nonsense (-85% "error")
    in the first pass.  Amplitude is therefore taken as half the peak-to-peak
    of the settled waveform, with the fit used only as a cross-check.
    """
    d = L.read_raw(path)
    t, v = d["time"], d["v(1)"]
    Lh, R = tank(Q)
    v_exact = amp * R
    m = t > 0.7 * t[-1]
    tt, vv = t[m], v[m]
    f, _ = L.fit_frequency(L.crossings(tt, vv, 0.0))
    amp_pp = float(vv.max() - vv.min()) / 2.0
    A = np.vstack([np.ones_like(tt), np.cos(2 * np.pi * f * tt),
                   np.sin(2 * np.pi * f * tt)]).T
    coef, *_ = np.linalg.lstsq(A, vv, rcond=None)
    amp_fit = float(np.hypot(coef[1], coef[2]))
    phase = float(np.degrees(np.arctan2(-coef[2], coef[1])))
    resid = vv - A @ coef
    return dict(ok=True, amp_sim=amp_pp, amp_fit=amp_fit, amp_exact=v_exact,
                amp_err_pct=(amp_pp - v_exact) / v_exact * 100.0,
                phase_deg=phase, f_sim_MHz=f / 1e6,
                rms_resid=float(np.sqrt(np.mean(resid ** 2))),
                vpp=float(vv.max() - vv.min()))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "check":
        print(json.dumps(check_analytic(), ensure_ascii=False, indent=1))
