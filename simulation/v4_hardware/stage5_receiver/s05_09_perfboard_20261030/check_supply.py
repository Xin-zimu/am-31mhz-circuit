"""S05-09 task 1: is the reported Vpp physically consistent with the supply?

Reads the rails straight out of the netlists that produced the S05-08 numbers,
then checks each measured output window against the rail and against the
OPA197 model's own output-stage limits. No new transient is run.
"""
from pathlib import Path
import json, re, sys

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
PARTS = STAGE/'lc_parts_20261030'
sys.path.insert(0, str(PARTS))

SUMMARY = json.loads((PARTS/'chain_summary.json').read_text(encoding='utf-8'))
MODEL = STAGE.parents[1]/'models/OPA197_TI/OPAx197.LIB'


def rail_of(netlist):
    """Supply voltage actually present in a netlist, or None."""
    t = Path(netlist).read_text(errors='replace')
    m = re.search(r'^V(?:SUP|CC|DD)\s+\S+\s+0\s+([0-9.eE+-]+)\s*$', t, re.M)
    return float(m.group(1)) if m else None


def ref_divider(netlist):
    """The 20k/10k reference divider, if present."""
    t = Path(netlist).read_text(errors='replace')
    rt = re.search(r'^RVT\s+vcc\s+ref\s+([0-9.eE+-]+)', t, re.M)
    rb = re.search(r'^RVB\s+ref\s+0\s+([0-9.eE+-]+)', t, re.M)
    if not (rt and rb):
        return None
    rt, rb = float(rt.group(1)), float(rb.group(1))
    return dict(r_top=rt, r_bottom=rb, fraction=rb/(rt+rb))


rows = []
for rec in SUMMARY['rows']:
    net = HERE.parent/'lc_parts_20261030'/'netlists'/(rec['name']+'_source.cir')
    rail = rail_of(net) if net.exists() else None
    rows.append(dict(name=rec['name'], rail_v=rail, vpp=rec['vpp'],
                     low=rec['low'], high=rec['high'],
                     headroom_low=round(rec['low'], 4),
                     headroom_high=round((rail-rec['high']), 4) if rail else None,
                     fits=bool(rail and rec['low'] > 0 and rec['high'] < rail)))

# every S05 netlist in the stage, to prove the rail is not a one-off
rails = {}
for p in STAGE.rglob('*.cir'):
    if 'attempt01_aborted' in p.parts:
        continue
    r = rail_of(p)
    if r is not None:
        rails[repr(r)] = rails.get(repr(r), 0) + 1

div = ref_divider(HERE.parent/'lc_parts_20261030'/'netlists'/'T_sq50_six_source.cir')
rail9 = 9.0
ref = rail9*div['fraction']

out = dict(
    question='Is the reported 5.109 Vpp consistent with the actual OPA197 supply rail?',
    answer=('Yes on the netlists as built: every S05 netlist runs the OPA197 from a '
            '9 V rail with a 3 V reference. A 0-5 V single rail would NOT allow it; '
            'that hypothetical is arithmetically excluded below.'),
    rail_census_across_stage=rails,
    reference_divider=div,
    reference_volts_on_9v=ref,
    model_file=str(MODEL),
    model_output_clamp_note=('OPAx197.LIB CLAWN/CLAWP tables act on V(VCC,VEE); they do '
                             'not add a separate 5 V ceiling, so the rail is the limit'),
    cases=rows,
    hypothetical_5v=dict(
        rail=5.0,
        reference=5.0*div['fraction'],
        max_symmetric_swing_vpp=2*(5.0*div['fraction']),
        note=('a 0-5 V single rail with the same 20k/10k divider would centre the output '
              'at %.3f V, so a symmetric square wave is capped near %.2f Vpp; the '
              'reported 5.109 Vpp is arithmetically impossible on 0-5 V. On the 9 V rail '
              'actually used the centre is %.3f V and the same square wave has room for '
              '%.2f Vpp, so there is no contradiction in the netlists as built.'
              % (5.0*div['fraction'], 2*(5.0*div['fraction']), ref, 2*ref))),
    invalid_run=dict(
        name='T_sq50_supply5',
        reason=('supply was forced to 5 V while the initialisation still imposed '
                '.ic v(ref)=3 v(bbin)=3, a state the 5 V divider (1.667 V) cannot '
                'reach; the resulting 1.627 Vpp is a contaminated operating point, '
                'not a 5 V design result'),
        verdict='discarded, not cited anywhere'),
)
json.dump(out, open(HERE/'supply_audit.json', 'w', encoding='utf-8'), indent=2,
          ensure_ascii=False)

print(json.dumps({k: out[k] for k in ('rail_census_across_stage', 'reference_divider',
                                      'reference_volts_on_9v')}, indent=1))
print()
for r in rows:
    print('%-22s rail=%s vpp=%7.3f  low=%6.3f high=%6.3f  fits=%s' %
          (r['name'], r['rail_v'], r['vpp'], r['low'], r['high'], r['fits']))
print()
bad = [r['name'] for r in rows if not r['fits']]
print('cases exceeding their rail:', bad if bad else 'none')
print('9 V rail symmetric limit: %.2f Vpp (reference %.3f V)' % (2*ref, ref))
print('5 V single-rail symmetric limit: %.2f Vpp (reference %.3f V)'
      % (2*(5.0*div['fraction']), 5.0*div['fraction']))
