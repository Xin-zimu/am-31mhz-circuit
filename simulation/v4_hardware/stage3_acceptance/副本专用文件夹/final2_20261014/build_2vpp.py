"""Build the 2 Vpp precharged netlist CORRECTLY.

The earlier attempt applied each regex substitution to the ORIGINAL bytes, so
the first swap (rRVAT) was discarded and only rRVAB changed. Fix: apply both
substitutions sequentially and assert the final state of BOTH resistors.

Target (D=50%, from potentiometer_settings.csv):
    4 Vpp baseline (accepted): rRVAT=1847.93   rRVAB=18152.1
    2 Vpp target            : rRVAT=10905.544559  rRVAB=9094.455441
Receiver chain (RG_BB / RF_BB / RV_BB / RLOAD) must be byte-identical.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent.parent
SRC = STAGE / 'nominal_full.cir'
RUNTIME = Path(r'D:\ms_xsp\stage3_acceptance\s0304_final2_20261014')

base = SRC.read_bytes()
print('=' * 94)
print('SOURCE')
print('=' * 94)
print(f'  {SRC}')
print(f'  sha256 = {hashlib.sha256(base).hexdigest()}')

TARGET = {'rRVAT': b'10905.544559', 'rRVAB': b'9094.455441'}
EXPECT = {'rRVAT': b'1847.93', 'rRVAB': b'18152.1'}

net = base
print()
print('=' * 94)
print('APPLY SUBSTITUTIONS SEQUENTIALLY (this is what the first attempt got wrong)')
print('=' * 94)
for comp, new in TARGET.items():
    pat = rb'(?m)^(' + comp.encode() + rb'(\s+\S+\s+\S+\s+))(\S+)'
    m = re.search(pat, net)
    if not m:
        raise SystemExit(f'{comp} not found')
    current = m.group(3)
    print(f'  {comp:7s} before={current.decode():<20s} expected={EXPECT[comp].decode()}')
    if current != EXPECT[comp]:
        print(f'          NOTE: differs from the value I assumed; using the actual one')
    net, n = re.subn(pat, lambda mm: mm.group(1) + new, net)
    if n != 1:
        raise SystemExit(f'{comp}: expected 1 replacement, got {n}')

print()
print('=' * 94)
print('VERIFY THE FINAL NETLIST')
print('=' * 94)
txt = net.decode('utf-8-sig', errors='replace')
ok = True
for comp, want in TARGET.items():
    m = re.search(r'(?m)^' + comp + r'\s+\S+\s+\S+\s+(\S+)', txt)
    got = m.group(1)
    good = got == want.decode()
    ok &= good
    print(f'  {comp:7s} = {got:<20s} want {want.decode():<20s} {"OK" if good else "WRONG"}')

# receiver chain must be untouched
print()
for line in ['rRG_BB BB_FB VREF 10000', 'rRF_BB BBO FB_TRIM 150000',
             'rRV_BB FB_TRIM BB_FB 3511', 'rRLOAD V2 0 1000000']:
    present = line.encode() in net
    ok &= present
    print(f'  receiver chain "{line[:24]:24s}..." preserved: {present}')

# precharge must still be the precharged variant
for line in [b'cC111 TP6 0 4.7e-11 IC=0.43', b'cC115 TP6 BB_IN 1e-08 IC=-4.1',
             b'cCBB V2_OP 0 1.32629e-10 IC=4.5']:
    present = line in net
    ok &= present
    print(f'  precharge "{line.decode()[:38]:38s}" preserved: {present}')

if not ok:
    raise SystemExit('VERIFICATION FAILED -- not writing')

# how many bytes differ from the baseline?
print()
diff = sum(1 for a, b in zip(base, net) if a != b) + abs(len(base) - len(net))
print(f'  bytes differing from baseline: {diff}')
print(f'  baseline {len(base)} B -> target {len(net)} B')

TAG = 'LIN_2Vpp_pre'
for d in (HERE, RUNTIME):
    (d / f'{TAG}.cir').write_bytes(net)
    cmd = f'''source {RUNTIME.as_posix()}/{TAG}.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set trtol = 1
set reltol = 0.0001
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 2n 5m 0 2n uic
write-and-destroy-iplot "{RUNTIME.as_posix()}/{TAG}.raw"
end-scope
'''.encode('ascii')
    (d / f'{TAG}.cmd').write_bytes(cmd)

# also (re)write the 4 Vpp reference under the SAME options
TAG4 = 'REF_4Vpp_pre'
for d in (HERE, RUNTIME):
    (d / f'{TAG4}.cir').write_bytes(base)
    (d / f'{TAG4}.cmd').write_bytes(
        cmd.replace(TAG.encode(), TAG4.encode()))

print()
print('=' * 94)
print('WRITTEN')
print('=' * 94)
for d in (HERE, RUNTIME):
    for tag in (TAG, TAG4):
        for ext in ('cir', 'cmd'):
            p = d / f'{tag}.{ext}'
            print(f'  {p.stat().st_size:>8d} B  sha256={hashlib.sha256(p.read_bytes()).hexdigest()[:16]}  {p}')

meta = {
    'tag': TAG,
    'tran': 'tran 2n 5m 0 2n uic',
    'initial': 'precharged (unchanged from accepted S03-03 baseline)',
    'source_sha256': hashlib.sha256(base).hexdigest(),
    'target_sha256': hashlib.sha256(net).hexdigest(),
    'changes': [{'component': k, 'from': EXPECT[k].decode(), 'to': v.decode()}
                for k, v in TARGET.items()],
    'unchanged': ['rRVRF', 'rRVDT', 'rRVDB', 'rRG_BB', 'rRF_BB', 'rRV_BB', 'rRLOAD',
                  'precharge IC values'],
    'note': 'D=50% row of potentiometer_settings.csv. Only the input attenuator '
            'divider changes; receive gain and duty are held fixed, as required.',
}
(HERE / 'lin_manifest.json').write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print()
print(f'  manifest: {HERE / "lin_manifest.json"}')
