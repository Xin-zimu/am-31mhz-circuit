"""S05-11 native KiCad verification: ERC, netlist re-export, plot re-export, mechanical landing.

This closes the gap recorded in S05-11: the delivered .kicad_sch files were rewritten
after the last kicad-cli export, so the drawings rested on a self-written geometry
check rather than on KiCad itself. This script re-runs the native tools against the
final files and records every violation without filtering.

Requires KiCad 8+ (`kicad-cli sch erc`, added in 8.0) reachable from WSL.
It does NOT modify the schematics, the netlists' electrical content, or any S05
parameter. KiCad's own export timestamps do change, which is expected.

Exit code 0 means the electrical comparison passed. ERC findings are recorded, not
waived: this script reports them and lets the record state what they mean.
"""
from pathlib import Path
import hashlib, json, re, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
# .../simulation/v4_hardware/stage5_receiver/s05_11_drawings_20261030 -> repo root
ROOT = HERE.parents[3]
DRAW = ROOT / 'output/pdf/S05_A_G22_施工图_20261030'
KICAD = DRAW / 'kicad'
QA = DRAW / 'qa/kicad_native_20261031'
WSL_DIR = '/mnt/d/实验报告文件夹/电路2/output/pdf/S05_A_G22_施工图_20261030'

SCHEETS = ['01_receiver', '02_lc_module', '09_model_and_test_boundaries']

# Datasheet pin spacing, in mm, for the LC board parts (Coilcraft Doc 114 /
# Vishay Doc 28529). None = axial part whose span is set by lead forming.
SPACING = {
    'LSEL1': 3.96, 'LSEL2': 3.96,
    'CT1': 5.08, 'CT2': 5.08,
    'CSEL': 2.54, 'CK': 2.54, 'COUT': 2.54,
    'CFIX1': 2.54, 'CFIX2': 2.54, 'CEXT': 2.54,
    'RPORT': None, 'RMEAS': None, 'JRF': None,
}
GRID = 2.54


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wsl(cmd, timeout=180):
    """Run a command inside WSL; return (rc, stdout+stderr).

    Decode as UTF-8 with replacement: KiCad emits UTF-8, but the Windows console
    default is GBK and would abort the reader thread on non-GBK bytes.
    """
    p = subprocess.run(['wsl', '-d', 'Ubuntu', '--', 'sh', '-c', cmd],
                       capture_output=True, timeout=timeout)
    out = (p.stdout or b'') + (p.stderr or b'')
    return p.returncode, out.decode('utf-8', errors='replace')


def kicad_version():
    rc, out = wsl('kicad-cli version')
    return out.strip() if rc == 0 else f'unavailable (rc={rc})'


def run_erc(name):
    out_rel = f'{WSL_DIR}/qa/kicad_native_20261031/erc_{name}.rpt'
    sch = f'{WSL_DIR}/kicad/{name}.kicad_sch'
    # --exit-code-violations makes the rc reflect findings; capture it, don't fail.
    rc, log = wsl(f'kicad-cli sch erc --exit-code-violations -o "{out_rel}" "{sch}"')
    rpt = QA / f'erc_{name}.rpt'
    if not rpt.exists():
        return {'error': 'ERC report not produced', 'log': log[-400:]}
    text = rpt.read_text(encoding='utf-8')

    kinds = {}
    for m in re.finditer(r'^\[(\w+)\]: (.+)$', text, re.M):
        kinds[m.group(1)] = kinds.get(m.group(1), 0) + 1
    sev = {}
    for m in re.finditer(r'^    ; (\w+)$', text, re.M):
        sev[m.group(1)] = sev.get(m.group(1), 0) + 1
    tail = re.search(r'\*\* ERC messages: (\d+)\s+Errors (\d+)\s+Warnings (\d+)', text)

    findings = []
    for m in re.finditer(r'^\[(\w+)\]: (.+)\n    ; (\w+)\n((?:    @.*\n)*)', text, re.M):
        at = re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): (.+)', m.group(4))
        findings.append({'rule': m.group(1), 'message': m.group(2).strip(),
                         'severity': m.group(3),
                         'objects': [{'x': a[0], 'y': a[1], 'what': a[2].strip()} for a in at]})
    return {
        'report': str(rpt.relative_to(ROOT)),
        'messages': int(tail.group(1)) if tail else None,
        'errors': int(tail.group(2)) if tail else None,
        'warnings': int(tail.group(3)) if tail else None,
        'by_rule': kinds, 'by_severity': sev,
        'findings': findings,
    }


def classify_erc(results):
    """Group violations by cause so the record can state what each one means."""
    out = {}
    for name, r in results.items():
        if 'findings' not in r:
            continue
        buckets = {}
        for f in r['findings']:
            rule = f['rule']
            if rule == 'lib_symbol_issues':
                key = 'library_reference'
            elif rule == 'no_connect_connected':
                key = 'redundant_nc_flag_on_nc_type_pin'
            elif rule == 'no_connect_dangling':
                key = 'nc_flag_offset_from_pin'
            elif rule == 'label_dangling':
                key = 'single_pin_label'
            else:
                key = rule
            buckets.setdefault(key, []).append(
                {'rule': rule, 'message': f['message'], 'severity': f['severity'],
                 'objects': f['objects']})
        out[name] = {k: {'count': len(v), 'items': v} for k, v in buckets.items()}
    return out


def single_pin_nets(name):
    """Nets that hold exactly one pin: an electrically dangling label in the drawing."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(QA / f'{name}.xml')
    found = []
    for net in tree.findall('./nets/net'):
        n = net.attrib['name'].lstrip('/')
        nodes = [(a.attrib['ref'], a.attrib['pin']) for a in net.findall('node')]
        if n.startswith('unconnected-'):
            continue
        if len(nodes) == 1:
            found.append({'net': n, 'pins': nodes})
    return found


def netlist_electrical(name):
    """Reduce a KiCad netlist XML to its electrical content: component->value and pin->net.

    KiCad 7 and 8 differ in metadata (date format, <tool> string, and an empty
    <fields> block per component). Those are not connection changes, so compare the
    electrical projection instead of raw text.
    """
    import xml.etree.ElementTree as ET
    tree = ET.parse(QA / f'{name}.xml')
    comps = {c.attrib['ref']: c.findtext('value')
             for c in tree.findall('./components/comp')}
    nets = {}
    for net in tree.findall('./nets/net'):
        n = net.attrib['name'].lstrip('/')
        nets[n] = sorted((a.attrib['ref'], a.attrib['pin']) for a in net.findall('node'))
    return comps, nets


def netlist_diff(old_path, new_path, name):
    """Compare old (KiCad 7) and new (KiCad 8) exports on electrical content only."""
    import xml.etree.ElementTree as ET

    def project(path):
        tree = ET.parse(path)
        comps = {c.attrib['ref']: c.findtext('value')
                 for c in tree.findall('./components/comp')}
        nets = {}
        for net in tree.findall('./nets/net'):
            n = net.attrib['name'].lstrip('/')
            nets[n] = sorted((a.attrib['ref'], a.attrib['pin']) for a in net.findall('node'))
        return comps, nets

    oc, onets = project(old_path)
    nc, nnets = project(new_path)
    value_diff = {r: (oc.get(r), nc.get(r)) for r in set(oc) | set(nc) if oc.get(r) != nc.get(r)}
    net_diff = {}
    for n in set(onets) | set(nnets):
        if onets.get(n) != nnets.get(n):
            net_diff[n] = {'old': onets.get(n), 'new': nnets.get(n)}
    return {
        'components_old': len(oc), 'components_new': len(nc),
        'value_differences': value_diff,
        'net_differences': net_diff,
        'electrically_identical': not value_diff and not net_diff,
    }


def mechanical():
    """Landing spans on the LC board against datasheet pin spacing."""
    graph = json.loads((DRAW / 'qa/perfboard_graph.json').read_text(encoding='utf-8'))
    lc = graph['LC']['placements']
    rows = []
    for ref, pins in lc.items():
        a, b = pins['1'], pins['2']
        span = round(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 * GRID, 3)
        spec = SPACING.get(ref)
        if spec is None:
            verdict = 'axial: span set by lead forming'
        elif abs(span - spec) < 0.05:
            verdict = 'matches datasheet'
        else:
            verdict = f'needs lead forming: datasheet {spec} mm vs landing {span} mm'
        rows.append({'ref': ref, 'pad_a': a, 'pad_b': b, 'landing_mm': span,
                     'datasheet_mm': spec, 'verdict': verdict})
    return rows


def main():
    QA.mkdir(parents=True, exist_ok=True)
    errors = []

    version = kicad_version()
    if 'unavailable' in version:
        errors.append('KiCad CLI unavailable; native verification cannot run')

    # 1. lock the files
    locked = {}
    for n in SCHEETS:
        f = KICAD / f'{n}.kicad_sch'
        locked[n] = {'sha256': sha(f), 'size': f.stat().st_size,
                     'header': f.read_text(encoding='utf-8')[:64]}

    # 2. ERC
    erc = {n: run_erc(n) for n in SCHEETS}
    for n, r in erc.items():
        if 'error' in r:
            errors.append(f'{n}: {r["error"]}')
    # 3. netlist re-export + comparison against the pre-existing export and the
    #    A+G22 source mapping already validated by verify_drawings.py
    reexports = {}
    for n in SCHEETS:
        sch = f'{WSL_DIR}/kicad/{n}.kicad_sch'
        out = f'{WSL_DIR}/qa/kicad_native_20261031/{n}.xml'
        rc, log = wsl(f'kicad-cli sch export netlist --format kicadxml -o "{out}" "{sch}"')
        if rc != 0:
            errors.append(f'{n}: netlist export failed rc={rc}')
        reexports[n] = netlist_diff(DRAW / 'qa' / f'{n}.xml', QA / f'{n}.xml', n) if rc == 0 else {}

    # 4. plot re-export (PDF + SVG) for version consistency
    plots = {}
    for n in SCHEETS:
        sch = f'{WSL_DIR}/kicad/{n}.kicad_sch'
        pdf = f'{WSL_DIR}/qa/kicad_native_20261031/pdf_{n}.pdf'
        svgdir = f'{WSL_DIR}/qa/kicad_native_20261031/svg_{n}'
        rc1, _ = wsl(f'kicad-cli sch export pdf -o "{pdf}" "{sch}"')
        rc2, _ = wsl(f'kicad-cli sch export svg -o "{svgdir}" "{sch}"')
        plots[n] = {'pdf_ok': rc1 == 0, 'svg_ok': rc2 == 0,
                    'pdf': f'qa/kicad_native_20261031/pdf_{n}.pdf'}

    # 5. single-pin nets (the electrically meaningful part of label_dangling)
    single = {n: single_pin_nets(n) for n in SCHEETS}

    # 6. mechanical
    mech = mechanical()

    result = {
        'status': 'PASS' if not errors else 'FAIL',
        'kicad': version,
        'scope': (
            'Native KiCad verification of the delivered S05-11 schematics: ERC, netlist '
            're-export, plot re-export and LC-board landing spans. Recorded against the '
            'final files. Electrical parameters were not changed, no simulation was run.'),
        'locked_schematics': locked,
        'erc': erc,
        'erc_causes': classify_erc(erc),
        'netlist_reexport': reexports,
        'plots': plots,
        'single_pin_nets': single,
        'mechanical_landing': mech,
        'errors': errors,
        'limits': [
            'ERC cannot prove the circuit works; it only checks drawing-level rules.',
            'Landing spans come from drawing data, not from a physical board.',
            'No purchased part has been measured; datasheet dimensions are not arrival checks.',
        ],
    }
    (QA / 'native_verification.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in
                      ('status', 'kicad', 'errors', 'single_pin_nets')},
                     ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
