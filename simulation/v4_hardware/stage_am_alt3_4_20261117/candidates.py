"""AM-ALT.3.4 candidate matrix.

Baseline rule set (the conditions under which the three candidates are compared):

  * primary comparison length 90 cm for EVERY candidate;
  * secondary check at 100 cm for the shortlisted ones only;
  * RSENSE fixed at 10 ohm for every candidate, no exceptions;
  * each candidate retuned to 31 MHz on its own, including the loss and
    parasitics of whatever compensation element that retuning needs
    (1812CS-332 and -392 cannot be reached with the 2-18 pF trimmer alone,
    so they carry a parallel C0G; that part is counted, not ignored);
  * the frozen driver, supply, modulation and ground network are identical.

Roles:
  472 = historical control (the previous round's main pick)
  392 = primary baseline for this round
  332 = efficiency control
"""
import engine as e
import coilmodels as cm

PRIMARY_LEN = 90
SECONDARY_LEN = 100

# name -> (part, length, extra knobs)
BASE_CASES = [
    ('h90_472', '1812CS-472', 90, {}),
    ('h90_392', '1812CS-392', 90, {}),
    ('h90_332', '1812CS-332', 90, {}),
]

FAMILY_CASES = [
    ('h90_222', '1812CS-222', 90, {}),
    ('h90_272', '1812CS-272', 90, {}),
]

SECONDARY_CASES = [
    ('h100_472', '1812CS-472', 100, {}),
    ('h100_392', '1812CS-392', 100, {}),
    ('h100_332', '1812CS-332', 100, {}),
]

# Corners applied to the three principal candidates at 90 cm.
#
# The "datasheet floor" corner is NOT a single number: Coilcraft guarantees Q only
# at 50 MHz, and each part's typical model is optimistic by a different amount, so
# the loss scale that reproduces Qmin(50 MHz) is solved per part (1.26 for 472,
# 1.34 for 332, 1.36 for 392).  Reusing 472's factor on the other two would have
# understated their worst case.
import datasheet_corners as dsc

CORNER_CASES = []
for tag, part in [('472', '1812CS-472'), ('392', '1812CS-392'), ('332', '1812CS-332')]:
    qscale = dsc.loss_scale_for_q50(part)
    srfc = dsc.extra_C_for_srf(part)          # farads
    CORNER_CASES += [
        # inductance tolerance is NOT re-trimmed away: the trimmer is set once,
        # then the part is what it is.  These are detuning stresses.
        ('h90_%s_Lm5' % tag, part, 90, dict(coil_L_scale=0.95, retune=False)),
        ('h90_%s_Lp5' % tag, part, 90, dict(coil_L_scale=1.05, retune=False)),
        ('h90_%s_loss2' % tag, part, 90, dict(coil_loss_scale=2.0)),
        ('h90_%s_Qds' % tag, part, 90, dict(coil_loss_scale=qscale)),
        ('h90_%s_srf' % tag, part, 90, dict(coil_extra_C_pF=srfc)),
        ('h90_%s_ct2' % tag, part, 90, dict(contact=2.0)),
        ('h90_%s_cb2' % tag, part, 90, dict(cbase=2e-12)),
        # stray 0.5 pF left in place WITHOUT retuning: a real detuning stress
        # (≈32 ohm of residual reactance), not a parasitic that the trimmer absorbs
        ('h90_%s_cx5' % tag, part, 90, dict(coil_extra_C_pF=0.5e-12, retune=False)),
    ]


# How much room is left at all?  These cases are NOT hardware: they put the
# manufacturer's ESR at essentially zero (x1e-6) while keeping the reactance and
# the retuning, so they bound what any coil improvement could buy at this length.
# They answer "how much of the loss is still addressable" without pretending a
# lossless part exists.
CEILING_CASES = [
    ('h90_ceil472', '1812CS-472', 90, dict(coil_loss_scale=1e-6)),
    ('h90_ceil332', '1812CS-332', 90, dict(coil_loss_scale=1e-6)),
]


def make(cases):
    return [dict(name=n, part=p, length_cm=L, **kw) for n, p, L, kw in cases]


def analytic_table(lengths=(70, 80, 90, 100), parts=cm.PARTS):
    rows = []
    for part in parts:
        for L in lengths:
            try:
                d = e.design(L, part)
            except ValueError as exc:
                rows.append(dict(part=part, length_cm=L, buildable=False, reason=str(exc)))
                continue
            b = e.budget(d)
            n = d['cap']
            rows.append(dict(
                part=part, length_cm=L, buildable=True,
                C_total_pF=d['C_total_pF'], C_trim_pF=n['C_trim'] * 1e12,
                C_cog_pF=n['C_cog'] * 1e12, trim_only=n['trim_only'],
                extra_C0G_pF=n['extra_C0G_pF'],
                coil_ESR_ohm=d['coil_z'].real, coil_X31_ohm=d['coil_z'].imag,
                coil_Q31=d['coil_z'].imag / d['coil_z'].real,
                cap_R_ohm=d['cap_r'],
                port_R_with_10ohm=b['Rt'],
                R_ant_port=b['R_ant_port'], R_rad_port=b['R_rad_port'],
                eta_pct=100 * b['eta'],
            ))
    return rows
