"""Coilcraft 1812CS series: manufacturer lumped-element (SPICE) models, Document 158.

Provenance
----------
Coilcraft Document 158 gives, for every part, the four model elements
R1, R2, C(pF), L(uH) plus the skin-effect coefficient k, and states the
"upper frequency limit" of the fit.  The schematic is

    R2 --- [ (Rskin + jwL) || (R1 + 1/(jwC)) ]

with Rskin = k * sqrt(f).  The model is derived from *de-embedded*
measurements fitted to the *average* of measured parts: it is a TYPICAL
model, NOT a guaranteed limit.  Document 158 itself warns that a mounted
part's SRF will be lower than the model's.

What this module does NOT do
----------------------------
It does not try to split the resulting ESR into "skin", "proximity" and
"core" percentages.  R2 is the DC resistance, Rskin is a fitted
frequency-dependent term and (R1||C) is a fitted loss/self-capacitance
branch; the element values were chosen to reproduce the measured
two-port behaviour as a whole, and Document 158 says explicitly that
"individual elements of the model are not determined by parameter
measurement".  Any per-mechanism split would therefore be an artefact of
the fit, not a measurement.  Likewise, Q is NOT the objective: Q=X/R
grows with L even when R grows faster, so a higher-Q part can have a
higher ESR.  The objective used throughout is R31 (ESR at 31 MHz).
"""
import math

DOC158_SOURCE = ("Coilcraft Document 158, 'SPICE Model for Coilcraft 1812CS Chip "
                 "Inductors', Rev 03/16/09, Table on p.2 and 'upper limit' column")

# Part -> Document 158 model elements.  limit_MHz = upper frequency limit of the fit.
PARTS = {
    '1812CS-222': dict(R1=80.0,  R2=2.2, Cp_pF=0.150, L_uH=2.250,  k=8.60e-4, limit_MHz=310),
    '1812CS-272': dict(R1=68.0,  R2=3.2, Cp_pF=0.123, L_uH=2.700,  k=9.80e-4, limit_MHz=310),
    '1812CS-332': dict(R1=81.0,  R2=3.8, Cp_pF=0.120, L_uH=3.330,  k=1.12e-3, limit_MHz=260),
    '1812CS-392': dict(R1=121.0, R2=5.0, Cp_pF=0.118, L_uH=3.950,  k=1.12e-3, limit_MHz=240),
    '1812CS-472': dict(R1=85.0,  R2=5.4, Cp_pF=0.122, L_uH=4.775,  k=1.80e-3, limit_MHz=220),
    '1812CS-562': dict(R1=198.0, R2=5.7, Cp_pF=0.165, L_uH=5.700,  k=2.01e-3, limit_MHz=190),
    '1812CS-682': dict(R1=203.0, R2=6.6, Cp_pF=0.166, L_uH=6.800,  k=2.58e-3, limit_MHz=170),
}

# The three parts the previous round actually compared.
COMPARE = ('1812CS-332', '1812CS-392', '1812CS-472')

F31 = 31e6
W31 = 2 * math.pi * F31


def _elements(part, loss_scale=1.0):
    p = PARTS[part]
    return (p['R1'], p['R2'], p['Cp_pF'] * 1e-12, p['L_uH'] * 1e-6, p['k'], loss_scale)


def z(part, f=F31, loss_scale=1.0, extra_C_pF=0.0):
    """Complex impedance of the part at frequency f [Hz].

    loss_scale multiplies both R1/R2 and the skin term; it is how the
    "what if the real part is worse than the typical model" corners are
    generated (the previous round used the same construct).
    """
    R1, R2, Cp, L, k, s = _elements(part, loss_scale)
    w = 2 * math.pi * f
    zskin = k * math.sqrt(f) * s
    zpar_branch = 1.0 / (1.0 / (zskin + 1j * w * L) + 1.0 / (R1 + 1.0 / (1j * w * Cp)))
    ztot = R2 * s + zpar_branch
    if extra_C_pF:
        ztot = 1.0 / (1.0 / ztot + 1j * w * extra_C_pF * 1e-12)
    return ztot


def describe(part, f=F31, loss_scale=1.0):
    zz = z(part, f, loss_scale)
    p = PARTS[part]
    w = 2 * math.pi * f
    pF = 1e12
    return dict(
        part=part,
        L_nominal_uH=p['L_uH'],
        L_effective_uH=zz.imag / w * 1e6,      # Im(Z)/(2*pi*f)
        R_esr_ohm=zz.real,
        X_ohm=zz.imag,
        Q=zz.imag / zz.real,                    # Im/Re at the same frequency
        Q_note='Q = X(31MHz)/R(31MHz) of the manufacturer TYPICAL model',
        DCR_R2_ohm=p['R2'],
        R1_ohm=p['R1'],
        Cp_pF=p['Cp_pF'],
        k=p['k'],
        upper_limit_MHz=p['limit_MHz'],
        Rskin_at_31MHz_ohm=p['k'] * math.sqrt(f) * loss_scale,
        X_over_wL=-1.0,
        model_source=DOC158_SOURCE,
        kind='typical_model_not_guaranteed',
    )


def reactance_needed_by_coil(part, length_cm):
    """Not used directly; the joint model computes the tuning."""
    raise NotImplementedError
