"""Print the exact envelope gaps used in the recommendation table."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rf_study as L

R = L.ROOT / 'results'
ar = json.loads((R / 'envelope_arithmetic.json').read_text(encoding='utf8'))

want = ('A 330/620', 'A 430/680', 'A 510/680', 'A 390/620', 'A470', 'A560')
for e in ar:
    if e['convention'] != 'A':
        continue
    if not any(w in e['label'] for w in want):
        continue
    h, lo = e['W_high_vpp'], e['W_low_vpp']
    print(f"{e['label']:18s} Ypk={e['Y_peak']:.4f} margin={100*(1-e['Y_peak']):5.2f}%  "
          f"Wh={h:.6f} (gap {2.0-h:+.6f})  Wl={lo:.6f} (gap {1.2-lo:+.6f})  m={e['modulation']:.4f}%")
