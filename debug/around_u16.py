import sys
from pathlib import Path

def u16_strings(data, minlen=4):
    out = []
    cur = []
    start = 0
    i = 0
    n = len(data)
    while i + 1 < n:
        lo = data[i]; hi = data[i+1]
        if hi == 0 and 32 <= lo < 127:
            if not cur: start = i
            cur.append(chr(lo))
            i += 2
        else:
            if len(cur) >= minlen:
                out.append((start, ''.join(cur)))
            cur = []
            i += 1 if not cur else 2
    if len(cur) >= minlen:
        out.append((start, ''.join(cur)))
    return out

target = sys.argv[1]
needle = sys.argv[2]
span = int(sys.argv[3]) if len(sys.argv) > 3 else 25
data = Path(target).read_bytes()
ss = u16_strings(data)
print('file %s : %d utf16 strings' % (Path(target).name, len(ss)))
found = 0
for idx, (off, s) in enumerate(ss):
    if needle.lower() in s.lower():
        found += 1
        print('\n===== match at 0x%X : %r (index %d)' % (off, s, idx))
        for j in range(max(0, idx - span), min(len(ss), idx + span + 1)):
            mark = '>>' if j == idx else '  '
            print('%s 0x%06X  %s' % (mark, ss[j][0], ss[j][1][:140]))
        if found >= 3: break
if not found:
    print('no match')
