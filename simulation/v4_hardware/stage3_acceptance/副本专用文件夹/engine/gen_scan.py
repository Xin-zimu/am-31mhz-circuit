"""Systematic .options sensitivity scan on the engine.

Goal: find which control cards actually reach the solver's step control.
Metric: the accepted time axis over 0..500 ns.
"""
from pathlib import Path
import hashlib, json

WS   = Path(r'D:\实验报告文件夹\电路2\simulation\v4_hardware\stage3_acceptance')
KEEP = WS / '副本专用文件夹'
ENG  = Path(r'D:\ms_xsp\stage3_acceptance\s0304')
base = (WS / 'cold_gui_actual.cir').read_bytes().rstrip()

CASES = {
 'U00_none':        '',
 'U01_reltol':      '.options reltol=0.1',
 'U02_reltoltight': '.options reltol=1e-9',
 'U03_trtol':       '.options trtol=7',
 'U04_trtol0':      '.options trtol=0.01',
 'U05_gui_lte':     '.options reltol=0.0001 trtol=1',
 'U06_abstol':      '.options abstol=1e-15',
 'U07_vntol':       '.options vntol=1e-12',
 'U08_chgtol':      '.options chgtol=1e-18',
 'U09_gmin0':       '.options gmin=0',
 'U10_maxord5':     '.options maxord=5',
 'U11_itl4':        '.options itl4=1000',
 'U12_pivtol':      '.options pivtol=1e-15',
 'U13_method_gear': '.options method=gear',
 'U14_defl':        '.options defl=1e-6 defw=1e-6 defad=1e-9 defas=1e-9',
 'U15_tnom':        '.options tnom=50',
 'U16_bypass0':     '.options bypass=0',
 'U17_oldlimit':    '.options oldlimit=1',
 'U18_convlimit':   '.options convlimit',
 'U19_dynamicdc':   '.options dynamicdc',
 'U20_inertial':    '.options inertialdelay',
 'U21_suposc':      '.options suposc',
 'U22_rshunt':      '.options rshunt=1e12',
 'U23_itl1':        '.options itl1=500',
 'U24_itl2':        '.options itl2=500',
 'U25_abstol_lo':   '.options abstol=1e-6',
 'U26_all_gui':     '.options reltol=0.0001 trtol=1 itl4=500 method=gear convlimit rshunt=1e12 dynamicdc inertialdelay suposc',
}
man = {'tran': '2n 500n 0 2n uic', 'cases': {}}
for name, opt in CASES.items():
    body = base + b'\n' + (opt.encode('ascii') + b'\n' if opt else b'') + b'.end\n'
    cir = ENG / f'{name}.cir'; cir.write_bytes(body)
    L = [f'source {cir.as_posix()}', 'begin-scope page Transient Analysis',
         'save $v1 $bb_in $bbo $v2', 'iplot $v1 $bb_in $bbo $v2',
         'tran 2n 500n 0 2n uic',
         f'write-and-destroy-iplot "{(ENG / (name + ".raw")).as_posix()}"', 'end-scope']
    cmd = ENG / f'{name}.cmd'; cmd.write_text('\n'.join(L) + '\n', encoding='ascii')
    man['cases'][name] = {'options': opt, 'netlist_sha256': hashlib.sha256(body).hexdigest()}
(KEEP/'engine'/'manifest_scan.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
(ENG/'manifest_scan.json').write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding='utf-8')
print('cases:', len(CASES))
