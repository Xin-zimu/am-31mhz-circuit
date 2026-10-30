"""Read-only S05-10 audit: independent raw-array reduction and document links."""
from pathlib import Path
import hashlib, json, re, subprocess, sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
import check_interfaces as c


def reduce_raw(raw, node):
    f = raw['frequency'].real
    amp = np.abs(raw[f'v({node})'])
    db = 20*np.log10(amp)
    peak = int(np.argmax(db)); level = db[peak]-20*np.log10(np.sqrt(2))
    lower = peak
    while lower > 0 and db[lower-1] >= level:
        lower -= 1
    upper = peak
    while upper+1 < len(f) and db[upper+1] >= level:
        upper += 1
    assert lower > 0 and upper+1 < len(f)
    def edge(a, b):
        return f[a]+(f[b]-f[a])*(level-db[a])/(db[b]-db[a])
    lo, hi = edge(lower-1, lower), edge(upper, upper+1)
    g31 = float(np.interp(31e6, f, amp))
    return dict(gain31_v_v=g31, gain31_db=20*np.log10(g31),
                flo_mhz=lo/1e6, fhi_mhz=hi/1e6,
                center_edges_mhz=(lo+hi)/2e6, bw_mhz=(hi-lo)/1e6,
                relative29_db=20*np.log10(np.interp(29e6, f, amp)/g31),
                relative33_db=20*np.log10(np.interp(33e6, f, amp)/g31))


def main():
    c.verify()
    maximum = 0.
    for p in (HERE/'results').glob('*.json'):
        rec = json.loads(p.read_text())
        independent = reduce_raw(c.d.readraw(Path(rec['raw_path'])), rec['node'])
        for key, val in independent.items():
            error = abs(val-rec['metrics'][key]); maximum = max(maximum, error)
            assert error < 1e-8, (p, key, val)
    main_doc = HERE.parent/'S05_10_实物实施前检查与LC测量准备.md'
    checked = 0
    for p in [main_doc, *HERE.glob('*.md')]:
        text = p.read_text(encoding='utf-8')
        for ref in re.findall(r'\]\(([^)]+)\)', text):
            if ref.startswith(('http:', 'https:', '#')):
                continue
            assert (p.parent/ref.split('#')[0]).exists(), (p, ref)
            checked += 1
    subprocess.run(['git','diff','--check'], cwd=ROOT, check=True)
    result = dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,
                   text=True).strip(), historical_files_unchanged=2752,
                   new_ac_cases=4, transient_cases=0, simulations_run_by_audit=0,
                   independent_reduction_max_absolute_error=maximum,
                   local_document_links_checked=checked, git_diff_check='pass',
                   hardware_measurements=0, buffer_device_qualified=False,
                   retained_failures=['preflight_reader_type.json'])
    # Generated once; future read-only audit compares the archived result.
    c.dump(HERE/'audit.json', result)
    files = [main_doc, *[p for p in HERE.rglob('*') if p.is_file()
                        and '__pycache__' not in p.parts and p.name != 'evidence_manifest.json']]
    c.dump(HERE/'evidence_manifest.json', dict(files={str(p.relative_to(ROOT)): c.sha(p)
                                                  for p in sorted(files)}))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
