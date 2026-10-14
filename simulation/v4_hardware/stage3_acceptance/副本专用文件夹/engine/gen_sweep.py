"""Generate engine option-sweep command files (copies only)."""
from pathlib import Path
import shutil, hashlib, json

WS = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
SRC = WS / 'cold_gui_actual.cir'          # GUI-exported netlist (read-only source)
ENG = WS / '副本专用文件夹' / 'engine'
ENG.mkdir(parents=True, exist_ok=True)

# copy the netlist byte-for-byte, append .end exactly as the previous engine runs did
data = SRC.read_bytes().rstrip() + b'\n.end\n'
net = ENG / 'cold_gui_actual.engine.cir'
net.write_bytes(data)

TESTS = {
 # name: (options dict or None, note)
 'A_REF':      (dict(trtol='1', reltol='0.0001', itl4='500', method='gear'), 'replicate documented engine config'),
 'B_LOOSE':    (dict(trtol='7', reltol='0.001', itl4='100'), 'XSPICE defaults (no strict set)'),
 'C_TIGHT':    (dict(trtol='0.5', reltol='1e-06', itl4='500', method='gear'), 'tighter LTE control'),
 'D_TIGHTEST': (dict(trtol='0.1', reltol='1e-09', itl4='500', method='gear'), 'tightest requested'),
 'E_NOMETHOD': (dict(trtol='1', reltol='0.0001', itl4='500'), 'same but trapezoidal'),
}

manifest = {'source_netlist': {'file': str(SRC), 'sha256': hashlib.sha256(SRC.read_bytes()).hexdigest()},
            'engine_netlist': {'file': str(net), 'sha256': hashlib.sha256(data).hexdigest()},
            'tests': {}}

for name, (opts, note) in TESTS.items():
    lines = [f'source {net.as_posix()}',
             'begin-scope page Transient Analysis',
             'save $v1 $bb_in $bbo $v2',
             'iplot $v1 $bb_in $bbo $v2',
             'set convlimit',
             'set rshunt = 1e+012',
             'set dynamicdc',
             'set inertialdelay',
             'set suposc']
    for k, v in opts.items():
        lines.append(f'set {k} = {v}')
    lines.append('tran 2n 20u 0 2n uic')
    lines.append(f'write-and-destroy-iplot "{(ENG / (name + ".raw")).as_posix()}"')
    lines.append('end-scope')
    cmd = ENG / f'{name}.cmd'
    cmd.write_text('\n'.join(lines) + '\n', encoding='ascii')
    manifest['tests'][name] = {'cmd': str(cmd), 'options': opts, 'note': note}

(ENG / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=False, indent=2))
