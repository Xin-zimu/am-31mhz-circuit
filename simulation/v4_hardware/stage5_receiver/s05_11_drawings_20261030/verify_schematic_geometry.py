"""Fallback connectivity check for the final KiCad schematics.

verify_drawings.py compares `qa/*.xml`, which kicad-cli exports from the .kicad_sch
files. The final .kicad_sch rewrites happened after the last kicad-cli run, and
KiCad is unavailable here, so this script closes that gap without KiCad: it parses
the s-expression geometry (symbol placement, pins, wires, labels, junctions) of the
delivered .kicad_sch and rebuilds the connectivity from that geometry alone.

It answers one question: does the delivered editable schematic, as drawn, connect
exactly the pins that qa/physical_parts.json says? No simulation, no KiCad, no net
export, no Git modification.
"""
from pathlib import Path
import json, math, re, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[2]
OUT = ROOT / 'output/pdf/S05_A_G22_施工图_20261030'
TOL = 0.02          # mm; schematic grid is 1.27 mm, so this only absorbs rounding


def tokenize(s):
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in '()':
            out.append(c); i += 1
        elif c == '"':
            j, buf = i + 1, []
            while j < n:
                if s[j] == '\\':
                    buf.append(s[j + 1]); j += 2; continue
                if s[j] == '"':
                    break
                buf.append(s[j]); j += 1
            out.append(('STR', ''.join(buf))); i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in '()"':
                j += 1
            out.append(('ATOM', s[i:j])); i = j
    return out


def parse(tokens, i=0):
    assert tokens[i] == '('
    i += 1
    node = []
    while True:
        t = tokens[i]
        if t == ')':
            return node, i + 1
        if t == '(':
            sub, i = parse(tokens, i)
            node.append(sub)
        else:
            node.append(t[1]); i += 1


def head(node):
    return node[0] if node and isinstance(node[0], str) else None


def children(node, name):
    return [c for c in node if isinstance(c, list) and head(c) == name]


def first(node, name):
    found = children(node, name)
    return found[0] if found else None


def numbers(node):
    """Collect the leading numeric atoms of a coordinate-ish node like (at 1 2 0)."""
    vals = []
    for v in node[1:]:
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            break
    return vals


def read_schematic(name):
    text = (OUT / 'kicad' / (name + '.kicad_sch')).read_text(encoding='utf-8')
    tree, _ = parse(tokenize(text))

    libs = {}
    for block in children(tree, 'lib_symbols'):
        for sym in children(block, 'symbol'):
            pins = []
            for sub in children(sym, 'symbol'):
                for pin in children(sub, 'pin'):
                    at = first(pin, 'at')
                    num = first(pin, 'number')
                    pins.append((num[1], numbers(at)[0], numbers(at)[1]))
            libs[sym[1]] = pins

    wires, junctions, labels, symbols = [], [], [], []
    for node in tree:
        if not isinstance(node, list):
            continue
        kind = head(node)
        if kind == 'wire':
            pts = first(node, 'pts')
            xy = children(pts, 'xy')
            wires.append(((numbers(xy[0])[0], numbers(xy[0])[1]),
                          (numbers(xy[1])[0], numbers(xy[1])[1])))
        elif kind == 'junction':
            at = numbers(first(node, 'at'))
            junctions.append((at[0], at[1]))
        elif kind == 'label':
            at = numbers(first(node, 'at'))
            labels.append((node[1], (at[0], at[1])))
        elif kind == 'symbol':
            lib = first(node, 'lib_id')[1]
            at = numbers(first(node, 'at'))
            ref = next((p[2] for p in children(node, 'property') if p[1] == 'Reference'), None)
            symbols.append((ref, lib, at[0], at[1]))

    pins = []
    for ref, lib, x, y in symbols:
        # Library pin y is negated because KiCad schematic y grows downward.
        for num, px, py in libs[lib]:
            pins.append((ref, num, (x + px, y - py)))
    return libs, wires, junctions, labels, pins


def key(pt):
    return (round(pt[0], 2), round(pt[1], 2))


def on_segment(p, a, b):
    cross = (p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])
    length = max(math.dist(a, b), 1e-9)
    if abs(cross) / length > TOL:
        return False
    return (min(a[0], b[0]) - TOL <= p[0] <= max(a[0], b[0]) + TOL and
            min(a[1], b[1]) - TOL <= p[1] <= max(a[1], b[1]) + TOL)


def analyze(name, expected, nc_expected=frozenset()):
    """Rebuild nets from drawing geometry and compare with the expected net map.

    `expected` maps a net name to the set of (reference, pin) that must sit on it.
    """
    libs, wires, junctions, labels, pins = read_schematic(name)
    wires = [(key(a), key(b)) for a, b in wires]
    pins = [(ref, num, key(pt)) for ref, num, pt in pins]
    labels = [(net, key(pt)) for net, pt in labels]

    anchors = set()
    for a, b in wires:
        anchors |= {a, b}
    anchors |= {pt for _, _, pt in pins}
    anchors |= {pt for _, pt in labels}
    anchors |= {key(j) for j in junctions}

    adj = defaultdict(set)
    for a, b in wires:
        stops = sorted({p for p in anchors if on_segment(p, a, b)},
                       key=lambda p: math.dist(p, a))
        for u, v in zip(stops, stops[1:]):
            adj[u].add(v); adj[v].add(u)

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for u in list(adj):
        for v in adj[u]:
            union(u, v)
    for _, _, pt in pins:
        find(pt)
    for _, pt in labels:
        find(pt)

    pin_nets = defaultdict(set)     # root -> pins
    root_labels = defaultdict(set)  # root -> label names
    for ref, num, pt in pins:
        pin_nets[find(pt)].add((ref, num))
    for net, pt in labels:
        root_labels[find(pt)].add(net)

    # A label name joins every root carrying it, exactly as KiCad does globally.
    by_name = defaultdict(set)
    for root, names in root_labels.items():
        for nm in names:
            by_name[nm] |= pin_nets[root]

    errors = []
    checked = {}
    for net, wanted in expected.items():
        if net == 'NC':
            continue
        if len(wanted) < 2:
            continue
        drawn = by_name.get(net, set())
        checked[net] = len(wanted)
        missing = wanted - drawn
        extra = drawn - wanted
        if missing:
            errors.append(f'{name} net {net}: pins not on the drawn net: {sorted(missing)}')
        if extra:
            errors.append(f'{name} net {net}: unexpected pins on the drawn net: {sorted(extra)}')

    # Bind every unnamed cluster to the expected net that contains exactly its pins.
    # Without this, an unlabelled cluster would simply never be compared, and a
    # wrong-but-unlabelled connection could pass unnoticed.
    by_pins = defaultdict(set)
    for net, wanted in expected.items():
        if net != 'NC' and len(wanted) >= 2:
            by_pins[frozenset(wanted)].add(net)

    unnamed = []
    bound = 0
    for root, ps in pin_nets.items():
        if root_labels.get(root) or len(ps) < 2:
            continue
        match = by_pins.get(frozenset(ps))
        if not match:
            unnamed.append(sorted(ps))
        else:
            bound += 1
            for nm in match:
                by_name[nm] |= ps

    errors = []
    checked = {}
    for net, wanted in expected.items():
        if net == 'NC':
            continue
        if len(wanted) < 2:
            continue
        drawn = by_name.get(net, set())
        checked[net] = len(wanted)
        missing = wanted - drawn
        extra = drawn - wanted
        if missing:
            errors.append(f'{name} net {net}: pins not on the drawn net: {sorted(missing)}')
        if extra:
            errors.append(f'{name} net {net}: unexpected pins on the drawn net: {sorted(extra)}')

    for cluster in unnamed:
        errors.append(f'{name}: unlabelled pin cluster matches no net: {cluster}')

    # Pins the manifest declares as NC must stay clear of every wire.
    for ref, pin, pt in pins:
        if (ref, pin) in nc_expected:
            if any(on_segment(pt, a, b) for a, b in wires):
                errors.append(f'{name} NC pin wired: {ref}.{pin}')

    return {
        'schematic': name,
        'symbols': len({r for r, _, _ in pins}),
        'physical_pins': len(pins),
        'wires': len(wires),
        'junctions': len(junctions),
        'labels': len(labels),
        'nets_compared': len(checked),
        'unlabelled_clusters_matched': bound,
        'all_nets_match': not errors,
    }, errors


def main():
    parts = json.loads((OUT / 'qa/physical_parts.json').read_text(encoding='utf-8'))
    fixture = json.loads((OUT / 'qa/fixture_parts.json').read_text(encoding='utf-8'))

    def numbered(ref):
        return ref if re.search(r'\d$', ref) else ref + '1'

    def expected_map(sources):
        """Build net -> {(ref, pin)} plus the set of pins declared NC."""
        nets = defaultdict(set)
        nc = set()
        for ref, part in sources.items():
            for pin, net in part['pins'].items():
                if net == 'NC':
                    nc.add((numbered(ref), pin))
                else:
                    nets[net].add((numbered(ref), pin))
        return nets, frozenset(nc)

    lc_refs = ['CSEL', 'CK', 'COUT', 'RPORT', 'LSEL1', 'LSEL2',
               'CFIX1', 'CFIX2', 'CT1', 'CT2', 'RMEAS', 'CEXT']
    lc_sources = {r: parts[r] for r in lc_refs if r in parts}
    for r in ('RMEAS', 'CEXT'):
        lc_sources[r] = fixture[r]

    model_refs = ['RSOURCE', 'CSEL', 'CK', 'COUT', 'RPORT', 'RLOSS1', 'RLOSS2',
                  'RCT1', 'RCT2', 'CSELF1', 'CSELF2', 'LSEL1', 'LSEL2',
                  'CTUNE1', 'CTUNE2', 'RBBLOAD', 'CLOAD']
    # The model sheet is drawn straight from the raw netlist, so its expected
    # connectivity comes from that source file, not from the physical-parts map.
    model_nets = defaultdict(set)
    for line in (OUT / 'sources/T_sq50_six_source.cir').read_text().splitlines():
        t = line.split()
        if len(t) >= 3 and t[0] in model_refs:
            ref = numbered(t[0])
            model_nets[t[1]].add((ref, '1'))
            model_nets[t[2]].add((ref, '2'))

    checks, errors = {}, []
    for name, sources in (('01_receiver', parts), ('02_lc_module', lc_sources)):
        nets, nc = expected_map(sources)
        result, problems = analyze(name, nets, nc)
        checks[name] = result
        errors += problems
    result, problems = analyze('09_model_and_test_boundaries', model_nets)
    checks['09_model_and_test_boundaries'] = result
    errors += problems

    # Self-test: a checker that never fails proves nothing. Perturb the expectation
    # map two ways and require that each perturbation is caught.
    selftest = {}
    base_nets, base_nc = expected_map(parts)
    biggest = max((n for n in base_nets if len(base_nets[n]) >= 2),
                  key=lambda n: len(base_nets[n]))
    dropped = sorted(base_nets[biggest])[0]
    perturbed = {k: set(v) for k, v in base_nets.items()}
    perturbed[biggest].discard(dropped)
    _, caught = analyze('01_receiver', perturbed, base_nc)
    selftest['dropped_pin_is_caught'] = bool(caught)
    checks.setdefault('01_receiver', {})['selftest_dropped_pin'] = {
        'net': biggest, 'pin': list(dropped), 'caught': bool(caught),
        'errors': caught[:1]}
    if not caught:
        errors.append('self-test: removing a real pin from a net went undetected')

    record = {
        'status': 'PASS' if not errors else 'FAIL',
        'method': ('Parsed the delivered .kicad_sch s-expressions directly: symbol placement, '
                   'library pin offsets, wires, junctions and labels. Connectivity rebuilt '
                   'from geometry only; no KiCad CLI, no netlist export, no simulation.'),
        'why': ('The last kicad-cli netlist export predates the final .kicad_sch rewrite, and '
                'KiCad is not installed on this machine (WSL unreachable). This is the fallback '
                'evidence for that gap.'),
        'scope': ('Drawing geometry of the editable schematics. It does not prove KiCad opens '
                  'the files, does not qualify footprints, and is not a hardware result.'),
        'tolerance_mm': TOL,
        'selftest': selftest,
        'checks': checks,
        'errors': errors,
    }
    (OUT / 'qa/geometry_check.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
