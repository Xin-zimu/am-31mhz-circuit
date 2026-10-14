import math, sys, collections
from pathlib import Path

MS14 = Path(r'D:\实验报告文件夹\电路2\simulation\system\AM_22k_D50_A4V_debug.ms14')
EWCFG = Path(r'C:\Users\86139\AppData\Roaming\National Instruments\Circuit Design Suite\14.3\config\standard_ms_pro.ewcfg')

def split(p):
    b = p.read_bytes()
    if b.startswith(b'MSMCompressedElectronicsWorkbenchXML'):
        off = 36
    elif b.startswith(b'CompressedElectronicsWorkbenchXML'):
        off = 32
    else:
        raise SystemExit('unknown magic')
    hdr = b[off:off+16]
    a, z, c, d = (int.from_bytes(hdr[i:i+4], 'little') for i in (0, 4, 8, 12))
    tag = b[off+16:off+20]
    payload = b[off+20:]
    return dict(total=len(b), off=off, A=a, zero=z, C=c, B=d, tag=tag.hex(), payload=payload)

m = split(MS14); e = split(EWCFG)
for nm, d in (('ms14', m), ('ewcfg', e)):
    print('%s total=%d payload=%d A=%d(0x%X) C=%d B=%d(0x%X) tag=%s' %
          (nm, d['total'], len(d['payload']), d['A'], d['A'], d['C'], d['B'], d['B'], d['tag']))

def entropy(b):
    c = collections.Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

for nm, d in (('ms14', m), ('ewcfg', e)):
    p = d['payload']
    print('%s payload entropy = %.4f bits/byte  (8.0=random, ~4.5=text)' % (nm, entropy(p[:200000])))
    print('   first 48 bytes:', p[:48].hex(' '))
    print('   zero bytes: %d (%.3f%%)' % (p.count(0), 100*p.count(0)/len(p)))

# common prefix between the two payloads
a = m['payload']; b = e['payload']
n = min(len(a), len(b)); i = 0
while i < n and a[i] == b[i]:
    i += 1
print('\ncommon payload prefix length = %d bytes' % i)
print('   ms14  @%d: %s' % (i, a[max(0,i-8):i+16].hex(' ')))
print('   ewcfg @%d: %s' % (i, b[max(0,i-8):i+16].hex(' ')))

# autocorrelation: search for a repeating XOR keystream period
def coincidences(p, lag, span=40000):
    s = p[:span]
    same = 0; tot = 0
    for k in range(len(s)-lag):
        if s[k] == s[k+lag]: same += 1
        tot += 1
    return same/tot

print('\nlag  coincidence (0.0039 = random, higher = repeating key)')
best = []
for lag in list(range(1, 33)) + [40,48,56,64,96,128,192,256]:
    c = coincidences(a, lag)
    best.append((c, lag))
for c, lag in sorted(best, reverse=True)[:10]:
    print('  lag=%-4d %.5f' % (lag, c))
