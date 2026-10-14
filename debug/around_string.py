import sys
from pathlib import Path

def strings_with_offsets(data, minlen=4):
    out = []
    cur = bytearray(); start = 0
    for i, byte in enumerate(data):
        if 32 <= byte < 127:
            if not cur: start = i
            cur.append(byte)
        else:
            if len(cur) >= minlen:
                out.append((start, bytes(cur).decode('ascii')))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append((start, bytes(cur).decode('ascii')))
    return out

target = sys.argv[1]
needle = sys.argv[2]
span = int(sys.argv[3]) if len(sys.argv) > 3 else 25
data = Path(target).read_bytes()
ss = strings_with_offsets(data)
print('file %s : %d ascii strings' % (Path(target).name, len(ss)))
for idx, (off, s) in enumerate(ss):
    if needle in s:
        print('\n===== match at 0x%X : %r  (index %d)' % (off, s, idx))
        for j in range(max(0, idx - span), min(len(ss), idx + span + 1)):
            mark = '>>' if j == idx else '  '
            print('%s 0x%06X  %s' % (mark, ss[j][0], ss[j][1][:150]))
