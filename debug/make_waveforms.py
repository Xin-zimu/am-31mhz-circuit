import sys, statistics, csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def parse_ascii_raw(p):
    txt = Path(p).read_text(errors='replace')
    head, body = txt.split('Values:', 1)
    names = []
    inb = False
    for l in head.splitlines():
        if l.startswith('Variables:'): inb = True; continue
        if inb:
            parts = l.split()
            if len(parts) >= 3: names.append(parts[-1])
    cols = [[] for _ in names]
    cur = None
    for l in body.splitlines():
        l = l.rstrip('\r\n')
        if not l.strip(): continue
        segs = [s for s in l.split('\t') if s.strip() != '']
        if len(segs) == 2 and segs[0].strip().isdigit():
            cols[0].append(float(segs[1])); cur = 1; continue
        if segs and cur is not None and cur < len(cols):
            v = segs[-1].strip()
            if ',' in v: v = v.split(',')[0]
            cols[cur].append(float(v)); cur += 1
    n = min(len(c) for c in cols)
    return names, [c[:n] for c in cols]

src = sys.argv[1]
outdir = Path(sys.argv[2])
names, cols = parse_ascii_raw(src)
d = {n: c for n, c in zip(names, cols)}
t = d['time']
print('points', len(t), 'span', t[-1])

step = max(1, len(t)//120000)
idx = range(0, len(t), step)
with (outdir/'AM_22k_200us_waveforms.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['time_s'] + [n for n in names if n != 'time'])
    for i in idx:
        w.writerow(['%.12g' % t[i]] + ['%.9g' % d[n][i] for n in names if n != 'time'])
print('csv rows', len(list(idx)))

fig, ax = plt.subplots(5, 1, figsize=(13, 15), sharex=True)
tv1 = [x*1e6 for x in t]
def dec(n):
    return [d[n][i]*1 for i in idx], [t[i]*1e6 for i in idx]
y, tx = dec('V(v1)');      ax[0].plot(tx, y, lw=0.9); ax[0].set_ylabel('V(v1)  [V]');  ax[0].set_title('VINPUT 22 kHz pulse (TSTART=0, TSTOP=200 us, engine TMAX=1.008 ns)')
y, tx = dec('V(tp3)');     ax[1].plot(tx, y, lw=0.4); ax[1].set_ylabel('V(tp3) [V]');  ax[1].set_title('EAM polynomial source output = 0.6*V1 + 0.1*V1*V2  (AM, 31 MHz carrier)')
y, tx = dec('V(tp6)');     ax[2].plot(tx, y, lw=0.8); ax[2].set_ylabel('V(tp6) [V]');  ax[2].set_title('D101 detector output (envelope)')
y, tx = dec('V(v2)');      ax[3].plot(tx, y, lw=0.9); ax[3].set_ylabel('V(v2)  [V]');  ax[3].set_title('EBB x15 output (baseband)')
y, tx = dec('V(tp2)');     ax[4].plot(tx, y, lw=0.4); ax[4].set_ylabel('V(tp2) [V]');  ax[4].set_title('VCARRIER 31 MHz')
ax[4].set_xlabel('time [us]')
for a in ax: a.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(outdir/'AM_22k_200us_waveforms.png', dpi=110)
print('png written')

# zoom on 0..2 us to show the 31 MHz carrier
m = [i for i in range(len(t)) if t[i] <= 2e-6]
fig2, ax2 = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
for k, n in enumerate(('V(tp2)', 'V(tp3)', 'V(tp6)')):
    ax2[k].plot([t[i]*1e6 for i in m], [d[n][i] for i in m], lw=0.8)
    ax2[k].set_ylabel(n); ax2[k].grid(True, alpha=0.3)
ax2[2].set_xlabel('time [us]')
ax2[0].set_title('Zoom 0-2 us : 31 MHz carrier (T=32.26 ns, engine step 1.008 ns = T/32)')
fig2.tight_layout()
fig2.savefig(outdir/'AM_22k_200us_zoom.png', dpi=110)
print('zoom written')
