"""S05-10: bounded AC interface checks; no historical/transient reruns.

Reuse the hashed NOM_132 and C_Q50 raw data. New cases change probe loading
only, or remove the RF stages to test an explicit passive port-load fixture.
The buffer's input R/C is an interface budget, NOT an ADA4817 macro-model.
Run without flags to create/reuse four short AC cases; --verify is read-only.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib, json, subprocess, sys, time
import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[2]
WORK = Path('D:/ms_xsp/s05_measurement_20261030')
EXE = Path('D:/ms_xsp/s04_crosscheck_20261017/Spice64/bin/ngspice_con.exe')
sys.path.insert(0, str(STAGE/'lc_parts_20261030'))
import lc_parts as lp
import run_diagnosis as d


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fixed(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        assert p.read_bytes() == data, f'Immutable result differs: {p}'
    else:
        p.write_bytes(data)


def dump(p, obj):
    fixed(p, (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8'))


def initialize_history():
    dest = HERE/'history_manifest.json'
    if not dest.exists():
        paths = subprocess.check_output(['git', 'ls-files', '-z', '--',
                  'simulation/v4_hardware/stage5_receiver'], cwd=ROOT).decode('utf-8').split('\0')
        dump(dest, dict(git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                  cwd=ROOT, text=True).strip(), files={p: sha(ROOT/p) for p in paths if p}))
    manifest = json.loads(dest.read_text(encoding='utf-8'))
    for p, h in manifest['files'].items():
        assert sha(ROOT/p) == h, f'Historical file changed: {p}'
    return manifest


def metric(f, h, zin):
    return lp.metrics(f, h, zin)


def diff(m, ref):
    return dict(center_khz=(m['center_edges_mhz']-ref['center_edges_mhz'])*1000,
                bandwidth_khz=(m['bw_mhz']-ref['bw_mhz'])*1000,
                gain31_db=m['gain31_db']-ref['gain31_db'],
                relative29_db=m['relative29_db']-ref['relative29_db'],
                relative33_db=m['relative33_db']-ref['relative33_db'])


def solve(name, net, node):
    record = HERE/'results'/(name+'.json')
    raw_path, log_path = WORK/(name+'.raw'), WORK/(name+'.log')
    net_path = HERE/'netlists'/(name+'.cir')
    fixed(net_path, net.replace('@RAW@', raw_path.as_posix()).encode('ascii'))
    fixed(WORK/net_path.name, net_path.read_bytes())
    if record.exists():
        r = json.loads(record.read_text())
        assert sha(net_path) == r['net_sha256'] and sha(raw_path) == r['raw_sha256']
        assert sha(log_path) == r['log_sha256']
        return d.readraw(raw_path), r
    assert not raw_path.exists() and not log_path.exists(), 'Preserved incomplete case; use new name'
    start = time.monotonic()
    try:
        proc = subprocess.run([str(EXE), '-b', '-n', '-o', str(log_path), str(WORK/net_path.name)],
                              cwd=WORK, capture_output=True, timeout=20,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        assert proc.returncode == 0 and raw_path.exists(), proc.stderr.decode(errors='replace')
        raw = d.readraw(raw_path)
        f = raw['frequency'].real
        assert len(f) == 2401 and f[0] == 20e6 and f[-1] == 44e6
        assert np.isfinite(raw['v('+node+')']).all()
    except Exception as e:
        dump(HERE/'failures'/(name+'.json'), dict(error=str(e), net_sha256=sha(net_path),
             elapsed_s=time.monotonic()-start, log_path=str(log_path), raw_path=str(raw_path)))
        raise
    fixed(HERE/'results'/(name+'.log'), log_path.read_bytes())
    zin = 50*raw['v(input)']/(1-raw['v(input)'])
    r = dict(name=name, node=node, net_sha256=sha(net_path), raw_sha256=sha(raw_path),
             raw_path=str(raw_path), log_sha256=sha(log_path), simulator_sha256=sha(EXE),
             elapsed_s=time.monotonic()-start, metrics=metric(f, raw['v('+node+')'], zin))
    dump(record, r)
    return raw, r


def main():
    history = initialize_history()
    prev = STAGE/'lc_parts_20261030'
    oldrecord = json.loads((prev/'results/NOM_132.json').read_text())
    assert sha(oldrecord['raw_path']) == oldrecord['raw_sha256']
    original_net = prev/'netlists/NOM_132.cir'
    assert sha(original_net) == oldrecord['net_sha256']
    old = d.readraw(Path(oldrecord['raw_path']))
    f = old['frequency'].real
    zin = 50*old['v(input)']/(1-old['v(input)'])
    baseline_rf = metric(f, old['v(rf)'], zin)
    baseline_port = metric(f, old['v(port)'], zin)
    n = lp.LoadedNetwork()
    params = next(r['parameters'] for r in json.loads((prev/'ac_cases.json').read_text())
                  if r['name'] == 'NOM_132')
    net = original_net.read_text().replace(oldrecord['raw_path'].replace('\\','/'), '@RAW@')
    assert '@RAW@' in net
    probes = []
    for cp in (1, 3, 10):
        modified = net.replace('RTEST rf 0 2000',
                   f'RPROBE rf 0 1Meg\nCPROBE rf 0 {cp}p\nRTEST rf 0 2000')
        raw, r = solve(f'RF_ADD_{cp}p', modified, 'rf')
        # Includes RRF and the ORIGINAL 2k||10p load. Only the extra probe varies.
        probes.append(dict(probe_pf=cp, probe_r_ohm=1e6, metrics=r['metrics'],
                           delta_vs_archived=diff(r['metrics'], baseline_rf)))

    # Independent LC, no Q1/Q2/diode/opamp. Total port capacitance = 14 pF.
    # Physical interpretation: Cext=11p plus probe/buffer INPUT budget=3p.
    passive = net.split('VSUP vcc')[0] + '''* Passive emulator includes RPORT=1Meg above
RLOAD port 0 953
RPROBE port 0 1Meg
CEXT port 0 11p
CPROBE port 0 3p
.control
set filetype=binary
save all
ac lin 2401 20meg 44meg
write @RAW@
quit
.endc
.end
'''
    raw, r = solve('PORT_LOAD_953_14p', passive, 'port')
    port_cases = []
    for total in (13., 14., 15.):
        y = 1/953 + 2e-6 + 2j*np.pi*f*total*1e-12
        fixture = SimpleNamespace(f=f, yload=y, amp=np.ones_like(f, dtype=complex))
        h, z = lp.response(fixture, params)
        m = metric(f, h, z)
        port_cases.append(dict(total_pf=total, metrics=m, delta_vs_original_port=diff(m, baseline_port)))
        if total == 14:
            numerical_error = float(np.max(np.abs(h/raw['v(port)']-1)))
            assert numerical_error < 1e-8
    y31 = np.interp(31e6, n.f, n.yload)
    extracted = []
    for mhz in (28,29,31,33,34):
        y = np.interp(mhz*1e6, n.f, n.yload)
        extracted.append(dict(f_mhz=mhz, parallel_r_ohm=float(1/y.real),
                              parallel_c_pf=float(y.imag/(2*np.pi*mhz*1e6)*1e12)))
    out = dict(kind='Small-signal AC only; no hardware or buffer stability qualification',
               git_head=history['git_head'], historical_files_checked=len(history['files']),
               baseline_raw_path=oldrecord['raw_path'], baseline_raw_sha256=oldrecord['raw_sha256'],
               baseline_rf=baseline_rf, baseline_port=baseline_port, probe_at_rf=probes,
               extracted_port_load=extracted, passive_port_fixture=port_cases,
               passive_spice_crosscheck_max_relative_error=numerical_error,
               new_ac_cases=4, transient_cases=0,
               limits=['Probe capacitance is lumped; no probe transfer/ground lead model',
                       'RF reference already contains RRF=1k and RTEST=2k || CTEST=10p',
                       '953 ohm || 14pF approximates Q1 input; it is not a 50 ohm port',
                       '13/15p are sensitivity calculations, not additional SPICE simulations',
                       'No specific test-buffer device model, loop gain or hardware was tested'])
    dump(HERE/'interface_results.json', out)
    initialize_history()
    print(json.dumps(out, ensure_ascii=False, indent=2))


def verify():
    history = initialize_history()
    rows = list((HERE/'results').glob('*.json'))
    assert len(rows) == 4
    for p in rows:
        r = json.loads(p.read_text())
        assert sha(HERE/'netlists'/(r['name']+'.cir')) == r['net_sha256']
        assert sha(r['raw_path']) == r['raw_sha256']
        assert sha(HERE/'results'/(r['name']+'.log')) == r['log_sha256']
        raw = d.readraw(Path(r['raw_path'])); f = raw['frequency'].real
        zin = 50*raw['v(input)']/(1-raw['v(input)'])
        assert metric(f, raw['v('+r['node']+')'], zin) == r['metrics']
    print(f'PASS: {len(rows)} raw/net/log hashes and metrics; {len(history["files"])} historical files unchanged; no simulations run')


if __name__ == '__main__':
    verify() if '--verify' in sys.argv else main()
