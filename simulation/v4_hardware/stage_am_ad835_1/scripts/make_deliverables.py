"""Build the Stage AM-AD835.1 delivery tables from the stored JSON results.

Nothing here re-runs a solver; every number is read from results/*.json that was
produced by rf_study.py / extra_rf.py / baseband_study.py.

The envelope arithmetic in section 5 is IDEAL-MULTIPLIER ARITHMETIC applied to
MEASURED interface waveforms. It is not an AD835 simulation and is labelled so.
"""
from pathlib import Path
import csv, json, math
import numpy as np
import rf_study as L

ROOT = L.ROOT
RES = ROOT / 'results'
OUT = ROOT / 'results'

LOAD_ORDER = [('load_500_4p', '500 Ω ∥ 4 pF'), ('load_600_4p', '600 Ω ∥ 4 pF'),
              ('load_700_4p', '700 Ω ∥ 4 pF'), ('load_800_4p', '800 Ω ∥ 4 pF'),
              ('load_900_4p', '900 Ω ∥ 4 pF'), ('load_1k_4p', '1 kΩ ∥ 4 pF'),
              ('load_2k_4p', '2 kΩ ∥ 4 pF'), ('load_2k_10p', '2 kΩ ∥ 10 pF (original C4)'),
              ('load_3k3_4p', '3.3 kΩ ∥ 4 pF'), ('load_10k_4p', '10 kΩ ∥ 4 pF'),
              ('load_37k5_4p', '37.5 kΩ ∥ 4 pF (Y/Z typical RC)'),
              ('load_50k_4p', '50 kΩ ∥ 4 pF'), ('load_100k_4p', '100 kΩ ∥ 4 pF')]

# candidate -> (Chinese name, [(result basename, displayed topology label)])
CANDIDATES = [
    ('A', 'A 被动衰减与偏置回路', [('A_nom', 'A 330Ω/680Ω 共节点'),
                                    ('A560_nom', 'A 560Ω/680Ω 共节点'),
                                    ('A470_nom', 'A 470Ω/680Ω 共节点'),
                                    ('SA_510_680', 'A 510Ω/680Ω 定尺'),
                                    ('SA_430_680', 'A 430Ω/680Ω 定尺'),
                                    ('SA_390_620', 'A 390Ω/620Ω 定尺'),
                                    ('SA_330_620', 'A 330Ω/620Ω 定尺'),
                                    ('A470_AMB', 'A 470Ω/680Ω + Z独立偏置')]),
    ('B', 'B 射频缓冲后再驱动Y/Z', [('B_nom', 'B 射随缓冲 Y=Z=Vc'),
                                     ('B_Z06_nom', 'B 射随缓冲 Y=Vc, Z=0.6Vc')]),
    ('C', 'C 分别控制Y和Z', [('C_A_nom', 'C 双分支 Z串330Ω'),
                              ('C_B_nom', 'C 双分支 Z串1kΩ')]),
]
ENVELOPE_CASES = [('A470_nom', 'A470'), ('A560_nom', 'A560'), ('A_nom', 'A'),
                  ('A470_AMB', 'A470+Z偏置'), ('B_nom', 'B Y=Z'),
                  ('B_Z06_nom', 'B Y=Vc/Z=0.6Vc'), ('C_A_nom', 'C_A'), ('C_B_nom', 'C_B'),
                  ('SA_330_620', 'A 330/620 定尺'), ('SA_390_620', 'A 390/620 定尺'),
                  ('SA_430_680', 'A 430/680 定尺'), ('SA_510_680', 'A 510/680 定尺')]
SIZING = ['SA_330_620', 'SA_390_620', 'SA_430_680', 'SA_470_620', 'SA_510_680', 'SA_560_680',
          'SA_390_680', 'A470_nom', 'A560_nom', 'A_nom']


ORIGINAL_C4_MW = 42.778   # load_2k_10p: the un-modified C4 carrier module


def load(name):
    p = RES / f'{name}.json'
    return json.loads(p.read_text(encoding='utf8')) if p.exists() else None


def peak(v):
    return max(abs(v['min']), abs(v['max']))


def rows_of(name):
    j = load(name)
    if j is None:
        return None
    return dict(
        name=name, f_mhz=j['frequency_hz'] / 1e6,
        tp2_vpp=j['out']['vpp'], tp2_min=j['out']['min'], tp2_max=j['out']['max'],
        y_vpp=j['y']['vpp'], y_min=j['y']['min'], y_max=j['y']['max'],
        z_vpp=j['z']['vpp'], z_min=j['z']['min'], z_max=j['z']['max'],
        y_dc=j['y']['dc'], z_dc=j['z']['dc'],
        y_thd=j['y']['thd'], z_thd=j['z']['thd'],
        y_ph=j['y_phase_relative_tp2_deg'], z_ph=j['z_phase_relative_y_deg'],
        ratio=j['z_y_amplitude_ratio'],
        zin_re=j['interface_zin_ohm'][0], zin_im=j['interface_zin_ohm'][1],
        mw=j['supply_mw'], y_peak=peak(j['y']), z_peak=peak(j['z']),
        drift=j['last_window_drift'])


# --------------------------------------------------------------------------- 1
def table_load_sweep():
    out = []
    for name, label in LOAD_ORDER:
        r = rows_of(name)
        if not r:
            continue
        out.append({
            '负载': label, 'run': name,
            'TP2_Vpp': round(r['tp2_vpp'], 4), 'TP2_min_V': round(r['tp2_min'], 4),
            'TP2_max_V': round(r['tp2_max'], 4),
            '峰值绝对值_V': round(r['y_peak'], 4),
            '基波_THD_%': round(r['y_thd'] * 100, 2),
            '频率_MHz': round(r['f_mhz'], 4),
            '供电_mW': round(r['mw'], 3),
            '末窗漂移': f"{r['drift']:.2e}",
            '超过标称±1V': 'YES' if r['y_peak'] > 1.0 else 'no',
        })
    return out


# --------------------------------------------------------------------------- 2
def table_candidates():
    out = []
    for cid, cname, tops in CANDIDATES:
        for rname, label in tops:
            r = rows_of(rname)
            if not r:
                continue
            out.append({
                '方案': cid, '拓扑说明': label, 'run': rname,
                'TP2_Vpp': round(r['tp2_vpp'], 4),
                'Y_Vpp': round(r['y_vpp'], 4), 'Y峰值_V': round(r['y_peak'], 4),
                'Z_Vpp': round(r['z_vpp'], 4), 'Z峰值_V': round(r['z_peak'], 4),
                'Z/Y幅度比': round(r['ratio'], 4),
                'Y相对TP2相位_deg': round(r['y_ph'], 3),
                'Z相对Y相位_deg': round(r['z_ph'], 3),
                'Y直流_V': round(r['y_dc'], 5), 'Z直流_V': round(r['z_dc'], 5),
                'Y基波THD_%': round(r['y_thd'] * 100, 2),
                'Z基波THD_%': round(r['z_thd'] * 100, 2),
                '接口Zin_re': round(r['zin_re'], 1), '接口Zin_im': round(r['zin_im'], 1),
                '载波模块_mW': round(r['mw'], 3),
                '相对原C4载波_mW': round(r['mw'] - ORIGINAL_C4_MW, 3),
                'Y在±1V内': 'yes' if r['y_peak'] <= 1.0 else 'NO',
            })
    return out


# --------------------------------------------------------------------------- 3
def table_baseband():
    out = []
    order = [('bare', '1 裸源（仅1MΩ）'), ('passive', '1 直接电阻网络'),
             ('post', '2 电阻网络+后置缓冲'), ('prepost', '3 前后双缓冲')]
    # the unloaded source amplitude comes from the bare runs
    vm_unloaded = {}
    for a in (1, 2, 3, 4):
        j = load(f'bb_bare_a{a}_d10')
        if j:
            vm_unloaded[a] = j['vm_high'] - j['vm_low']
    for typ, label in order:
        for a in (1, 2, 3, 4):
            for d in (10, 30, 50):
                j = load(f'bb_{typ}_a{a}_d{d}')
                if not j:
                    continue
                vpp = j['vm_high'] - j['vm_low']
                droop = (vpp / vm_unloaded[a] - 1) if a in vm_unloaded and vm_unloaded[a] else 0.0
                # X error against a target built from the UNLOADED source amplitude
                tgt_lo = 0.105 * (j['vm_low'] / (1 + droop) if droop != -1 else j['vm_low']) - 0.42
                tgt_hi = 0.105 * (j['vm_high'] / (1 + droop) if droop != -1 else j['vm_high']) - 0.42
                xe = max(abs(j['x_low'] - tgt_lo), abs(j['x_high'] - tgt_hi))
                out.append({
                    '电路': label, 'topology': typ, '幅度档A': a, '占空比D%': d,
                    'Vm_Vpp': round(vpp, 5), '源幅度跌落_%': round(droop * 100, 3),
                    'X低_V': round(j['x_low'], 5), 'X高_V': round(j['x_high'], 5),
                    'X平台误差_mV': round(j['plateau_max_error_v'] * 1000, 3),
                    'X对未加载目标误差_mV': round(xe * 1000, 2),
                    '全波形最大误差_mV': round(j['max_total_waveform_error_v'] * 1000, 1),
                    '边沿1%建立_µs': None if j['settling_1pct_own_plateau_s'] is None
                    else round(j['settling_1pct_own_plateau_s'] * 1e6, 3),
                    'X_min_V': round(j['x_min'], 5), 'X_max_V': round(j['x_max'], 5),
                    '正轨附加_mW': round(j['positive_extra_mw'], 3),
                    '负轨附加_mW': round(j['negative_extra_mw'], 3),
                })
    return out


# --------------------------------------------------------------------------- 4
def table_power():
    """Power delta versus the un-modified C4 carrier module.

    The two baseband rows are a DIFFERENT subsystem (LM393 front end), so their
    delta is measured against the bare baseband run, never against the carrier.
    """
    base = rows_of('load_2k_10p')['mw']      # original C4 load, no interface
    bb_base = load('bb_bare_a1_d10')['source_mw']
    out = []
    for cid, cname, tops in CANDIDATES:
        for rname, label in tops:
            r = rows_of(rname)
            if not r:
                continue
            out.append({'项目': f'{cid} | {label}', '载波模块_mW': round(r['mw'], 3),
                        '相对原C4载波_mW': round(r['mw'] - base, 3)})
    for typ, label in (('post', '2 电阻网络+后置缓冲'), ('prepost', '3 前后双缓冲')):
        j = load(f'bb_{typ}_a4_d10')
        if j:
            out.append({'项目': f'基带 | {label}（LM393 前端，基准不同于载波）',
                        '载波模块_mW': round(j['source_mw'], 3),
                        '相对原C4载波_mW': round(j['source_mw'] - bb_base, 3)})
            out[-1]['正负轨附加_mW'] = round(j['positive_extra_mw'] + j['negative_extra_mw'], 3)
    return out, base, bb_base


# --------------------------------------------------------------------------- 5  sizing
def table_sizing():
    out = []
    for n in SIZING:
        r = rows_of(n)
        if not r:
            continue
        j = json.loads((RES / f'{n}.json').read_text(encoding='utf8'))
        out.append({
            'run': n, 'RS_ohm': j.get('rs'), 'RP_ohm': j.get('rp'),
            'TP2_Vpp': round(r['tp2_vpp'], 4),
            'Y_Vpp': round(r['y_vpp'], 4), 'Y峰值_V': round(r['y_peak'], 4),
            'Z_Vpp': round(r['z_vpp'], 4),
            'Y直流_V': round(r['y_dc'], 5),
            'Y基波THD_%': round(r['y_thd'] * 100, 2),
            'Z相对Y相位_deg': round(r['z_ph'], 3),
            '载波模块_mW': round(r['mw'], 3),
            'Y在±1V内': 'yes' if r['y_peak'] <= 1.0 else 'NO',
        })
    return out


# --------------------------------------------------------------------------- 6  envelope arithmetic
U = 1.05


def envelope_arith(name, convention, label=None):
    """Ideal-multiplier arithmetic on the measured interface waveform.

    convention 'A': X = 0.105*Vm - 0.42 (bipolar)  -> Z must equal Y
    convention 'B': X = 0.105*Vm       (unipolar)  -> Z must be 0.6*Y
    Amplitude-only: the measured Z/Y phase error is used as a range bound.
    """
    r = rows_of(name)
    if not r:
        return None
    ay, az = r['y_peak'], r['z_peak']
    dphi = math.radians(r['z_ph'])
    vm_lo, vm_hi = 0.0748175, 4.0748183          # original LM393 baseband, stage AM
    if convention == 'A':
        xl, xh = 0.105 * vm_lo - 0.42, 0.105 * vm_hi - 0.42
    else:
        xl, xh = 0.105 * vm_lo, 0.105 * vm_hi
    # worst case of the phasor sum Y*X/U + Z (Z lags by dphi)
    def wpp(x):
        a = ay * x / U
        return 2 * math.sqrt(a * a + az * az + 2 * a * az * math.cos(dphi))
    wh, wl = wpp(xh), wpp(xl)
    m = (wh - wl) / (wh + wl) if (wh + wl) else 0
    return dict(name=name, label=label or name, convention=convention, Y_peak=ay, Z_peak=az,
                Z_over_Y=r['ratio'], Z_phase_rel_Y_deg=r['z_ph'],
                W_high_vpp=wh, W_low_vpp=wl, modulation=100 * m,
                meets_2v0_1v2=bool(wh >= 1.995 and wl <= 1.205 and wl >= 1.195),
                y_peak_within_1v=bool(ay <= 1.0))


if __name__ == '__main__':
    def dump(fn, rows, fields):
        with (OUT / fn).open('w', newline='', encoding='utf-8-sig') as f:
            wr = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            wr.writeheader()
            wr.writerows(rows)
        print(fn, len(rows), 'rows')

    sz = table_sizing()
    dump('A方案衰减器定尺扫描.csv', sz, list(sz[0].keys()))

    ls = table_load_sweep()
    dump('TP2负载扫描.csv', ls, list(ls[0].keys()))

    cand = table_candidates()
    dump('接口候选汇总.csv', cand, list(cand[0].keys()))

    bb = table_baseband()
    dump('基带电平转换对比.csv', bb, list(bb[0].keys()))

    pw, base, bb_base = table_power()
    (OUT / 'power_baselines.json').write_text(json.dumps(
        dict(original_C4_carrier_mw=base, original_LM393_mw=bb_base), indent=2), encoding='utf8')
    allf = ['项目', '载波模块_mW', '相对原C4载波_mW', '正负轨附加_mW']
    dump('功耗预算变化.csv', pw, allf)

    ar = []
    for rname, label in ENVELOPE_CASES:
        for conv in ('A', 'B'):
            e = envelope_arith(rname, conv, label)
            if e:
                ar.append(e)
    (OUT / 'envelope_arithmetic.json').write_text(json.dumps(ar, indent=2), encoding='utf8')
    print('\n--- ideal-multiplier envelope arithmetic on measured waveforms ---')
    for e in ar:
        print(f"{e['label']:16s} conv{e['convention']} Yp={e['Y_peak']:.3f} Zp={e['Z_peak']:.3f} "
              f"Wh={e['W_high_vpp']:.3f} Wl={e['W_low_vpp']:.3f} m={e['modulation']:5.2f}% "
              f"{'MEETS' if e['meets_2v0_1v2'] else '      '}")
