"""Inspect Multisim XSPICE .raw text waveforms in read-only mode."""
from pathlib import Path
import sys

def head_tail(path, n=3):
    p = Path(path)
    size = p.stat().st_size
    with p.open('rb') as f:
        first = f.read(1200)
        f.seek(max(0, size - 1200))
        last = f.read()
    return first, last, size

for name in ['cold_engine_gui_net.raw', 'cold_engine_control.raw']:
    path = Path(r'D:\ms_xsp\stage3_acceptance') / name
    first, last, size = head_tail(path)
    print('=' * 70)
    print(name, size, 'bytes')
    print('--- first 1200 bytes ---')
    print(first.decode('ascii', 'replace'))
    print('--- last 1200 bytes ---')
    print(last.decode('ascii', 'replace'))
