"""Extract the embedded lib_symbols from the delivered schematics into S05.kicad_sym.

ERC warns "The current configuration does not include the library 'S05'" once per
placed symbol. The symbols are embedded in each .kicad_sch (generator
s05_netlist_drawings), so the drawings are self-contained and open fine; the warning
is about the reusable library file being absent.

This builds that library file and a project-local sym-lib-table so the delivered
folder can be re-checked with a real library behind it. It does not modify the
schematics and does not change any net.
"""
from pathlib import Path
import re, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
KICAD = ROOT / 'output/pdf/S05_A_G22_施工图_20261030/kicad'


def balanced_block(text, start):
    """Return the balanced s-expression starting at `start` (points at '(')."""
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError('unbalanced')


def strip_prefix(sym):
    """'S05:C_h' -> 'C_h' and drop the KiCad-only instance paths."""
    name = re.match(r'\(symbol "S05:([^"]+)"', sym).group(1)
    body = re.sub(r'\(symbol "S05:', '(symbol "', sym)
    body = re.sub(r'^\(symbol "[^"]+"', f'(symbol "{name}"', body, count=1)
    return name, body


def main():
    libs = {}
    for sch in sorted(KICAD.glob('*.kicad_sch')):
        text = sch.read_text(encoding='utf-8')
        i = text.find('(lib_symbols')
        if i < 0:
            continue
        block = balanced_block(text, i)
        # Walk the direct children of (lib_symbols ...) that are (symbol "..." ...)
        pos = len('(lib_symbols')
        while True:
            m = re.compile(r'\s*\(symbol "').search(block, pos)
            if not m:
                break
            start = m.end() - len('(symbol "')
            child = balanced_block(block, start)
            name, body = strip_prefix(child)
            libs.setdefault(name, body)
            pos = start + len(child)

    if not libs:
        print('no embedded symbols found', file=sys.stderr)
        return 1

    header = ('(kicad_symbol_lib (version 20231120) (generator s05_lib_extract)\n')
    out = header + '\n'.join('  ' + b for _, b in sorted(libs.items())) + '\n)\n'
    (KICAD / 'S05.kicad_sym').write_text(out, encoding='utf-8')

    # Project-local symbol library table so KiCad can resolve the S05 nickname.
    table = ('(sym_lib_table\n'
             '  (lib (name "S05")(type "KiCad")(uri "${KIPRJMOD}/S05.kicad_sym")'
             '(options "")(descr "S05 receiver symbols extracted from the delivered schematics"))\n'
             ')\n')
    (KICAD / 'sym-lib-table').write_text(table, encoding='utf-8')

    print(f'wrote S05.kicad_sym with {len(libs)} symbols: {sorted(libs)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
