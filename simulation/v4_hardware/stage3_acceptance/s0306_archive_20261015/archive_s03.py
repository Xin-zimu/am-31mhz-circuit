"""Build/verify the S03 evidence index without starting or changing a simulation.

Run with --build to generate the case table and SHA-256 index. The default
verifies the existing index, frozen metrics and twenty spent attempts read-only.
Large waveform files stay at their recorded local locations (not in Git).
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
STAGE = HERE.parent
ROOT = STAGE.parents[2]
ENDPOINTS = STAGE / 's0305_endpoints_20261014'
FINAL2 = STAGE / '副本专用文件夹/final2_20261014'
RUNTIME = Path('D:/ms_xsp/stage3_acceptance/s0305_endpoints_20261014')
INDEX = HERE / 'evidence_manifest.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(value, description):
    if not value:
        raise ValueError(description)


def close(a, b, description):
    require(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), description)


def evidence_checks():
    verdict = read(ENDPOINTS / 'verdict_table.json')
    sources = {r['case']: r for name in ['summary.json', 'resupply_frozen_summary.json']
               for r in read(ENDPOINTS / name)}
    rows = []
    for case in verdict['cases']:
        key = case['case']
        d = case['precharged_5ms_tail'] or case['precharged_2ms_full']
        s = sources[key]
        metric_path = ENDPOINTS / (key + ('_metrics.json' if case['precharged_5ms_tail']
                                          else '_resupply_frozen_metrics.json'))
        metric = read(metric_path)
        derived = {'setting_ratio_error_signed_percent', 'setting_ratio_error_absolute_percent',
                   'normalized_gain_error_percent'}
        require(all(k in s and s[k] == value for k, value in metric.items()) and
                set(s)-set(metric) <= derived, f'{key}: individual metrics differ from summary')
        require(d['tag'] == s['tag'], f'{key}: attempt tag mismatch')
        for dest, source in [('fin_hz', 'input_frequency_hz'), ('fout_hz', 'output_frequency_hz'),
                             ('din_percent', 'input_duty_percent'), ('dout_percent', 'output_duty_percent'),
                             ('last_five_start_s', 'last_five_start_s'), ('last_five_end_s', 'last_five_end_s')]:
            close(d[dest], s[source], f'{key}: {dest}')
        close(d['vin_vpp'], s['nodes']['V(v1)']['robust_vpp'], f'{key}: Vin')
        close(d['vout_vpp'], s['nodes']['V(v2)']['robust_vpp'], f'{key}: Vout')
        close(d['vout_mean_v'], s['nodes']['V(v2)']['mean_v'], f'{key}: mean')
        close(d['gain'], d['vout_vpp']/d['vin_vpp'], f'{key}: gain')
        close(d['frequency_error_percent'], 100*(d['fout_hz']/20000-1), f'{key}: frequency error')
        close(d['duty_error_pp'], d['dout_percent']-d['din_percent'], f'{key}: duty transfer error')
        for field in ['mean_span_percent', 'robust_vpp_span_percent', 'period_span_percent']:
            close(d[field], s['repeatability_screen'][field], f'{key}: {field}')
        require(d['repeatability_screen_passes'] == s['repeatability_screen']['passes'], f'{key}: screen')
        require(d['repeatability_screen_passes'] == all(d[k] <= .1 for k in
                ['mean_span_percent', 'robust_vpp_span_percent', 'period_span_percent']), f'{key}: screen threshold')
        close(d['drift_last_mV_per_ms'], s['drift_windows'][-1]['slope_mV_per_ms'], f'{key}: drift')
        raw = Path(s['raw_path'])
        require(raw.stat().st_size == s['raw_bytes'] and sha(raw) == s['raw_sha256'], f'{key}: raw hash')
        input_dir = FINAL2 if key in ['C4', 'C5'] else ENDPOINTS
        for ext in ['.cir', '.cmd']:
            local = input_dir / (d['tag'] + ext)
            runtime = raw.with_suffix(ext)
            require(sha(local) == sha(runtime), f'{key}: archived/runtime {ext} differ')
        net = (input_dir / (d['tag'] + '.cir')).read_text(encoding='utf-8-sig')
        require(not re.search(r'^\s*\.(include|lib)\b', net, re.I | re.M), f'{key}: external model dependency')
        for component, initial in [('cC111', .43), ('cC115', -4.1), ('cCBB', 4.5)]:
            line = re.search(r'^' + component + r'\b.*$', net, re.I | re.M)
            require(line is not None, f'{key}: missing {component}')
            ic = re.search(r'\bIC\s*=\s*([-+\d.eE]+)', line[0], re.I)
            require(ic is not None, f'{key}: missing initial value')
            close(float(ic[1]), initial, f'{key}: precharge')
        require(len(s['last_five_cycles']) == 5, f'{key}: five complete cycles')
        require(abs(d['frequency_error_percent']) <= 1, f'{key}: frequency threshold')
        require(abs(100*(d['fin_hz']/20000-1)) <= 1, f'{key}: input frequency threshold')
        require(abs(d['din_percent'] - case['target_duty_percent']) <= 5, f'{key}: input duty threshold')
        require(abs(d['duty_error_pp']) <= 5, f'{key}: duty transfer threshold')
        rows.append((case, d, s, metric_path, input_dir))
    require(len(rows) == 7 and set(sources) == {f'C{i}' for i in range(1, 8)}, 'seven cases')
    by_case = {c['case']: d for c, d, *_ in rows}
    # Frozen 6.2 uses normalized gain, not the rounded nominal input ratio.
    linear = 100*(by_case['C5']['gain']/by_case['C4']['gain']-1)
    require(abs(linear) < 10, 'C4/C5 linearity threshold')
    failures = []
    groups = [('C4_4Vpp_D50_5ms', 2), ('C1_1Vpp_D10_5ms', 3), ('C3_4Vpp_D10_5ms', 3),
              ('C6_4Vpp_D30_5ms', 3), ('C7_3Vpp_D50_5ms', 3), ('C2_1Vpp_D50_7ms', 3),
              ('C4_4Vpp_D50_7ms', 3)]
    for base, count in groups:
        for n in range(1, count+1):
            tag = f'{base}_b{n}'
            status_path = ENDPOINTS / (tag + '_status.json')
            status = read(status_path)
            require(status['tag'] == tag and status['status'] in ['EXCEPTION', 'FAILED'], tag + ': status')
            require(status['owned_pids'] and status['raw_bytes'] == 0, tag + ': launched, no data')
            failed_raw = Path(status['raw_path'])
            require(not failed_raw.exists() or failed_raw.stat().st_size == 0, tag + ': nonempty raw')
            command = (RUNTIME / (tag + '.cmd')).read_text(encoding='utf-8-sig')
            source = re.search(r'^\s*source\s+"?([^"\r\n]+)', command, re.M | re.I)
            require(source is not None and Path(source[1].strip()).resolve() ==
                    (RUNTIME / (tag + '.cir')).resolve(), tag + ': command source path')
            failures.append((tag, status_path, status))
    return rows, failures, linear


def case_table(rows, linear):
    lines = ['# S03-06 工况汇总表', '', '日期：2026-10-15。仅汇总已有数据；本轮没有新增仿真或外推。', '',
             'S03-05：**条件性完成，尚未闭合**。判定与完整边界见[阶段验收报告](S03_06_阶段验收报告.md)。', '',
             '## 1. 条件与实际测量窗口', '',
             '所有端点均为预充电：UIC，C111=0.43 V、C115=−4.1 V、CBB=4.5 V。', '',
             '| 用例 | 目标 Vpp / 占空比 | 保存窗口 ms | 末五完整输入周期 ms | 成功尝试标签 |',
             '|---|---|---|---|---|']
    for c, d, s, *_ in rows:
        window = '4.5～5' if c['precharged_5ms_tail'] else '0～2'
        lines.append(f"| {c['case']} | {c['target_vpp']} / {c['target_duty_percent']}% | {window} | "
                     f"{1000*d['last_five_start_s']:.6f}～{1000*d['last_five_end_s']:.6f} | `{d['tag']}` |")
    lines += ['', '**C1/C3/C6/C7 的幅度和均值均为末五完整周期窗口测量值（2 ms 窗口，仍在建立过程）**；不得与 C2/C4/C5 跨窗口作稳态幅度或线性比较。', '',
              '## 2. 频率与占空比', '',
              '频率误差 = 100×(fout/20 kHz−1)。输入占空比误差 = Din−目标（对应评分要求）；传递误差 = Dout−Din（历史端点表的 0.060～0.231 pp 指此列）。两者分列，不互换定义。', '',
              '| 用例 | fin Hz | fout Hz | 输出频率误差 % | Din % | Dout % | 输入占空比误差 pp | 传递误差 pp |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for c, d, *_ in rows:
        lines.append(f"| {c['case']} | {d['fin_hz']:.6f} | {d['fout_hz']:.6f} | {d['frequency_error_percent']:+.6f} | "
                     f"{d['din_percent']:.6f} | {d['dout_percent']:.6f} | {d['din_percent']-c['target_duty_percent']:+.6f} | {d['duty_error_pp']:+.6f} |")
    lines += ['', '七组输入与输出频率均在 20 kHz 的 1% 范围内；输入占空比误差与传递误差均小于 5 pp。历史 ≤0.052% / ≤0.231 pp 为保守上界，余量仍至少 19 倍 / 21 倍；不宣称重复运行统计。', '',
              '## 3. 幅度、均值、重复性筛查与漂移（必须同报）', '',
              '幅度采用 2 ns 均匀插值后的 P98−P2；均值为梯形积分时间加权均值。跨度列均取末五完整周期；0.1% 是工程筛查，非评分指标。漂移列取已保存 drift_windows 的末四个窗口，按时间顺序列出。', '',
              '| 用例 | Vin Vpp | Vout Vpp | Vout 均值 V | 均值跨度 % | 幅度跨度 % | 周期跨度 % | 筛查 |',
              '|---|---:|---:|---:|---:|---:|---:|---|']
    for c, d, *_ in rows:
        lines.append(f"| {c['case']} | {d['vin_vpp']:.6f} | {d['vout_vpp']:.6f} | {d['vout_mean_v']:.6f} | "
                     f"{d['mean_span_percent']:.6f} | {d['robust_vpp_span_percent']:.6f} | {d['period_span_percent']:.6f} | "
                     f"{'通过' if d['repeatability_screen_passes'] else '未通过'} |")
    lines += ['', '| 用例 | 末四个漂移窗口覆盖范围 ms | 局部漂移速率序列 mV/ms | 解释 |', '|---|---|---|---|']
    for c, d, s, *_ in rows:
        w = s['drift_windows'][-4:]
        seq = ' → '.join(f"{v['slope_mV_per_ms']:.4f}" for v in w)
        note = '局部正负波动，不构成单调衰减证据' if c['case'] == 'C4' else '所列末段速率下降，偏置仍上升'
        lines.append(f"| {c['case']} | {w[0]['start_s']*1000:.6f}～{w[-1]['end_s']*1000:.6f} | {seq} | {note} |")
    lines += ['', '末段趋势不推广为整个启动过程单调。C5 虽通过末五周期筛查，仍有约 9.96 mV/ms 漂移；C4/C5 均不称“完全稳定”。C2 未通过筛查，7 ms 没有新数据。', '',
              '## 4. 线性度及幅度门槛', '',
              f'冻结 6.2 归一化增益公式：100×[(Vout/Vin)C5 ÷ (Vout/Vin)C4−1] = **{linear:.7f}%**，四舍五入 **−1.4435%**，绝对值小于 10%。仅适用于预充电 5 ms 尾段 C4/C5 对照。', '',
              '既有 verdict_table.json 的线性项使用名义输入减半公式，未舍入值为 −1.4434826054%；冻结归一化增益公式的微小差别来自实测 Vin 并非数学上精确 1/2。两者都舍入为 −1.4435%，判定不变。', '',
              '1/3 Vpp 线性核对仍未完成。C4 的已验收标称窗口 Vout=4.816023 Vpp，满足该操作点的 ≥4 V 数值门槛；C3/C6 的窗口幅度大于 4 V 不能关闭其稳态缺口。门槛适用的输入档位解释仍按原计划保留。', '',
              '## 5. 数据来源', '',
              '以下指标文件与 summary/resupply_frozen_summary、verdict_table 已逐项核对；原始波形 SHA-256、实际网表和命令位置见 [evidence_manifest.json](evidence_manifest.json)。', '']
    for c, d, s, metric, *_ in rows:
        lines.append(f"- {c['case']}：[{metric.name}](../s0305_endpoints_20261014/{metric.name})；原始点数 {s['points']:,}。")
    lines += ['', '**2026-10-15 长窗补测：20 次有效尝试，0 次成功，无新数据。** 这批运行没有筛查或漂移结果；不得把它写成“筛查未通过”。', '']
    return '\n'.join(lines)


def build(rows, failures, linear):
    (HERE / 'S03_06_工况汇总表.md').write_text(case_table(rows, linear), encoding='utf-8', newline='\n')
    entries = {}

    def add(path, role, expected=None):
        path = path.resolve()
        require(path.is_file(), 'Missing evidence: ' + str(path))
        digest = sha(path)
        if expected:
            require(digest.lower() == expected.lower(), 'Historical hash mismatch: ' + str(path))
        local = path.is_relative_to(ROOT)
        location = path.relative_to(ROOT).as_posix() if local else path.as_posix()
        entry = entries.setdefault(location, {'path': location, 'storage': 'workspace' if local else 'external_local',
                                             'bytes': path.stat().st_size, 'sha256': digest, 'roles': []})
        if role not in entry['roles']:
            entry['roles'].append(role)
        if expected:
            entry['historical_sha256_match'] = True

    baseline_paths = ['simulation/v4_hardware/AM_20k_31MHz_V4_3_REPAIRED.ms14',
                      'simulation/v4_hardware/repair_20261011/final_actual.cir',
                      'simulation/v4_hardware/AM_20k_31MHz_V4_3_REPAIRED.gra',
                      '设计.docx', '电子线路实验评分标准-学生.docx', '性能指标要求_N31_M50.md']
    for path, old in zip(baseline_paths, read(STAGE/'baseline_manifest.json')['sources'], strict=True):
        add(ROOT/path, 'baseline/source', old['sha256'])
    for name in ['S03_BASELINE_V4_3.ms14', 'S03_GUI_2ms_V4_3.ms14', 'S03_GUI_2ms_V4_3.gra',
                 'S03_GUI_2ms_V4_3.npz', 'S03_GUI_2ms_V4_3_metrics.json', 'S03_GUI复跑报告.md',
                 'gui_project_audit.json', 'gui_engine_comparison.json', 'baseline_manifest.json',
                 'nominal_full.cir', 'nominal_5ms.cmd', 'nominal_5ms.log', 'nominal_5ms.npz',
                 'nominal_5ms_metrics.json', 'measure_stage3.py', 'S03_指标与测量定义.md',
                 'S03_04_冷启动排查记录.md']:
        add(STAGE/name, 'S03 baseline/GUI/method')
    require(sha(STAGE/'S03_BASELINE_V4_3.ms14') == sha(ROOT/baseline_paths[0]), 'stage baseline copy')
    add(ROOT/'simulation/v4_hardware/repair_20261011/final_reopen.net.txt', 'existing native reopen evidence')
    for path in (ROOT/'simulation/v4_hardware/models').rglob('*'):
        if path.is_file() and path.suffix.lower() == '.lib':
            add(path, 'model source/reference; actual embedded model in netlist governs')
    for c, d, s, metric, input_dir in rows:
        add(Path(s['raw_path']), c['case'] + ' original waveform', s['raw_sha256'])
        add(metric, c['case'] + ' frozen metrics')
        for suffix in ['.cir', '.cmd', '.log', '_status.json']:
            add(input_dir/(d['tag']+suffix), c['case'] + ' selected attempt')
    for name in ['summary.json', 'resupply_frozen_summary.json', 'verdict_table.json', 'evidence_audit.json',
                 'run_manifest.json', 'analyze_cases.py', 'analyze_resupply_frozen.py', 'analyze_longwindow_frozen.py',
                 'build_verdict.py', 'check_verdict_consistency.py', 'run_one.ps1', 'run_budget.ps1',
                 '生成补测用例.ps1', 'S03_05_汇总与判定.md', 'S03_05_长窗补测批次记录.md',
                 'S03_05_长窗补测交接.md', 'S03_05_失败取证分析报告.md', '运行异常记录.md',
                 '补测批次作废记录_C4_b1b2.md', 'README.md']:
        add(ENDPOINTS/name, 'S03-05 method/status/provenance')
    failure_inputs = HERE/'failed_attempt_inputs'
    failure_inputs.mkdir(exist_ok=True)
    for tag, status_path, status in failures:
        add(status_path, 'effective failed attempt; no measurement')
        add(ENDPOINTS/(tag+'.log'), 'effective failed attempt log')
        if Path(status['raw_path']).exists():
            add(Path(status['raw_path']), 'empty failure output; not measurement')
        for ext in ['.cir', '.cmd']:
            source = RUNTIME/(tag+ext)
            dest = failure_inputs/source.name
            if dest.exists():
                require(sha(dest) == sha(source), 'Refusing overwrite of differing archived input: '+tag)
            else:
                shutil.copyfile(source, dest)
            add(dest, 'effective failed attempt input copied unchanged from '+source.as_posix())
    # Retain full inherited boundary evidence alongside the final 12 ms data.
    aux = STAGE/'副本专用文件夹'
    for name in ['cold_7ms_1ns.npz', 'mmraw.py']:
        add(aux/name, 'S03-04 7 ms numerical archive/parser')
    for name in ['L_7ms_1ns.cir', 'L_7ms_1ns.cmd']:
        add(aux/'engine'/name, 'S03-04 7 ms input')
    for folder in ['cold12ms_20261014', 'cold9ms_20261014', 'gui_evidence_20261014']:
        for path in (aux/folder).iterdir():
            if path.is_file() and (path.suffix in ['.md', '.json', '.py', '.ms14', '.cir', '.cmd', '.gra']):
                add(path, 'S03-04 inherited evidence')
    nine_status = read(aux/'cold9ms_20261014/COLD_9ms_tail_status.json')
    add(Path(nine_status['raw_path']), 'S03-04 9 ms raw; hash recorded at archive')
    cold12 = read(aux/'cold12ms_20261014/cold12ms_analysis.json')['twelve']
    status = read(FINAL2/'COLD_12ms_clean_status.json')
    add(Path(status['raw_path']), 'S03-04 12 ms raw', cold12['sha256'])
    for suffix in ['.cir', '.cmd', '.log', '_status.json']:
        add(FINAL2/('COLD_12ms_clean'+suffix), 'S03-04 12 ms successful attempt')
    for path in HERE.iterdir():
        if path.suffix in ['.md', '.py'] or path.name == '.gitattributes':
            add(path, 'S03-06 deliverable')
    manifest = {'date': '2026-10-15', 'decision': 'A, scope confirmed in current user conversation',
                's0305_status': '条件性完成，尚未闭合', 's0306_status': '受限验收报告与归档完成',
                's03_status': '待验收/受限；不标为整体已验收', 'new_simulations': 0,
                'new_extrapolations': 0, 'measured_cases': 7, 'effective_longwindow_attempts': 20,
                'longwindow_successes': 0, 'longwindow_measurement_status': '无数据可报',
                'frozen_normalized_gain_error_percent': linear,
                'failed_outputs': [{'tag': tag, 'raw_path': Path(s['raw_path']).as_posix(),
                                    'status_raw_bytes': s['raw_bytes'],
                                    'file_present_at_archive': Path(s['raw_path']).exists(),
                                    'measurement_status': '无数据可报'} for tag, _, s in failures],
                'storage_policy': 'In-place local archive. Git omits large waveforms; preserve every indexed external/local binary separately when migrating.',
                'files': sorted(entries.values(), key=lambda e: e['path'])}
    INDEX.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def verify():
    manifest = read(INDEX)
    for row in manifest['failed_outputs']:
        require(Path(row['raw_path']).exists() == row['file_present_at_archive'],
                'Failed output presence changed: '+row['tag'])
    for row in manifest['files']:
        path = ROOT/row['path'] if row['storage'] == 'workspace' else Path(row['path'])
        require(path.is_file() and path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],
                'Archive mismatch: '+row['path'])
    return {'status': 'PASS', 'indexed_files': len(manifest['files']), 'frozen_cases_checked': 7,
            'effective_failed_attempts_checked': 20, 'new_simulations': 0,
            'verification_scope': 'Hashes/provenance/metric consistency only; no solver replay or new acceptance evidence'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--record', action='store_true', help='Save the verification result, without changing evidence')
    args = parser.parse_args()
    rows, failures, linear = evidence_checks()
    if args.build:
        build(rows, failures, linear)
    result = verify()
    if args.record:
        (HERE/'verification_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, ensure_ascii=False))
