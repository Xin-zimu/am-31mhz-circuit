"""Build S03-04 step-2..5 engine trial set.

Canonical copies stay in the workspace folder; the engine itself is driven from an
ASCII staging path because Multisim's nutmeg 'source' command cannot read non-ASCII paths.
"""
from pathlib import Path
import shutil, hashlib, json

WS   = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS / '副本专用文件夹'
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')       # ASCII staging for the engine
for d in (KEEP / 'engine', ENG):
    d.mkdir(parents=True, exist_ok=True)

SRC = WS / 'cold_gui_actual.cir'                        # GUI-exported netlist, read-only
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

manifest = {
  'purpose': 'S03-04 control-line difference closure: does the GUI control block alone explain '
             'the ~226 ns transient nonconvergence?',
  'source_netlist': {'file': str(SRC), 'sha256': sha(SRC),
                     'note': 'Exact GUI export of S03_COLD_ZERO_GEAR500_UIC_20us. Copied, .end appended, nothing else changed.'},
  'staging_dir_ascii': str(ENG),
  'canonical_dir': str(KEEP),
  'tests': {},
}

def build(name, opts, tstop='20u', trtol_default=True, extra=None, note=''):
    cir = ENG / f'{name}.cir'
    data = SRC.read_bytes().rstrip() + b'\n.end\n'
    cir.write_bytes(data)
    (KEEP / 'engine' / f'{name}.cir').write_bytes(data)
    lines = [f'source {cir.as_posix()}',
             'begin-scope page Transient Analysis',
             'save $v1 $bb_in $bbo $v2',
             'iplot $v1 $bb_in $bbo $v2']
    lines += ['set convlimit', 'set rshunt = 1e+012', 'set dynamicdc', 'set inertialdelay', 'set suposc']
    for k, v in (extra or {}).items():
        lines.append(f'set {k} = {v}')
    for k, v in opts.items():
        lines.append(f'set {k} = {v}')
    lines.append(f'tran 2n {tstop} 0 2n uic')
    lines.append(f'write-and-destroy-iplot "{(ENG / (name + ".raw")).as_posix()}"')
    lines.append('end-scope')
    cmd = ENG / f'{name}.cmd'
    cmd.write_text('\n'.join(lines) + '\n', encoding='ascii')
    shutil.copy2(cmd, KEEP / 'engine' / f'{name}.cmd')
    manifest['tests'][name] = {
        'cmd': str(cmd), 'canonical_cmd': str(KEEP / 'engine' / f'{name}.cmd'),
        'netlist_sha256': sha(cir), 'options': opts, 'extra': extra or {},
        'tstop': tstop, 'note': note}
    return name

# --- Step 2/3 baseline: reproduce the documented engine configuration exactly
build('A_ref', dict(trtol='1', reltol='0.0001', itl4='500', method='gear'),
      note='documented engine configuration; expected to reach 20 us')

# --- Step 1 closure: vary ONLY the LTE control that the GUI also has (reltol/trtol)
build('B_xspice_default', dict(trtol='7', reltol='0.001', itl4='100'),
      note='XSPICE defaults, i.e. GUI settings actually in force if the GUI .options were ignored')
build('C_tight', dict(trtol='0.5', reltol='1e-06', itl4='500', method='gear'),
      note='stricter than GUI')
build('D_tightest', dict(trtol='0.1', reltol='1e-09', itl4='500', method='gear'),
      note='much stricter than GUI')
build('E_trap_nomethod', dict(trtol='1', reltol='0.0001', itl4='500'),
      note='same LTE, trapezoidal instead of gear')

# --- Step 2: TMAX=TSTEP=1 ns, short window first
for tstop, tag in [('500n', 'f500ns'), ('2u', 'f2us'), ('20u', 'f20us')]:
    build(f'F_tmax1ns_{tag}',
          dict(trtol='1', reltol='0.0001', itl4='100'),
          tstop=tstop, extra={'tmax': '1e-09'},
          note=f'TMAX forced to 1 ns; TSTOP={tstop}')

# --- Method/pivot family, one item at a time (step 4 priority order)
build('G_pivtol', dict(trtol='1', reltol='0.0001', itl4='500', method='gear'),
      extra={'pivtol': '1e-15'}, note='tighter pivot tolerance')
build('H_gmin', dict(trtol='1', reltol='0.0001', itl4='500', method='gear'),
      extra={'gmin': '0'}, note='kills the parallel gmin leak conductances')
build('I_chgtol', dict(trtol='1', reltol='0.0001', itl4='500', method='gear'),
      extra={'chgtol': '1e-18'}, note='tighter charge tolerance')
build('J_trap_maxord1', dict(trtol='1', reltol='0.0001', itl4='500', method='trapezoidal'),
      extra={'maxord': '1'}, note='backward Euler via maxord=1')

(KEEP / 'engine' / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(ENG / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v['options'] for k, v in manifest['tests'].items()}, indent=1))
print('staging:', ENG)
