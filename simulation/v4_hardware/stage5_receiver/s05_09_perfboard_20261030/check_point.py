"""S05-09: where can a scope probe actually be attached at 31 MHz?

The intuitive answer ("measure at the emitter-follower output, its 1 kOhm swamps
the probe") is WRONG and this script shows why: 1 kOhm in parallel with 10 pF is
a pole at 15.9 MHz, i.e. below the signal. The numbers below are computed, not
assumed, and the conclusion is that a passive probe cannot measure this filter
correctly at either node.
"""
from pathlib import Path
import json, sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'lc_parts_20261030'))
import lc_parts as LP

HERE = Path(__file__).resolve().parent
PARTS = Path(__file__).resolve().parents[1]/'lc_parts_20261030'
AC = json.loads((PARTS/'ac_cases.json').read_text(encoding='utf-8'))
NOM = next(r for r in AC if r['name'] == 'NOM_132')['parameters']
n = LP.LoadedNetwork()

# Node impedances taken from the netlists, not guessed:
#   tank nodes : 460 nH || (40.6 / 46.1 pF) -> a few kOhm, resonant
#   rf node    : RRF = 1 kOhm to ground (A2 / S05-08 fixtures)
RF_R = 1000.0


def buffered_metrics(pf):
    """Full metrics seen THROUGH a 1 kOhm || C_probe pole at the rf node."""
    h, z = LP.response(n, NOM)
    if pf:
        w = 2*np.pi*LP.FGRID
        pole = 1/(1 + 1j*w*RF_R*pf*1e-12)
        h = h*pole
    return LP.metrics(LP.FGRID, h, z)


def buffered(pf):
    """Droop at the rf node from 1 kOhm || C_probe, relative to no probe."""
    if not pf:
        return dict(probe_pf=0.0, pole_hz=float('inf'), droop_db=0.0,
                    slope_db_per_mhz=0.0)
    corner = 1/(2*np.pi*RF_R*pf*1e-12)
    # asymptotic 6 dB/octave: the reading is frequency dependent, which is what
    # corrupts a relative-suppression measurement.
    droop = -10*np.log10(1+(31e6/corner)**2)
    d29 = -10*np.log10(1+(29e6/corner)**2)
    d33 = -10*np.log10(1+(33e6/corner)**2)
    return dict(probe_pf=pf, pole_hz=corner, droop_db=droop,
                slope_db_per_mhz=(d33-d29)/4.0,
                distortion_29_vs_31_db=(d29-droop),
                distortion_33_vs_31_db=(d33-droop))


def tank(pf):
    """Same probe capacitance directly on tank2, which is what a careless
    'just clip it on the coil' measurement does."""
    p = dict(NOM)
    p['board2'] = NOM['board2'] + pf
    h, z = LP.response(n, p)
    m = LP.metrics(n.f, h, z)
    return dict(probe_pf=pf, center=m['center_edges_mhz'], bw=m['bw_mhz'],
                gain31=m['gain31_v_v'], d29=m['relative29_db'],
                d33=m['relative33_db'])


base_tank = tank(0.0)
rows = []
for pf in (1.0, 3.0, 10.0, 15.0):
    b = buffered(pf)
    bm = buffered_metrics(pf)
    t = tank(pf)
    rows.append(dict(
        probe_pf=pf, buffered_node=b, buffered_metrics=bm, tank_node=t,
        buffered_bw_error_pct=100*(bm['bw_mhz']-base_tank['bw'])/base_tank['bw'],
        buffered_center_error_mhz=bm['center_edges_mhz']-base_tank['center'],
        tank_center_error_mhz=t['center']-base_tank['center'],
        tank_bw_error_pct=100*(t['bw']-base_tank['bw'])/base_tank['bw'],
        tank_suppression_error_db_29=t['d29']-base_tank['d29']))

out = dict(
    baseline_tank=base_tank,
    rows=rows,
    verdict=('the two nodes are not equally usable and the difference is the whole '
             'point. A tank node is disqualified: 10 pF of probe moves the centre by '
             '1.49 MHz, the bandwidth by 22 % and the 29 MHz relative suppression by '
             '+17 dB, so the measurement would destroy the thing it measures. The '
             'buffered rf node is conditionally usable: the same 10 pF probe pulls it '
             '6.81 dB down at 31 MHz, but because that is a smooth 1 kOhm||C pole the '
             'bandwidth error is only +1.5 % and the 29-vs-31 MHz relative error is '
             '0.45 dB. So shape and relative suppression survive at the buffered node; '
             'ABSOLUTE amplitude does not, and must be corrected or reported as a '
             'relative quantity only.'),
    absolute_vs_relative=('do not quote a measured Vpp or gain in dB from a passive '
                          'probe at the buffered node without stating the droop. With a '
                          '10 pF probe the honest number at 31 MHz is 6.81 dB below the '
                          'true value; with a 3 pF probe it is 1.28 dB.'),
    what_changes_the_answer=[
        'an active probe at 1-3 pF: droop falls to 0.16-1.28 dB and the relative '
        'error to 0.02-0.14 dB, which makes the absolute reading defensible too',
        'a dedicated on-board test buffer with a 50 Ohm output driven into a 50 Ohm '
        'scope input; this is a measurement fixture and must be documented as such, '
        'never counted as part of the receiver',
        'a spectrum analyser or VNA with a high-impedance probe, which avoids the '
        'problem but is equipment the project does not have',
    ],
    honest_note=('this replaces an earlier draft conclusion in this same script that '
                 'claimed the buffered node was safe. The computed pole shows it is not; '
                 'the claim was withdrawn before it reached the report.'),
)
json.dump(out, open(HERE/'measurement_point.json', 'w', encoding='utf-8'), indent=2)

print('%-6s | %-34s | %s' % ('C/pF', 'buffered rf node', 'tank2 node'))
print('%-6s | %8s %9s %8s %8s | %8s %8s' %
      ('', 'pole/MHz', 'droop@31', 'BWerr%', '29v31', 'ctrErr', 'BWerr%'))
for r in rows:
    b, t = r['buffered_node'], r['tank_node']
    print('%-6.1f | %8.1f %9.2f %+8.1f %8.2f | %+8.3f %+8.1f' %
          (r['probe_pf'], b['pole_hz']/1e6, b['droop_db'],
           r['buffered_bw_error_pct'], b['distortion_29_vs_31_db'],
           r['tank_center_error_mhz'], r['tank_bw_error_pct']))
print()
print('baseline tank: centre %.4f MHz, BW %.4f MHz, 29/33 %.2f/%.2f dB'
      % (base_tank['center'], base_tank['bw'], base_tank['d29'], base_tank['d33']))
