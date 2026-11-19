"""Datasheet-floor corners (Coilcraft Document 105 guarantee, not the typical model).

For every part the typical model is optimistic:
  * its Q at 50 MHz is HIGHER than the guaranteed minimum, so the real ESR at
    31 MHz can be worse than the model predicts;
  * its SRF is 1.64-1.81x HIGHER than the guaranteed minimum, i.e. the model
    under-states the effective shunt capacitance of a mounted part.

Both are corrected here, per part, so the three candidates are compared on the
same "worst credible" basis.  The correction is an EXTRAPOLATION: Coilcraft
guarantees Q only at 50 MHz, so the 31 MHz ESR produced by this scaling is a
stress corner, not a guarantee.
"""
import math

import coilmodels as cm

QMIN50 = {'1812CS-222': None, '1812CS-272': 63.0, '1812CS-332': 65.0,
          '1812CS-392': 69.0, '1812CS-472': 63.0, '1812CS-562': 59.0,
          '1812CS-682': None}
QMIN_DEFINITION_MHZ = 50.0
SRF_MIN_MHZ = {'1812CS-272': 160.0, '1812CS-332': 145.0, '1812CS-392': 130.0,
               '1812CS-472': 115.0, '1812CS-562': 100.0}


def loss_scale_for_q50(part, qmin50=QMIN50[None] if False else None):
    from scipy.optimize import brentq
    q = qmin50 if qmin50 is not None else QMIN50[part]
    if q is None:
        raise ValueError('no datasheet Q for ' + part)
    f = lambda s: cm.z(part, QMIN_DEFINITION_MHZ * 1e6, s).imag / \
                  cm.z(part, QMIN_DEFINITION_MHZ * 1e6, s).real - q
    return brentq(f, 1.0, 8.0)


def extra_C_for_srf(part):
    """Shunt capacitance that lowers the model SRF to the guaranteed minimum."""
    if part not in SRF_MIN_MHZ:
        return 0.0
    L = cm.PARTS[part]['L_uH'] * 1e-6
    Cp = cm.PARTS[part]['Cp_pF'] * 1e-12
    srf_model = 1 / (2 * math.pi * math.sqrt(L * Cp)) / 1e6
    srf_ds = SRF_MIN_MHZ[part]
    return Cp * ((srf_model / srf_ds) ** 2 - 1)


def corners(part):
    s = loss_scale_for_q50(part)
    return dict(part=part,
                loss_scale_qmin50=s,
                Q31_datasheet_floor=cm.z(part, 31e6, s).imag / cm.z(part, 31e6, s).real,
                ESR31_datasheet_floor_ohm=cm.z(part, 31e6, s).real,
                Q31_typical_model=cm.z(part, 31e6).imag / cm.z(part, 31e6).real,
                ESR31_typical_model_ohm=cm.z(part, 31e6).real,
                extra_C_pF_for_datasheet_SRF=extra_C_for_srf(part) * 1e12,
                Qmin50=QMIN50[part], SRF_min_MHz=SRF_MIN_MHZ.get(part))


if __name__ == '__main__':
    import json
    out = {p: corners(p) for p in cm.PARTS if QMIN50.get(p)}
    print(json.dumps(out, indent=2))
