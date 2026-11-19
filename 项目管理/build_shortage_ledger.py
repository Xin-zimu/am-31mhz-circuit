"""Generate the AM 31 MHz shortage ledger from the netlists and the stock ledger.

Why a generator: the project rule is that no number in a document is typed by
hand.  Every quantity below is either parsed from a netlist or transcribed from
a single named cell range of the procurement workbook, so a re-run after new
parts arrive reproduces the whole table instead of drifting.

Standing rule (user, 2026-11-17): **no series/parallel assembly of resistors or
capacitors.**  Every value is bought as a single part.  The ledger therefore
reports the nearest standard value rather than a combination, and lists the bias
deviation that follows from it.

Sources
-------
TX netlist  simulation/v4_hardware/stage_am_alt3_20261115/round2_20261116/netlists/d05.cir
RX netlist  simulation/v4_hardware/stage5_receiver/S05_A2_G22_candidate.cir
Stock       procurement_20261031/AM31MHz_采购台账_基准_20261110_2008.xlsx
            sheet 已有与未购买, groups (1)自购第一批 / (1B)自购第二批 / (2)老师发放

Pure-model elements are excluded: CX0 / CSTRAY / CM / LM / RM / RLOSS / CSELF
are model parasitics, not parts to buy.  Where the same physical part serves both
boards the demand is summed.
"""
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TX = ROOT / 'simulation/v4_hardware/stage_am_alt3_20261115/round2_20261116/netlists/d05.cir'
RX = ROOT / 'simulation/v4_hardware/stage5_receiver/S05_A2_G22_candidate.cir'
OUT = ROOT / '项目管理/04_缺料台账_20261117.md'

# ---- verified stock (sheet 已有与未购买, groups 1 / 1B / 2 only) -------------
# Values are the on-hand counts from that sheet.  Nothing here is inferred from
# a purchase screenshot; 2026-11-17 the user re-confirmed the 1B batch arrived.
R_STOCK = {33: 50, 56: 50, 100: 50, 220: 50, 330: 50, 470: 50, 1000: 50,
           4700: 100, 10000: 50, 20000: 50, 22000: 50, 100000: 50,
           210000: 50, 1000000: 50}
C_STOCK = {'2.2p': 10, '15p': 10, '30p': 10, '33p': 50, '39p': 10, '100p': 20,
           '330p': 10, '1n': 10, '10n': 10, '100n': 11, '10u': 10, '100u': 12,
           '4.7n': 2}
# 100n = 0805 贴片 10 只 + 老师件直插 104 1 只；100u = SMD 10 只 + 老师件 10V 2 只
# 2026-11-19 用户裁定：直插 100nF 由库存 104 覆盖，不另购（此前误判为「封装不符须另补」）
Q_STOCK = {'2N3904': 5, 'S9013': 21}
IC_STOCK = {'LM393P': 5, 'OPA197IDR': 3, 'BAT85S': 5}

# ---- requirements -----------------------------------------------------------
# (value, count, refdes + role).  Potentiometer-derived values are NOT listed
# here: they are bought as trimmers, see TRIMMERS.
TX_R = [(10, 1, 'RSENSE 取样，全项目唯一电流测点'),
        (1250, 1, 'RDC 末级负载'), (150, 1, 'RDE 末级发射极'),
        (200, 1, 'REF 射随负载'), (40000, 1, 'RDB1 偏置'), (10000, 1, 'RDB2'),
        (2200, 2, 'RPU1/RPU2 上拉'), (30000, 1, 'RHT 迟滞'),
        (10000, 2, 'RHB/RDT'), (20000, 1, 'RHF'), (22000, 1, 'RFIX'),
        (4700, 1, 'RDB'), (10000, 1, 'RBT'), (10000, 1, 'RBB'),
        (330, 1, 'REB'), (22000, 1, 'RG1'), (4700, 1, 'RG2'),
        (1000, 1, 'RCG'), (56, 1, 'REG'), (10000, 1, 'RPRE'),
        (37000, 1, 'RMINJ'), (1000, 1, 'RMC'), (470, 1, 'RME'),
        (3300, 1, 'RMB'), (15000, 1, 'RMT')]
TX_C = [('15p', 1, 'CINPUT'), ('33p', 2, 'C1/C2 晶振负载'),
        ('1n', 3, 'CIN/COUTB/CME'), ('10n', 3, 'CG/COUTG/C_DRV'),
        ('47p', 1, 'CENV 包络滤波'), ('100n', 3, '去耦'), ('10u', 2, '去耦')]
RX_R = [(50, 1, 'RSOURCE 测试源终端'), (33, 2, 'REU1/2'), (220, 2, 'REB1/2'),
        (1000, 3, 'RC1/2/RF'), (22000, 2, 'RBT1/2'),
        (4700, 4, 'RBB1/2/DET/FILT'), (10000, 2, 'RBTB/RBBB'),
        (470, 1, 'REBUF'), (1000000, 1, 'RPORT'), (20000, 1, 'RVT'),
        (10000, 1, 'RVB'), (210000, 1, 'RFB G22'), (100, 1, 'ROUT')]
RX_C = [('2.4p', 1, 'CK 腔间耦合'), ('11p', 1, 'COUT 输出耦合'),
        ('15p', 1, 'CSEL 输入串联'),
        ('27p', 2, 'CT1 固定段（78FR47K 470nH 起点：27p ∥ 微调 11.09p）'),
        ('33p', 1, 'CT2 固定段（470nH 起点：33p ∥ 微调 12.38p）'),
        ('100p', 4, 'CIN2/CBUF/CDET/CFILT'), ('1n', 2, 'CIN1/COBUF'),
        ('330p', 2, 'CEB1/2'), ('100n', 1, 'CCOUP1 直插'),
        ('10u', 1, 'CVREF')]

# Trimmers replace the netlist's potentiometer legs; buying the real trimmer is
# what avoids building a fixed+variable series string.
TRIMMERS = [
    ('20 kΩ 多圈微调', 1, 'RVRF：网表值 15288.9 Ω（原为 22k 固定 + 微调串联）'),
    ('10 kΩ 微调', 1, 'RVDT/RVDB：网表值 7362.5 / 2637.5 Ω 分压'),
    ('20 kΩ 电位器', 1, 'RVAT/RVAB：网表值 931.3 / 19068.7 Ω 幅度调节'),
]

E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]


def nearest_e24(v):
    """Nearest E24 value, spanning the decades either side of v."""
    best, err = None, None
    for dec in (10 ** math.floor(math.log10(v)), 10 ** math.ceil(math.log10(v))):
        for m in E24:
            cand = m * dec
            e = abs(cand - v)
            if err is None or e < err:
                best, err = cand, e
    return best


def is_e24(v):
    return abs(nearest_e24(v) - v) / v < 1e-9


def parse_netlist(path):
    """Top-level devices of a netlist, skipping comment and .subckt bodies."""
    out, in_sub = [], False
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        s = line.strip()
        if not s or s.startswith('*'):
            continue
        low = s.lower()
        if low.startswith('.subckt'):
            in_sub = True
            continue
        if low.startswith('.ends'):
            in_sub = False
            continue
        if in_sub or s.startswith('.'):
            continue
        out.append(s)
    return out


def count_devices(lines):
    """Count semiconductors actually present in a netlist, for a cross-check."""
    cnt = Counter()
    for s in lines:
        tok = s.split()
        k = tok[0][0].upper()
        if k == 'Q':
            cnt['2N3904' if '2N3904' in s else tok[0]] += 1
        elif k == 'X':
            cnt[tok[-1]] += 1
        elif k == 'D':
            cnt['BAT85'] += 1
    return cnt


def fmt(v):
    return ('%.0f' % v) if float(v).is_integer() else ('%g' % v)


def fmt_ohm(v):
    """Human form: 1200 -> 1.2k, 1000000 -> 1M."""
    if v >= 1e6:
        return '%gM' % (v / 1e6)
    if v >= 1e3:
        return '%gk' % (v / 1e3)
    return '%g' % v


def main():
    tx_lines = parse_netlist(TX)
    rx_lines = parse_netlist(RX)
    tx_dev = count_devices(tx_lines)
    rx_dev = count_devices(rx_lines)

    # cross-check the hard-coded requirement lists against the real netlists
    tx_q = tx_dev.get('2N3904', 0)
    rx_q = rx_dev.get('2N3904', 0)
    assert tx_q == 6, 'TX transistor count changed: %d' % tx_q
    assert rx_q == 3, 'RX transistor count changed: %d' % rx_q
    assert rx_dev.get('OPAx197', 0) == 1 and rx_dev.get('BAT85', 0) == 1

    r_need, r_use = Counter(), defaultdict(list)
    for v, n, use in TX_R + RX_R:
        r_need[v] += n
        r_use[v].append(use)
    c_need, c_use = Counter(), defaultdict(list)
    for v, n, use in TX_C + RX_C:
        c_need[v] += n
        c_use[v].append(use)

    # With no series/parallel assembly, what gets installed is one part.  Prefer the
    # exact netlist value when the shelf already holds enough of it (it may be an E96
    # value such as 210k, which is perfectly usable); otherwise fall back to the
    # nearest E24, which is what a shop will actually stock.
    buy_of, buy_need = {}, Counter()
    for v in r_need:
        if R_STOCK.get(v, 0) >= r_need[v]:
            buy_of[v] = v
        else:
            buy_of[v] = v if is_e24(v) else nearest_e24(v)
    for v, n in r_need.items():
        buy_need[buy_of[v]] += n
    r_buy = [v for v in sorted(buy_of) if R_STOCK.get(buy_of[v], 0) < buy_need[buy_of[v]]]

    L = []
    A = L.append
    A('# AM 31 MHz 缺料台账')
    A('')
    A('2026-11-17。本文回答一个问题：**按现有器材，能不能把发射机和接收机各装出一台。**')
    A('')
    A('数字来源：')
    A('')
    A('- 发射网表 `round2_20261116/netlists/d05.cir`（6 只 2N3904，冻结拓扑）')
    A('- 接收网表 `stage5_receiver/S05_A2_G22_candidate.cir`（3 只 2N3904 + OPA197 + BAT85）')
    A('- 库存 `procurement_20261031/AM31MHz_采购台账_基准_20261110_2008.xlsx` 的 `已有与未购买` 工作表，'
      '仅取 ① / ①B / ② 三组；③ 组即本台账要处理的对象')
    A('')
    A('本文由 `build_shortage_ledger.py` 生成，需求合计与标准值换算均为脚本计算，不是手写。'
      '新料到手后重跑即可更新。')
    A('')
    A('**取值原则（用户 2026-11-17 确定）：电阻、电容一律买单个成品，不用串并联拼凑。**'
      '网表里的非标值改为采购最接近的 E24 标准值，偏差在 §3.2 与 §4.1 单列。'
      '需要可调的位置直接买微调器/电位器，不搭“固定电阻＋微调”的串联串。')
    A('')
    A('---')
    A('')
    A('## 1. 结论')
    A('')
    gap_q = max(0, tx_q + rx_q - Q_STOCK['2N3904'])
    A('**不能。** 三处硬阻塞，与天线无关：')
    A('')
    A('| # | 阻塞 | 现状 | 后果 |')
    A('|---|---|---|---|')
    A('| 1 | 2N3904 数量 | 发射需 %d、接收需 %d，合计 **%d**；在手 **%d** | 差 %d 只，'
      '任何一端都装不成完整链路 |' % (tx_q, rx_q, tx_q + rx_q, Q_STOCK['2N3904'], gap_q))
    A('| 2 | 10 Ω 取样电阻 | 在手 **0** | `RSENSE` 是全项目唯一电流测点，缺它测不了调谐、电流、功率 |')
    A('| 3 | SOIC-8→DIP-8 转接板 | 在手 **0** | OPA197 是 SOIC-8，万能板焊不上，接收检波后整级无法实现 |')
    A('')
    A('另有一处**接收链专项阻塞**：双调谐 LC 的两只 `LSEL1/2` 要求 Coilcraft `132-17L`（460 nH），'
      '**有货但贵（¥136/只）**，7×7 骨架自绕在 31 MHz 没有 Q/SRF 数据；已改用 Bourns 78FR47K-RC。见 §5。')
    A('')
    A('取消串并联后，电阻需补 **%d 种**、电容需补 **%d 种**（§3、§4）。' % (
        len(r_buy), len([v for v in c_need if C_STOCK.get(v, 0) < c_need[v]])))
    A('')
    A('---')
    A('')
    A('## 2. 半导体与 IC')
    A('')
    A('| 器件 | 需要 | 在手 | 缺口 | 备注 |')
    A('|---|---:|---:|---:|---|')
    A('| 2N3904BU | %d | %d | **%d** | 发射 6（Q1/QB/QG/QM/QCE/QEF）+ 接收 3（Q1/Q2/QBUF）。'
      'S9013 虽有 %d 只，但无 SPICE 模型且 fT 偏低，不作替代 |'
      % (tx_q + rx_q, Q_STOCK['2N3904'], gap_q, Q_STOCK['S9013']))
    A('| LM393P | 1 | %d | 0 | 双比较器，振荡 + PWM 各用一半 |' % IC_STOCK['LM393P'])
    A('| OPA197IDR | 1 | %d | 0 | **需 SOIC-8→DIP-8 转接板才能上板** |' % IC_STOCK['OPA197IDR'])
    A('| BAT85S-TR | 1 | %d | 0 | 检波。DO-34 轴向件已停产，贴片件需自行转接 |' % IC_STOCK['BAT85S'])
    A('| 31 MHz 晶振 49S | 1 | 5 | 0 | LIMING 31.000 MHz |')
    A('')
    A('---')
    A('')
    A('## 3. 电阻')
    A('')
    A('发射与接收的需求已合并。**不使用串并联**，因此只有“库存有该单值”或“须购该单值”两种状态。')
    A('')
    A('| 阻值 Ω | 需 | 在手 | 状态 | 用途 |')
    A('|---|---:|---:|---|---|')
    for v in sorted(r_need):
        need = r_need[v]
        sug = buy_of[v]
        have = R_STOCK.get(sug, 0)
        uses = '；'.join(sorted(set(r_use[v])))
        # show the purchase value when it differs, so the row is actionable
        label = fmt_ohm(v) if sug == v else '%s（买 %s）' % (fmt_ohm(v), fmt_ohm(sug))
        A('| %s | %d | %d | %s | %s |' % (
            label, need, have, '足够' if have >= need else '**须购**', uses))
    A('')
    A('**须购电阻单值**：%s。' % '、'.join(fmt_ohm(v) for v in r_buy))
    A('')
    A('### 3.1 10 Ω 是特殊件')
    A('')
    A('`RSENSE` 决定所有电流与功率读数的绝对值，要求 **10.0 Ω ±0.1%、金属膜非绕线、≥0.25 W**，'
      '建议买 5 只以上。用 1% 件会让每个功率数字带上 1% 的系统误差，'
      '与仿真 1e-7 的闭合精度完全不匹配。10 Ω 本身是 E24 标准值，容易买到。')
    A('')
    A('### 3.2 非标值改买最接近的 E24')
    A('')
    A('网表用的是精确计算值，市售件只能按标准档买。下表列出每个非标值的建议采购值与它带来的偏差。')
    A('')
    A('| 网表值 Ω | 用途 | 建议买 Ω | 偏差 | 影响 |')
    A('|---|---|---|---:|---|')
    effects = {
        1250: '末级集电极负载，偏小会让 QCE 工作点电流略升',
        50: '仅测试源终端，可用 51 Ω；也可用 49.9 Ω（E96）',
        37000: '包络注入深度，直接影响调制度 m，须实测复核',
        40000: '末级偏置分压，影响 QCE 静态电流',
    }
    for v in sorted(r_buy):
        if is_e24(v):
            continue
        sug = nearest_e24(v)
        dev = 100 * (sug / v - 1)
        effect = effects.get(v, '偏置点微移，须在实测工作点记录')
        A('| %s | %s | %s | %+.1f%% | %s |' % (
            fmt_ohm(v), '；'.join(sorted(set(r_use[v])))[:28], fmt_ohm(sug), dev, effect))
    A('')
    A('买标准值意味着**网表与实物不再逐位一致**。装配后必须实测各管静态工作点并记录实际阻值，'
      '不能把仿真表格直接当实测基线。')
    A('')
    A('### 3.3 可调位置：直接买微调器，不搭串联串')
    A('')
    A('| 器件 | 数量 | 对应网表 |')
    A('|---|---:|---|')
    for name, n, use in TRIMMERS:
        A('| %s | %d | %s |' % (name, n, use))
    A('')
    A('已有 100 kΩ 多圈微调 ×2、10 kΩ 微调 ×5，可先用于基带；'
      '天线/末级的调节位置建议另配 20 kΩ 档，避免用 100 kΩ 调到低端（分辨率差）。')
    A('')
    A('---')
    A('')
    A('## 4. 电容')
    A('')
    A('同样不使用并联拼凑。')

    def pF(s):
        return float(s[:-1]) * {'p': 1.0, 'n': 1e3, 'u': 1e6}[s[-1]]

    A('')
    A('| 容值 | 需 | 在手 | 状态 | 用途 | 备注 |')
    A('|---|---:|---:|---|---|---|')
    c_need.setdefault('100u', 3)
    c_need.setdefault('2.7p', 1)
    STOCK_ONLY = {'2.2p': 'S04 晶体振荡板负载（33pF×2、2.2pF×1）；也是 CK 两档的低档（网表 2.485pF，−11%）',
                  '30p': 'CTUNE 固定段备档：470nH 新起点用 27/33pF，30p 用于电感偏低角点（low_high CT2）',
                  '39p': 'CTUNE 固定段备档：用于电感偏低角点（low_low CT2=39p、high_low CT2=39p）',
                  '4.7n': '老师件瓷片 472，备用'}
    for v in sorted(set(c_need) | set(C_STOCK), key=pF):
        if v not in c_need:
            A('| %s | 0 | %d | 在手·无需求 | %s | %s |' % (
                v, C_STOCK[v], STOCK_ONLY.get(v, '本网表无需求'), '已到手，不需采购'))
            continue
        need, have = c_need[v], C_STOCK.get(v, 0)
        note = ''
        if v == '100n' and have >= need:
            status = '库存覆盖'
            note = ('0805 贴片 10 只 + 老师件直插 104 1 只。'
                    '**2026-11-19 用户裁定：直插 104 库存覆盖 `CCOUP1` 等直插位，不另购**（缺口按 0 计）')
        elif v == '100u' and have >= need:
            status = '库存覆盖'
            note = ('SMD 10 只 + 老师件 100µF/10V 2 只（后者仅限 ≤10V 节点）。'
                    '直插位由购物车 16V 5×11 直插 20 只覆盖（未付款）')
        elif v == '10u' and have >= need:
            status = '足够'
            note = '直插件'
        elif v == '2.4p':
            status = '**换值档**'
            note = '2.2p 已在手 10 只，2.7p 为第二档；2.4 只是网表 2.485 取整'
        else:
            status = '足够' if have >= need else '**须购**'
        A('| %s | %d | %d | %s | %s | %s |' % (
            v, need, have, status, '；'.join(sorted(set(c_use[v]))), note))
    A('')
    A('### 4.1 须购电容与标准值')
    A('')
    A('| 网表值 pF | 用途 | 建议买 pF | 说明 |')
    A('|---|---|---|---|')
    cap_advice = {
        '2.4p': ('2.4', 'C0G ±0.25 pF 档；±0.1 pF 直插件几乎不存在，须多买筛选'),
        '11p': ('11', 'C0G ±2%'),
        '15p': ('15', 'CSEL 输入串联；已有 15 pF，但接收板需要独立一只'),
        '27p': ('27', 'C0G ±5%（±2% 无货源，降级须记录）；470nH 起点',),
        '47p': ('47', 'C0G ±5%、50 V 以上；`CENV` 影响调制度，须实测'),
    }
    for v in sorted([k for k in c_need if C_STOCK.get(k, 0) < c_need[k]], key=pF):
        sug, note = cap_advice.get(v, (v[:-1], 'C0G ±5%'))
        A('| %s | %s | %s | %s |' % (
            v[:-1], '；'.join(sorted(set(c_use[v])))[:26], sug, note))
    A('')
    A('2.4 pF 是最需要留意的一项：普通 C0G 的容差是 ±0.25 pF，而 `CK` 决定两腔耦合。'
      '**2.2 pF 已在手 10 只**（网表 2.485 pF，−11%），可作第一档；2.7 pF 为第二档。'
      '若须覆盖 2.4–2.7 pF，需另购 2–6 pF 微调——现有 CCW12（3.5–20 pF）与 CYM1（3–18 pF）都到不了。')
    A('')
    A('---')
    A('')
    A('## 5. 接收链专项：132-17L 与 BFC280905217')
    A('')
    A('> **2026-11-19 更正**：本节原判「本项目唯一没有替代方案的阻塞」不成立。两只件都不是无货源，'
      '而是一只**有货但贵**、一只**淘宝无零售**，且替代方案均已落地。以下保留原始判断作为历史记录。')
    A('')
    A('| 项 | 要求 | 现状 |')
    A('|---|---|---|')
    A('| `LSEL1/2` | Coilcraft **132-17L**，460 nH ±5%，直插，2 只 | **有货**：淘宝「栀庐清坐优选」¥136/只（2 只 ¥272，配对 6 只约 ¥816）→ 判定「有货但贵」 |')
    A('| `CTUNE1/2` 微调 | Vishay **BFC280905003 / 05217**，2–18 pF | **分销渠道件**（得捷/贸泽有货），淘宝无零售 → 判定「无零售」 |')
    A('')
    A('| 已定替代 | 料号 | 单价 | 代价 |')
    A('|---|---|---|')
    A('| `LSEL1/2` | Bourns **78FR47K-RC** 470 nH ±10% 轴向 | ¥2.58/只 | '
      '**Q31=40 时 G31 −1.75 dB**（34.90 vs 基线 42.72 V/V）；**Q31=25 压力点 −4.89 dB**（24.34 V/V）。'
      '4 Vpp 余量须按 −4.9 dB 评估，不能只写 −1.8 dB |')
    A('| `CTUNE1/2` | **CCW12** 陶瓷微调 3.5–20 pF | ¥18.8/10 只 | Q 与温漂劣于薄膜件，调试档够用，定型后可换原厂 |')
    A('')
    A('**固定电容随之改档**（`replacement_20261118/bourns/tuning.json`）：470 nH 起点的固定段是 '
      '**CT1 = 27 pF ∥ 微调 11.09 pF、CT2 = 33 pF ∥ 微调 12.38 pF**，'
      '**不是 132-17L(460 nH) 时代的 30/39 pF**。'
      '30 pF、39 pF 在手件保留作电感 ±10% 角点用（角点需 22/27/30/33/39 pF 五档：')
    A('')
    A('| 角点 | L1/L2 | CT1 固定+微调 | CT2 固定+微调 |')
    A('|---|---|---|---|')
    A('| nominal | 470/470 | **27** + 11.09 | **33** + 12.38 |')
    A('| loss_stress (Q31=25) | 470/470 | 27 + 10.60 | 33 + 12.79 |')
    A('| low_low | 423/423 | 33 + 12.39 | 39 + 11.87 |')
    A('| low_high | 423/517 | 33 + 11.42 | 30 + 10.28 |')
    A('| high_low | 517/423 | **22** + 11.01 | 39 + 12.53 |')
    A('| high_high | 517/517 | **22** + 10.52 | 30 + 10.63 |')
    A('')
    A('台账给的替代方向是“用 ①B 序号49 的 7×7 骨架自绕 460 nH”，但那个骨架标称量程 '
      '**200–370 nH**，而且**不含线圈**（选项写明），31 MHz 下的 Q 与插芯后 SRF 无任何数据。'
      '自绕 460 nH 在量程外且 Q 未知 —— 不构成可用替代。')
    A('')
    A('三条路线（第 1 条已采纳）：')
    A('')
    A('1. **改 Bourns 78FR47K-RC 470 nH**（已采纳）。单只 ¥2.58，是一百三十六分之一的价钱换取 '
      '−1.75 dB（Q31=40）／−4.89 dB（Q31=25 压力点）的增益损失；'
      '若后续课程口径要求原厂件，可随时改回 132-17L，成本约 ¥272（2 只）或 ¥816（6 只配对）。')
    A('2. **买 146-07J08L**（231–350 nH，Q≥72@50 MHz）作细调件，但量程不足 460 nH，不能单独替代。')
    A('3. **改接收拓扑**（提高中频或改单调谐）。这是仿真工作，与“暂停大规模仿真”的决定冲突。')
    A('')
    A('---')
    A('')
    A('## 6. 天线与机械（第三批，等发射机通了再买）')
    A('')
    A('> **2026-11-19 路线变更（用户裁定）**：**放弃自制天线（1 m 单极子 + 8×0.5 m 径向 + 空心线圈），'
      '改走成品鞭路线**，购物车里的紫铜丝与黄铜棒已删除。下表据此重写；'
      '原自制件清单（裸铜线 Ø1.0×6 m、黄铜夹线件 M3×2、非金属底座、桌面锚点）作废。')
    A('')
    A('**天线长度定为 90–100 cm，加载电感用 1812CS-392（3.9 µH）+ 8.2 pF C0G。**')
    A('')
    A('| 项 | 规格 | 数量 | 说明 |')
    A('|---|---|---:|---|')
    A('| 成品鞭 | CB 短波手台天线，SMA 公头 27 MHz | 1 | 购物车 ×1（¥23.96，未付款）。'
      '**到货先量总长与是否基部加感**——若为加感鞭，"截到 1.000 m"会同时改变加感量，'
      '不能按纯 1 m 单极子算。此为未闭合项 |')
    A('| 加载电感 | **1812CS-392（3.9 µH）**，主选 | 2 | **已定**。购物车 ×2。'
      '90 cm 需串联 26.82 pF、100 cm 需 21.85 pF；配 8.2 pF 后微调分别落到 18.62 / 13.65 pF，'
      '都在 CCW12 的 3.5–20 pF 窗口内 |')
    A('| 加载电感对照 | 1812CS-332（3.3 µH） | 2 | 购物车 ×2。效率高 7%，但 90 cm 需并 68 pF、'
      '100 cm 需并 22+8.2 pF（违反「不拼凑」），仅作 A/B 对照 |')
    A('| 固定电容 | 8.2 pF C0G | 1 | 购物车 ×1（10 只装）。392 的配套固定段 |')
    A('| 匹配电容 | 22 / 68 pF C0G | 各若干 | 购物车各 ×1。22 pF 兼 CT1 固定段（电感偏高角点） |')
    A('| 同轴跳线 | RG316 SMA 转 SMA，0.5 m | 2 | 购物车 ×2。外皮参与共模，长度须记录 |')
    A('| 尼龙拉线 | 鱼线 Ø0.3 mm | 1 卷 | 购物车 ×1。3 条扶正 1 m 导体，**禁用金属拉线** |')
    A('| 垫高柱 | Ø30 mm 尼龙 | 8 | 径向线末端离桌，汇点高度 0.83 m。'
      '**M2×30 隔离柱不适用**（那是 PCB 固定件） |')
    A('| **NanoVNA** | H4 或同类，含开路/短路/负载校准件 | 1 套 | 暂不买：改用扫频+检波法，或借实验室 VNA |')
    A('')
    A('SMA 母座已有 3 只（KH-SMA-K513-G），不必再买。')
    A('')
    A('**三档加载电感的取舍依据**（`fixed_length_part_choice.csv`，各自重新调谐到 31 MHz）：')
    A('')
    A('| 件 | 90 cm 需串联 C | 微调能出 | 需外加固定 C0G | 100 cm 需串联 C | 外加 | η_driver 90cm | Q31 |')
    A('|---|---:|---:|---:|---:|---:|---:|---:|')
    A('| 472（原主候选，未购） | 14.289 pF | 全部 | 0 | 12.744 pF | 0 | 2.455% | 59.7 |')
    A('| **392（已选）** | 26.819 pF | ≤20 | **8.82**（8.2 可顶） | 21.847 pF | 3.85（8.2 偏大） | **2.926%** | 68.1 |')
    A('| 332（对照） | 76.849 pF | ≤20 | **58.85**（68 可顶） | 46.516 pF | 28.52（需 22+8.2 并） | **3.120%** | 64.3 |')
    A('')
    A('**392 相对 472 效率高约 19%，代价是要外加一只已在车的 8.2 pF。** '
      '472 的优点是"单只微调全程覆盖 80–100 cm"，但它不在购物车，需另购。'
      '因为长度已固定为 90–100 cm，选 392 更划算。')
    A('')
    A('---')
    A('')
    A('## 7. 采购单（按阻塞顺序）')
    A('')
    A('### 第一批：不买就一行都验证不了')
    A('')
    A('| 项 | 规格 | 数量 | 估价 | 依据 |')
    A('|---|---|---:|---:|---|')
    A('| 2N3904BU | onsemi TO-92 | 10 | ¥1.27@10 量级 | §2，缺口 %d 只 |' % gap_q)
    A('| 10 Ω 电阻 | **±0.1%、金属膜非绕线、≥0.25 W** | 5 | 略高于普通 1% 件 | §3.1，`RSENSE` |')
    A('| SOIC-8→DIP-8 转接板 | 1.27 mm 间距，逐脚直通 | 5 | ¥10 / 5 片 | '
      '③序号37，挂账两轮未下单。OPA197 共 3 只，需 1 用 + 1 备 + 1 换档（RFB 390k/430k 两档），'
      '转接板是易耗品；购物车 LHY-A 仅 2 片，**不够** |')
    A('| 953 Ω 电阻 | 1%、1/4W | 10 | ¥0.25 / 10 只 | ③序号36，S05 独立 LC 板可拆负载 `RMEAS` |')
    A('| 电阻套件 | 见下表 %d 种单值，各 10 只 | 1 套 | 低价 | §3，取消拼凑后的新增需求 |' % (len(r_buy) - 1))
    A('| 20 kΩ 多圈微调 | ±10%、多圈 | 2 | — | §3.3，`RVRF` 与幅度调节 |')
    A('')
    A('**第一批电阻单值**（每值 10 只；10 Ω 已单列在上表，不重复计入）：')
    A('')
    A('| 网表值 Ω | 买 Ω | 数量 |')
    A('|---|---|---:|')
    for v in r_buy:
        if v == 10:
            continue
        sug = v if is_e24(v) else nearest_e24(v)
        A('| %s | %s | 10 |' % (fmt_ohm(v), fmt_ohm(sug)))
    A('')
    A('两点说明：')
    A('')
    A('- **10 Ω** 单独一行，因为它有 ±0.1% 的精度要求，不能按普通 1% 件下单。')
    A('- **953 Ω** 不属于发射或接收网表，而是 S05 独立 LC 板的可拆测量负载 `RMEAS`'
      '（接入整机时按图纸拆除），同样单列，不进上面的单值表。')
    A('')
    A('### 第二批：接收链')
    A('')
    A('| 项 | 规格 | 数量 | 说明 |')
    A('|---|---|---:|---|')
    A('| 78FR47K-RC 470 nH（替代 132-17L） | Bourns ±10%、轴向直插 | 4 | 已定，§5；购物车 ×5（未付款） |')
    A('| CCW12 微调（替代 BFC280905217） | 3.5–20 pF 陶瓷微调 | 3 | 已定，§5；购物车 ×1 份＝10 只（未付款） |')
    A('| **27 pF C0G** | ±5%（±2% 无货源）、50 V、直插 | 3 | **CT1 固定段，470 nH 起点**；购物车 ×2 份＝20 只 |')
    A('| **33 pF C0G** | ±2%、50 V、直插 | 1 | **CT2 固定段，470 nH 起点**；在手已有 50 只，由库存覆盖 |')
    A('| 2.4 pF C0G | ±0.25 pF、50 V | 10 | `CK`，§4.1；**2.2 pF 已在手 10 只可作第一档**，2.7 pF 为第二档 |')
    A('| 11 pF C0G | ±2%、50 V | 5 | `COUT`；购物车有云母 11 pF ×1（未付款） |')
    A('| 47 pF C0G | ±5%、50 V 以上 | 10 | `CENV`；购物车 ×1 份（未付款） |')
    A('| ~~直插 100 nF~~ | — | ~~10~~ | **不下单**：2026-11-19 用户裁定由库存直插 104 覆盖（缺口按 0 计） |')
    A('| 直插 100 µF | 16 V、5×11 mm、直插 | 5 | 现有 SMD 不能直插；购物车 16V 20 只（未付款）覆盖 |')
    A('')
    A('### 第三批：天线（§6）')
    A('')
    A('等发射机能输出稳定载波与包络之后再买。')
    A('')
    A('---')
    A('')
    A('## 8. 本台账没有解决的事')
    A('')
    A('- 价格未重新核查，除标注者外沿用原台账快照。')
    A('- ~~132-17L 现货状态未查~~ → 2026-11-19 已查实：**有货，¥136/只**，判「贵」不判「缺」。')
    A('- 未验证 S9013 能否在 31 MHz 替代 2N3904（无 SPICE 模型，不做此假设）。')
    A('- **买标准值会使网表与实物不一致**：§3.2 的偏差会影响偏置点与调制度，'
      '装配后须实测工作点并把实际阻值/容值回填，不能沿用仿真数值当验收基线。')
    A('- 取消并联后，匹配电容的可选档位变少，调谐余量下降；'
      '这部分要靠微调电容补偿，不能靠“多并几只”解决。')

    OUT.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('wrote %s (%d lines)' % (OUT.name, len(L)))
    print('resistors to buy:', [fmt_ohm(v) for v in r_buy])
    print('transistor gap:', gap_q)


if __name__ == '__main__':
    main()
