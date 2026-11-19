"""重建元器件总表（库存驱动）。

事实源：AM31MHz_采购台账_基准_20261110_2008.xlsx「已有与未购买 / 采购明细」
需求源：04_缺料台账_20261117.xlsx「电阻 / 电容」+「可调与换值件」
购物车：2026-11-19 09:31 用户淘宝长截图，逐段切分核对，本项目 37 项、¥212.59。
        全部未付款，单独成表，不计入在手。
输出：05_元器件总表_20261119.xlsx / .md
"""
import re
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'simulation/v4_hardware/procurement_20261031/AM31MHz_采购台账_基准_20261110_2008.xlsx'
LEDGER = ROOT / '项目管理/04_缺料台账_20261117.xlsx'
OUTX = ROOT / '项目管理/05_元器件总表_20261119.xlsx'
OUTM = ROOT / '项目管理/05_元器件总表_20261119.md'
TODAY = '2026-11-19'

FONT = '微软雅黑'
THIN = Side(style='thin', color='BFBFBF')
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HDR_FILL = PatternFill('solid', fgColor='1F4E79')
HDR_FONT = Font(name=FONT, size=10, bold=True, color='FFFFFF')
BODY = Font(name=FONT, size=9)
BOLD = Font(name=FONT, size=9, bold=True)
F_DONE = PatternFill('solid', fgColor='E2EFDA')
F_TEACH = PatternFill('solid', fgColor='FFF2CC')
F_CART = PatternFill('solid', fgColor='DDEBF7')
F_GAP = PatternFill('solid', fgColor='FCE4D6')
F_NO = PatternFill('solid', fgColor='EDEDED')
F_WARN = PatternFill('solid', fgColor='FFE699')
WRAP = Alignment(wrap_text=True, vertical='top')
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)

BRANDS = {'YAGEO', 'VISHAY', 'Vishay', 'TI', 'onsemi', 'TDK', 'BOURNS', 'Rubycon',
          'KNSCHA', 'Dersonic', '风华', 'BOOMELE', 'XFCN', 'HCTL', '金航标', '长电',
          'LIMING', 'TOCOS', 'CCO', 'UNI-ROYAL', '华星机电', '莱联', 'G-Switch',
          'MYOUNG', '天球', '嘉立创'}
UNIT = {'k': 1e3, 'M': 1e6, 'p': 1, 'n': 1e3, 'u': 1e6, 'µ': 1e6, None: 1}


def parse_val(*texts):
    s = ' '.join(t or '' for t in texts)
    m = re.search(r'(\d+(?:\.\d+)?)\s*(k|M)?\s*Ω', s)
    if m:
        return 'R', round(float(m.group(1)) * UNIT[m.group(2)])
    m = re.search(r'(\d+(?:\.\d+)?)\s*(p|n|µ|u)F', s)
    if m:
        return 'C', round(float(m.group(1)) * UNIT[m.group(2)], 2)
    return None, None


def key_val(k):
    t = re.sub(r'（.*?）', '', str(k)).strip()
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(k|M|p|n|u|µ)?', t)
    if not m:
        return None
    return float(m.group(1)) * UNIT[m.group(2)]


def split_spec(text):
    parts = [p.strip() for p in re.split(r'[；;]', text or '') if p.strip()]
    brand = next((p for p in parts if p in BRANDS), '')
    mpn = parts[0] if parts else ''
    rest = [p for p in parts[1:] if p != brand]
    return mpn, brand, '；'.join(rest)


def classify(name):
    if '电位器' in name or '微调' in name:
        return '微调 / 电位器'
    if '电阻' in name:
        return '电阻'
    if '电容' in name:
        return '电容'
    if any(k in name for k in ('电感', '线圈', '骨架', '磁芯')):
        return '电感与磁性'
    if any(k in name for k in ('三极管', '二极管', '运算', '比较器', '晶振', 'IC',
                               '放大器', '稳压', '开关')):
        return '半导体 / IC'
    if any(k in name for k in ('天线', '铜线', '尼龙', '鱼线', '夹线', '拉杆')):
        return '天线与机械'
    if '电池' in name:
        return '电源附件'
    return '连接器与结构'


# ---------- 1. 需求 ----------
wb4 = openpyxl.load_workbook(LEDGER, data_only=True)


def read_need(sheet):
    out = {}
    for row in wb4[sheet].iter_rows(min_row=4, values_only=True):
        k, need = row[0], row[1]
        if not isinstance(k, str) or not k.strip() or not isinstance(need, (int, float)):
            continue
        out[k.strip()] = dict(need=need, use=row[5] or '', tag=row[6] or '')
    return out


R_NEED = read_need('电阻')
C_NEED = read_need('电容')
C_NEED.setdefault('2.2p', dict(need=1, use='S04 晶体振荡板负载；CK 两档的低档', tag='已定值'))
C_NEED.setdefault('30p', dict(need=0, use='CTUNE 备档（电感偏低角点 CT2）', tag='备档'))
C_NEED.setdefault('39p', dict(need=0, use='CTUNE 备档（电感偏低角点 CT2）', tag='备档'))
C_NEED.setdefault('4.7n', dict(need=0, use='备用（老师件 472）', tag='无需求'))
C_NEED.setdefault('100u', dict(need=3, use='CVREF；去耦', tag='库存覆盖'))
C_NEED.setdefault('27p', dict(need=2, use='CT1 固定段（470nH 起点）', tag='须购'))
R_NEED.setdefault('953', dict(need=1, use='RMEAS，S05 独立 LC 板取样', tag='精度件 0.1%'))


def need_of(kind, val):
    table = {'R': R_NEED, 'C': C_NEED}.get(kind)
    if not table:
        return dict(need=None, use='', tag='')
    best = None
    for k, v in table.items():
        kv = key_val(k)
        if kv is not None and abs(kv - val) < 1e-6:
            best = v
            break
    return best or dict(need=None, use='', tag='')


# ---------- 2. 已到手 ----------
wbb = openpyxl.load_workbook(BASE, data_only=True)
stock = [dict(no=int(r[0]), group=r[1] or '', status=r[2] or '', name=r[3] or '',
              spec=r[4] or '', qty=r[5], src=r[7] or '', note=r[11] or '', ref=r[10] or '')
         for r in wbb['已有与未购买'].iter_rows(min_row=4, values_only=True)
         if isinstance(r[0], (int, float))]

wsp = wbb['采购明细']
hdr = [c.value for c in wsp[1]]
purch = {}
for r in wsp.iter_rows(min_row=2, values_only=True):
    d = dict(zip(hdr, r))
    if d.get('编号'):
        purch[int(d['编号'])] = d

rows = []
for s in stock:
    if s['group'].startswith('③'):
        continue
    m = re.search(r'(\d+)$', str(s['ref']))
    p = purch.get(int(m.group(1))) if m else None
    if p is None:
        key = (s['spec'] or '').split('；')[0].strip()
        p = next((v for v in purch.values()
                  if key and str(v.get('型号/商品选项') or '').strip() == key), None)
    mpn, brand, extra = split_spec(s['spec'])
    params = pkg = platform = shop = price = amount = order = ''
    if p:
        mpn = p.get('型号/商品选项') or mpn
        b = p.get('品牌') or ''
        brand = brand or ('' if ('未显示' in b or '未提供' in b) else b)
        params = p.get('标称参数/规格') or extra
        pkg = p.get('封装/引脚/包装') or ''
        platform = p.get('商城/平台') or ''
        shop = p.get('店铺/供应商') or ''
        order = p.get('购物车状态') or ''
        sub_, fre_, qty_ = p.get('商品小计(元)'), p.get('运费(元)'), p.get('总数量')
        if isinstance(sub_, (int, float)):
            amount = round(float(sub_) + float(fre_ or 0), 2)
            if isinstance(qty_, (int, float)) and qty_:
                price = round(amount / qty_, 4)
    else:
        params, platform = extra, ''
    shop = shop or s['src']
    kind, val = parse_val(s['name'], s['spec'])
    if '电位器' in s['name']:
        kind = None
    nd = need_of(kind, val) if kind else dict(need=None, use='', tag='')
    have = s['qty'] if isinstance(s['qty'], (int, float)) else None
    st = '已到手·老师发放' if s['group'].startswith('②') else '已到手·自购'
    if '封装不符' in (s['status'] or '') or any(k in (params + pkg) for k in ('SMD', '0805', '贴片')):
        st = '已到手·自购（封装不符）'
    rows.append(dict(cat=classify(s['name']), name=s['name'], mpn=mpn, brand=brand,
                     params=params, pkg=pkg, use=nd['use'] or '', need=nd['need'],
                     have=have, status=st, platform=platform, shop=shop, price=price,
                     amount=amount, order=order, note=s['note'][:300],
                     kind=kind, val=val))

# ---------- 3. 购物车 ----------
CART = [
    ('电阻', '金属膜电阻 15kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RMT 15k', 1),
    ('电阻', '金属膜电阻 2.2kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RPU1/RPU2 上拉', 2),
    ('电阻', '金属膜电阻 36kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RMINJ（37k 改 36k，−2.7%）', 1),
    ('电容', '铝电解电容 100µF 16V 直插', '5×11mm（20只/份），脚距 2mm', 'zave旗舰店', 1, 2.30, 'CVREF / 去耦', 3),
    ('电阻', '金属膜电阻 390kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RFB G=40 对照档（不达标档）', 1),
    ('电阻', '金属膜电阻 430kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RFB G=44', 1),
    ('微调 / 电位器', '3296W 多圈微调 20kΩ', '3296W 20K，多圈，±10%（5个）', 'zave旗舰店', 2, 3.70, 'RVRF；RVAT/RVAB 幅度调节', 2),
    ('微调 / 电位器', '3296W 多圈微调 10kΩ', '3296W 10K，多圈（5个）', 'zave旗舰店', 1, 3.70, 'RVDT/RVDB 占空比分压', 1),
    ('电阻', '金属膜电阻 39kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RDB1（40k 改 39k，−2.5%）', 1),
    ('电阻', '金属膜电阻 30kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RHT 迟滞', 1),
    ('电阻', '金属膜电阻 3.3kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RMB', 1),
    ('电阻', '金属膜电阻 1.2kΩ', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RDC（1.25k 改 1.2k，−4.0%）', 1),
    ('电阻', '金属膜电阻 200Ω', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'REF 射随负载', 1),
    ('电阻', '金属膜电阻 150Ω', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RDE 末级发射极', 1),
    ('电阻', '金属膜电阻 51Ω', '1/4W 1%，100只/份', 'zave旗舰店', 1, 2.13, 'RSOURCE 测试源终端（50Ω 改 51Ω，−2.0%）', 1),
    ('半导体 / IC', '2N3904 直插 NPN', 'TO-92（50只/份）', 'zave旗舰店', 1, 3.69, 'Q1/QB/QG/QM/QCE/QEF + 接收 3 只', 9),
    ('电容', 'NP0/C0G 陶瓷电容 27pF', 'NP0 100V 27pF ±5%（10只/份）', '仁十众旗舰店', 2, 7.66, 'CT1 固定段（470nH 起点：27p ∥ 微调 11.09p）', 3),
    ('电容', 'NP0/C0G 陶瓷电容 47pF', 'NP0 100V 47pF ±5%（10只/份）', '仁十众旗舰店', 1, 7.66, 'CENV 包络滤波', 1),
    ('电容', 'NP0/C0G 陶瓷电容 68pF', 'NP0 100V 68pF ±5%（10只/份）', '仁十众旗舰店', 1, 7.66, '天线匹配（332 档配套）', 1),
    ('电容', 'NP0/C0G 陶瓷电容 22pF', 'NP0 100V 22pF ±5%（10只/份）', '仁十众旗舰店', 1, 7.66, 'CT1 固定段（电感偏高角点）+ 天线匹配', 1),
    ('电容', 'NP0/C0G 陶瓷电容 10pF', 'NP0 100V 10pF ±5%（10只/份）', '仁十众旗舰店', 1, 7.66, '天线匹配', 1),
    ('电容', 'NP0/C0G 陶瓷电容 8.2pF', 'NP0 100V 8.2pF（10只/份）', '仁十众旗舰店', 1, 8.33, '天线匹配 C_ant（392 档配套固定段）', 1),
    ('电阻', '精密金属膜电阻 10Ω 0.1%', '芃赞 PY 千分之一系列 10R，插件，10只包邮', '芃赞企业店', 1, 4.76, 'RSENSE，全项目唯一电流测点', 5),
    ('电阻', '精密金属膜电阻 953Ω 0.1%', '芃赞 PY 千分之一系列 953R，插件', '芃赞企业店', 10, 0.25, 'RMEAS，S05 独立 LC 板', 10),
    ('天线与机械', 'CB 短波手持对讲机天线', 'SMA 公头 27MHz', '宝锋欣奥维专卖店', 1, 23.96, '辐射体（成品鞭路线）', 1),
    ('天线与机械', '鱼线（尼龙拉线替代）', '0.3mm 约1000米', '天天特卖工厂', 1, 6.51, '3 条扶正 1 m 导体，禁用金属拉线', None),
    ('天线与机械', '双通六角尼龙柱 M2×30', 'M2×30（20只/白色）', '力烁旗舰店', 1, 2.78, 'PCB 隔离柱，不是天线 Ø30 垫高件', None),
    ('微调 / 电位器', 'CCW12 陶瓷微调电容', '100V，3.5~20pF，黄点（10只/份）', '南京新飞凡', 1, 18.80, 'CTUNE1/2（替代 BFC280905217）', 2),
    ('电阻', 'RJ15 铜脚金属膜 10Ω 1%', '0.5W 1%，10只/份', '南京新飞凡', 1, 2.68, 'RSENSE 粗用（非 0.1% 件，不可替代）', 0),
    ('电感与磁性', '78FR47K-RC 470nH 轴向', 'Bourns 78FR47K-RC，±10%', '承湘电子', 5, 2.58, 'L1/L2 接收 LC', 2),
    ('电容', '云母电容 11pF', 'CMDB2A11PJ 100V 11pF，脚距 P=6mm', '好博特', 1, 2.20, 'COUT 输出耦合', 1),
    ('连接器与结构', 'SOIC8 转直插转换板', 'LHY-A，1.27mm，两个插针一块板', '老虎鱼官方店', 5, 2.00, 'OPA197IDR 上板（1 用+1 备+1 换档）', 5),
    ('连接器与结构', 'SMA 射频转接线 RG316', '0.5m，SMA 内螺内针转内螺内针', '特加特数码专营店', 2, 8.63, '同轴跳线；外皮参与共模，长度须记录', 2),
    ('微调 / 电位器', 'CYM1 可调电容 3/18P', '薄膜微调 3–18pF', '深圳赛格和泰电子', 3, 0.60, '微调备用件', None),
    ('电感与磁性', '1812CS-332X 贴片绕线电感', '1812，3.3µH', '猎芯商城', 2, 2.50, '加载电感对照：90cm 需并 68pF（在车）', 1),
    ('电感与磁性', '1812CS-392X 贴片绕线电感', '1812，3.9µH', '猎芯商城', 2, 4.50, '加载电感主选（固定 90–100cm，配 8.2pF）', 2),
    ('连接器与结构', '单面散热焊盘间距转接板', 'SOP-8 带散热焊盘转 DIP', '易津电子', 5, 0.30, '贴片件上万能板（OPA197 无散热焊盘，用不上）', None),
]
NOTE = {
    'RJ15': '冗余：已有 PY 10Ω 0.1%（10 只），建议删除',
    '100µF 16V': '脚距 2mm，万能板需掰脚；覆盖 100µF 直插缺口',
    '云母电容 11pF': '脚距 6mm，万能板需掰脚 90°，注意瓷片应力',
    'M2×30': '非天线 Ø30 垫高件，仅用于 PCB 固定',
    '953Ω': '两个历史订单均未成交（嘉立创已取消、淘宝未付款）；本轮购物车 ×10 未付款',
    '10Ω 0.1%': '芃赞 SKU 为 10 只包邮，×1 份＝10 只，满足台账「≥5 只」',
    '27pF': '精度 ±5%（台账要求 ±2%，±2% 无货源），降级须记录；×2 份＝20 只',
    '8.2pF': 'SKU 写 ±0.2、图上写 ±0.5，下单页须核对；392 加载电感的配套固定段',
    '2N3904': '标题写 S8550/SS8050，SKU 才是 2N3904；非 onsemi 原厂，RF 级优先用在手 BU 件',
    '78FR47K': '标题写 78FR15M/78FR22K，SKU 才是 47K；到货须逐只量电感（±10% 本就要测）',
    'CYM1': '3–18pF，覆盖不到 CK 的 2.4pF 档，勿当 CK 微调',
    'SOIC8 转直插': '需求 5 片（1 用+1 备+1 换档），当前 5 片',
    '单面散热焊盘': 'OPA197 是普通 SOIC-8 无 exposed pad；与 LHY-A 功能重叠，建议删',
}
cart_rows = []
for cat, name, spec, shop, qty, price, use, need in CART:
    kind, val = parse_val(name, spec)
    if cat.startswith('微调'):
        kind = None
    cart_rows.append(dict(cat=cat, name=name, mpn='', brand='', params=spec, pkg='',
                          use=use, need=need, have=0, status='购物车未付款',
                          platform='淘宝/天猫', shop=shop, price=price,
                          amount=round(price * qty, 2), order=f'购物车 {TODAY}（未付款）',
                          note=next((v for k, v in NOTE.items() if k in name), ''),
                          qty=qty, kind=kind, val=val))

# ---------- 4. 缺口：按值聚合 ----------
# 2026-11-19 用户裁定：这两个值的直插缺口由库存/已购件覆盖，缺口按 0 计。
# 不把 0805 贴片计入「可覆盖数量」（它确实装不进直插位），而是明确标注为裁定覆盖。
# 注意单位：本脚本内部统一折算到 pF。100nF = 100×1e3 = 100000 pF；100µF = 100×1e6 = 1e8 pF。
RULED = {('C', 100e3): '2026-11-19 用户裁定：直插 100nF 由库存直插 104 覆盖，缺口按 0 计',
         ('C', 100e6): '2026-11-19 裁定：直插 100µF 由购物车 16V 5×11 直插 20 只覆盖（未付款），缺口按 0 计'}
pool = {}
for r in rows:
    if r['kind'] and isinstance(r['have'], (int, float)) and '封装不符' not in r['status']:
        pool[(r['kind'], r['val'])] = pool.get((r['kind'], r['val']), 0) + r['have']
for r in rows + cart_rows:
    if r['need'] is None or not r['kind']:
        r['gap'] = None
        continue
    r['gap'] = max(0, r['need'] - pool.get((r['kind'], r['val']), 0))
    ruled = RULED.get((r['kind'], r['val']))
    if ruled:
        r['gap'] = 0
        r['note'] = (r['note'] + '；' if r['note'] else '') + ruled
for r in cart_rows:
    if r['need'] is None:
        continue
    if '2N3904' in r['name']:
        r['gap'] = max(0, r['need'] - 5)
    elif r['kind'] is None:
        r['gap'] = r['need']

# ---------- 5. xlsx ----------
wb = openpyxl.Workbook()
wb.remove(wb.active)
COLS = ['序号', '类别', '元件名称', '型号 / 料号', '品牌', '关键参数', '封装 / 尺寸',
        '位号 / 用途', '需', '在手', '缺口', '状态', '平台', '店铺 / 供应商',
        '单价(元)', '金额(元)', '单据 / 日期', '备注 / 核对提示']
WIDTHS = [5, 13, 24, 26, 11, 30, 20, 24, 6, 6, 6, 20, 11, 20, 8, 8, 22, 36]


def sheet_title(ws, text, sub, ncol):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    c = ws.cell(row=1, column=1, value=text)
    c.font = Font(name=FONT, size=15, bold=True, color='1F4E79')
    c.alignment = Alignment(vertical='center')
    ws.row_dimensions[1].height = 30
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncol)
    c = ws.cell(row=2, column=1, value=sub)
    c.font = Font(name=FONT, size=9, color='595959')
    c.alignment = Alignment(vertical='center', wrap_text=True)
    ws.row_dimensions[2].height = 28


def sheet_head(ws, row, cols, widths):
    for i, (t, w) in enumerate(zip(cols, widths), start=1):
        c = ws.cell(row=row, column=i, value=t)
        c.font, c.fill, c.border, c.alignment = HDR_FONT, HDR_FILL, BOX, CENTER
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 30
    return row + 1


def paint(cell, st):
    if '封装不符' in st:
        cell.fill = F_WARN
    elif st.startswith('已到手·自购'):
        cell.fill = F_DONE
    elif st.startswith('已到手·老师'):
        cell.fill = F_TEACH
    elif st.startswith('购物车'):
        cell.fill = F_CART
    elif '无货源' in st or '不买' in st:
        cell.fill = F_NO
    else:
        cell.fill = F_GAP


ws = wb.create_sheet('00_说明')
sheet_title(ws, '元器件总表 · 重建版',
            f'生成日期 {TODAY}　｜　本表是「在手库存」的唯一权威视图；04 台账继续负责需求推算', 6)
TXT = [
    ('B', '一、为什么重建'),
    ('', '04 台账的「电容」「电阻」是需求驱动的表：只有网表用到的值才会出现一行。它因此漏掉了 2.2pF、30pF、39pF、4.7nF 四个已在手件，也漏掉 100µF 整行——凭 04 表判断库存必然出错（2026-11-19 已实际误判两次）。本表改为库存驱动：一件实物一行，无论有无需求。'),
    ('B', '二、数据源与优先级'),
    ('', '① 在手、型号、价格、订单：AM31MHz_采购台账_基准_20261110_2008.xlsx →「已有与未购买」「采购明细」'),
    ('', '② 需求（需）、位号用途：04_缺料台账_20261117.xlsx →「电阻」「电容」「半导体IC」「可调与换值件」'),
    ('', '③ 购物车：2026-11-19 09:31 淘宝长截图（1256×18402，切 14 段逐项核对），'
          '**本项目 37 项、合计 ¥212.59**，全部未付款，单列于 02 表，不计入「在手」'),
    ('B', '三、状态定义（互斥）'),
    ('', '已到手·自购　　钱已付、货已到（2026-11-10 两批，实付 ¥62.11 + ¥214.43）→ 计入在手'),
    ('', '已到手·自购（封装不符）　件在手但装不上（100nF 0805 贴片、100µF SMD）→ 计入数量，不计可用'),
    ('', '已到手·老师发放　老师发的件，不计采购成本 → 计入在手'),
    ('', '库存覆盖　　缺口已由在手件或已裁定方案覆盖，不再下单（100nF 直插 104、100µF 直插）'),
    ('', '购物车未付款　　已在购物车、尚未结算 → 不计入在手，见 02 表'),
    ('', '须购·未下单 / 无货源·暂缓 / 不买·已裁定　见 03 表'),
    ('B', '四、缺口算法'),
    ('', '缺口 = MAX(0, 需 − 同值在手合计)。同值在手合计 = 该值所有「已到手·自购 / 老师发放」行之和，'
          '不含封装不符行、不含购物车行。因此 10nF 的 C0G 件与老师件瓷片会合计后再判断。'),
    ('B', '五、2026-11-19 已裁定的旧不一致（原文保留，结论已更新）'),
    ('', '1) 1nF 同一料号 K102J15C0GF5TH5，采购明细记 VISHAY，已有与未购买记 YAGEO —— 仍待实物核对'),
    ('', '2) 100nF 原按直插下单、实收 0805 贴片；100µF 同样买到 SMD —— '
          '**用户 2026-11-19 裁定：直插 100nF 由库存 104 覆盖；100µF 由购物车 16V 直插 20 只覆盖**，'
          '两项缺口均按 0 计，不再列入须购'),
    ('', '3) 953Ω 两平台均未购买（嘉立创已取消、淘宝未付款）；购物车芃赞 PY 953R ×10 为新一轮未付款'),
    ('', '4) 2.2kΩ / 3.3kΩ / 15kΩ / 30kΩ 四项 —— **2026-11-19 09:31 购物车已补齐**（各 1 份 100 只装，未付款），原缺口关闭'),
    ('', '5) 10Ω 0.1% 原记「仅 1 只」有误 —— 芃赞 SKU 为 10 只包邮，×1 份＝10 只，满足「≥5 只」'),
    ('', '6) CTUNE 固定段原写 30/39 pF（132-17L 460nH 时代）—— '
          '**470nH 起点应为 27/33 pF**（∥ 微调 11.09/12.38 pF）；30/39 pF 转为电感角点备档'),
    ('', '7) ① 批（序号 1–10）只有合计 ¥62.11，无逐项单价，本表不完全分摊'),
]
r = 4
for kind, text in TXT:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    c = ws.cell(row=r, column=1, value=text)
    c.font = Font(name=FONT, size=11 if kind == 'B' else 9, bold=(kind == 'B'),
                  color='1F4E79' if kind == 'B' else '000000')
    c.alignment = Alignment(wrap_text=True, vertical='top')
    if kind != 'B':
        ws.row_dimensions[r].height = max(18, 14 * (len(text) // 62 + 1))
    r += 1
for i, w in enumerate([8, 18, 18, 18, 16, 34], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w

ws = wb.create_sheet('01_元器件总表')
sheet_title(ws, '01 元器件总表（库存驱动，一件一行）',
            '绿＝已到手自购｜黄＝老师发放｜橙黄＝封装不符｜蓝＝购物车未付款（不计入在手）｜橙色＝须购缺口', len(COLS))
r = sheet_head(ws, 3, COLS, WIDTHS)
order_key = {'半导体 / IC': 1, '电阻': 2, '电容': 3, '微调 / 电位器': 4, '电感与磁性': 5,
             '连接器与结构': 6, '天线与机械': 7, '电源附件': 8}
allrows = rows + cart_rows
allrows.sort(key=lambda x: (order_key.get(x['cat'], 99), x['status'].startswith('购物车'),
                            x.get('val') or 0, str(x['name'])))
for i, d in enumerate(allrows, start=1):
    vals = [i, d['cat'], d['name'], d['mpn'], d['brand'], d['params'], d['pkg'], d['use'],
            d['need'] if d['need'] is not None else '',
            d['have'] if d['have'] is not None else '',
            d['gap'] if d['gap'] is not None else '',
            d['status'], d['platform'], d['shop'], d['price'], d['amount'],
            d['order'], d['note']]
    for j, v in enumerate(vals, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.font, c.border = BODY, BOX
        c.alignment = CENTER if j in (1, 9, 10, 11, 15, 16) else WRAP
    paint(ws.cell(row=r, column=12), d['status'])
    if isinstance(d['gap'], (int, float)) and d['gap'] > 0:
        cell = ws.cell(row=r, column=11)
        cell.fill = F_GAP
        cell.font = Font(name=FONT, size=9, bold=True, color='C00000')
    r += 1
ws.freeze_panes = 'D4'
ws.auto_filter.ref = f'A3:{get_column_letter(len(COLS))}{r-1}'

ws = wb.create_sheet('02_购物车未付款')
sheet_title(ws, '02 购物车未付款清单（2026-11-19）',
            f'共 {len(cart_rows)} 项，合计 ¥{sum(x["amount"] for x in cart_rows):.2f}（页面券后单价 × 份数，未含运费）。本页任何一件都不算在手。', 10)
cols2 = ['序号', '类别', '商品', '规格 / 选项', '店铺', '份数', '单价(元)', '小计(元)',
         '对应位号 / 用途', '判定 / 备注']
r = sheet_head(ws, 3, cols2, [5, 13, 26, 36, 20, 7, 9, 9, 26, 40])
for i, d in enumerate(cart_rows, start=1):
    vals = [i, d['cat'], d['name'], d['params'], d['shop'], d['qty'], d['price'],
            d['amount'], d['use'], d['note'] or '保留']
    for j, v in enumerate(vals, start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.font, c.border = BODY, BOX
        c.alignment = CENTER if j in (1, 6, 7, 8) else WRAP
    if d['note'].startswith('冗余'):
        for j in range(1, 11):
            ws.cell(row=r, column=j).fill = F_GAP
    r += 1
ws.cell(row=r, column=1, value='合计').font = BOLD
ws.cell(row=r, column=8, value=round(sum(x['amount'] for x in cart_rows), 2)).font = BOLD
ws.freeze_panes = 'A4'

GAPS = [
    ('电容', '27pF C0G', '±2%、50V、直插，3 只', 'CT1 固定段（470nH 起点）',
     '购物车有仁十众 100V ±5% ×2 份 ＝ 20 只；±2% 无货源，实际按 ±5% 降级并记录'),
    ('电容', '2.7pF（CK 第二档）', 'C0G ±0.25pF', 'CK 腔间耦合',
     '2.2pF 已在手 10 只可作为第一档（网表 2.485pF，−11%）；2.7pF 未购。'
     '现有 CCW12（3.5–20pF）与 CYM1（3–18pF）都到不了 2.4pF，不能当 CK 微调用'),
    ('电容', '直插 100nF', '—', 'CCOUP1 等直插位',
     '**2026-11-19 用户裁定：由库存直插 104 覆盖，不另购**（缺口按 0 计）'),
    ('电容', '直插 100µF', '16V、5×11mm、直插', 'CVREF 等',
     '在手 SMD 不能直插；购物车 16V 5×11 直插 20 只（未付款）覆盖'),
    ('电阻', '10Ω 0.1% 非绕线', '≥0.25W，5 只以上', 'RSENSE',
     '购物车芃赞 PY 10R ×1 份＝**10 只**（未付款），满足「≥5 只」（此前误记「仅 1 只」）'),
    ('电阻', '953Ω 0.1%', '1/4W 级', 'RMEAS（S05 独立 LC 板）',
     '购物车有芃赞 PY 953R ×10（未付款）'),
    ('电感', '78FR47K-RC', 'Bourns 470nH 轴向，2 只', 'L1/L2 接收 LC',
     '购物车已有 ×5（未付款）；代价 −1.75dB(Q31=40)／−4.89dB(Q31=25)'),
    ('连接器', 'SOIC-8→DIP-8 转接板', '1.27mm 逐脚直通，5 块', 'OPA197IDR 上板',
     '购物车 LHY-A ×5（未付款）；需 1 用＋1 备＋1 换档'),
    ('天线', '加载电感 392 + 8.2pF', '1812CS-392X 3.9µH ＋ 8.2pF C0G', 'LTUNE（发射天线）',
     '两者均在购物车（未付款）；天线定为 90–100cm 固定长度'),
    ('天线', 'NanoVNA-H4', '含开路/短路/负载校准件', '第三批仪器',
     '暂不买：改用扫频+检波法，或借实验室 VNA'),
    ('天线', 'Ø30mm 尼龙垫高柱', '8 个，高度一致', '径向线末端离桌 0.83m',
     '可用瓶盖/PVC 管段替代；M2×30 隔离柱不适用'),
]
ws = wb.create_sheet('03_须购缺口')
sheet_title(ws, '03 须购缺口（合并 04 台账要求与购物车核算）',
            '标「购物车有」＝不需重复下单，只是尚未付款；标「未见」＝购物车里确实没有', 5)
r = sheet_head(ws, 3, ['类别', '缺什么', '规格要求', '用在哪儿', '现状 / 处理'],
               [9, 26, 30, 24, 56])
for row_ in GAPS:
    for j, v in enumerate(row_, start=1):
        cell = ws.cell(row=r, column=j, value=v)
        cell.font, cell.border, cell.alignment = BODY, BOX, WRAP
    r += 1
ws.freeze_panes = 'A4'

ws = wb.create_sheet('04_状态汇总')
sheet_title(ws, '04 状态汇总', '件数按「在手」列合计；金额按「金额」列合计（老师件计 0）', 4)
r = sheet_head(ws, 3, ['状态', '行数', '件数', '金额(元)'], [26, 8, 10, 12])
agg = {}
for d in allrows:
    a = agg.setdefault(d['status'], [0, 0, 0.0])
    a[0] += 1
    a[1] += d['have'] if isinstance(d['have'], (int, float)) else 0
    a[2] += d['amount'] if isinstance(d['amount'], (int, float)) else 0
for st, (n, q, m) in agg.items():
    for j, v in enumerate([st, n, q, round(m, 2)], start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.font, c.border = BODY, BOX
        c.alignment = CENTER if j > 1 else WRAP
    paint(ws.cell(row=r, column=1), st)
    r += 1
for label, val in [('① 批（序号1–10）实付合计（无逐项单价，未分摊）', 62.11),
                   ('①B 批（序号49–84）实付合计（商品 ¥211.43 ＋ 运费 ¥3.00）', 214.43),
                   ('在手现金口径合计', 276.54)]:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    c = ws.cell(row=r, column=1, value=label)
    c.font, c.alignment = BOLD, WRAP
    c2 = ws.cell(row=r, column=4, value=val)
    c2.font, c2.alignment = BOLD, CENTER
    r += 1

ws = wb.create_sheet('05_变更日志')
sheet_title(ws, '05 本次重建的变更日志', '对应 2026-11-19 核对结果', 3)
r = sheet_head(ws, 3, ['#', '变更', '依据 / 说明'], [5, 46, 70])
LOG = [
    ('购物车整表重录（35→37 项，¥230.78→¥212.59）',
     '2026-11-19 09:31 长截图逐段核对：新增 15k/2.2k/30k/3.3k；删除 39pF、33pF；'
     '47pF 2→1、36K 2→1、953R 60→10；8 项电阻 2.23→2.13、20K 电位器 4.00→3.70、RG316 8.68→8.63'),
    ('CTUNE 固定段改 27/33 pF（原 30/39）',
     '470nH（78FR47K）起点应为 27pF ∥ 11.09p、33pF ∥ 12.38p（tuning.json nominal）；'
     '30/39 pF 在手件转为电感 ±10% 角点备档'),
    ('100nF / 100µF 改判「库存覆盖」',
     '2026-11-19 用户裁定：直插 100nF 由库存 104 覆盖；100µF 由购物车 16V 直插 20 只覆盖。缺口按 0 计'),
    ('10Ω 0.1% 改判「10 只，已满足」',
     '芃赞 SKU 为 10 只包邮，×1 份＝10 只；原写「仅 1 只」是错的'),
    ('78FR47K 代价补压力点',
     '原只写 −1.8 dB（Q31=40 实际 −1.75 dB）；补 Q31=25 压力点 −4.89 dB，4Vpp 余量按后者评估'),
    ('SOIC8 转接板 2→5 片',
     'OPA197 共 3 只，需 1 用＋1 备＋1 换档（RFB 390k/430k 两档）；转接板为易耗品'),
    ('加载电感定为 392＋8.2pF',
     '天线长度定 90–100cm 固定；392 需串联 26.82pF(90cm)/21.85pF(100cm)，配 8.2pF 后微调落 18.62/13.65pF，'
     '均在 CCW12 的 3.5–20pF 窗口内；效率比 472 高约 19%'),
    ('天线改成品鞭路线',
     '用户 2026-11-19 裁定放弃自制（1m 单极子＋8×0.5m 径向）；紫铜丝、黄铜棒已从购物车删除'),
    ('新增 2.2pF ×10（在手）', '序号52；04 电容表整行缺失，是本次两次误判的直接原因'),
    ('新增 30pF ×10、39pF ×10（在手）', '序号51/53；改用「电感角点备档」表述，不再是 CTUNE 主固定段'),
    ('新增 4.7nF ×1（老师件）', '序号18（瓷片 472）'),
    ('新增 100µF 两行', '序号65（SMD ×10）/ 序号15（老师件 10V ×2）；04 电容表无 100µF 整行'),
    ('953Ω 改判「未购」', '嘉立创编号33 已取消、淘宝编号41 未付款；购物车芃赞 953R ×10 仍为未付款'),
    ('2.4pF 改为「2.2pF 在手 + 2.7pF 缺」', '可调与换值件 F20 已把 2.2/2.7 指定为调试档，2.4 只是网表 2.485 的取整'),
    ('缺口改为按值聚合计算', '原先逐行算，导致 10nF（C0G 10 只 + 老师件 2 只）被误判缺 1'),
    ('购物车已删 1000pF、8.2pF 独石、BAT85、BWL3W、132-17L、0307 色环、围巾', '用户 2026-11-19 自行清理，与核对结论一致'),
]
for i, (a, b) in enumerate(LOG, start=1):
    for j, v in enumerate([i, a, b], start=1):
        c = ws.cell(row=r, column=j, value=v)
        c.font, c.border = BODY, BOX
        c.alignment = CENTER if j == 1 else WRAP
    r += 1
ws.freeze_panes = 'A4'

wb.save(OUTX)

# ---------- 6. md ----------
L = [f'# 元器件总表（重建版）\n', f'> 生成日期 {TODAY}　｜　本表是「在手库存」的唯一权威视图\n']
L.append('## 0. 为什么重建\n')
L.append('04 台账的「电容」「电阻」是需求驱动的表：只有网表用到的值才会出现一行。它因此漏掉了 2.2pF、30pF、39pF、4.7nF 四个已在手件，也漏掉 100µF 整行。本表改为库存驱动：一件实物一行，无论有无需求。\n')
L.append('## 1. 状态定义\n')
L.append('| 状态 | 含义 | 计入在手 |\n|---|---|---|')
L.append('| 已到手·自购 | 2026-11-10 两批已付款到货 | 是 |')
L.append('| 已到手·自购（封装不符） | 件在手但装不上（100nF 0805、100µF SMD） | 数量计，可用性不计 |')
L.append('| 已到手·老师发放 | 老师发放，不计成本 | 是 |')
L.append('| 购物车未付款 | 已在购物车、尚未结算 | 否 |')
L.append('| 须购·未下单 / 无货源·暂缓 / 不买 | 见 03 表 | 否 |\n')
L.append('## 2. 已到手清单\n')
L.append('| # | 类别 | 元件 | 型号 / 料号 | 关键参数 | 位号 / 用途 | 需 | 在手 | 缺口 | 状态 | 平台 / 店铺 | 金额 |\n|---|---|---|---|---|---|---|---|---|---|---|---|')
for i, d in enumerate([x for x in allrows if x['status'].startswith('已到手')], start=1):
    L.append(f"| {i} | {d['cat']} | {d['name']} | {d['mpn']} | {d['params']} | {d['use'] or '—'} | "
             f"{d['need'] if d['need'] is not None else '—'} | "
             f"{d['have'] if d['have'] is not None else '—'} | "
             f"{d['gap'] if d['gap'] else '—'} | {d['status']} | "
             f"{(d['platform'] + ' / ' if d['platform'] else '') + d['shop']} | {d['amount'] or '—'} |")
L.append('')
L.append('## 3. 购物车未付款（2026-11-19 09:31，本项目 37 项）\n')
L.append('> 本页任何一件都不算在手。价格为页面券后单价，未含运费。'
         '截图共 14 段（1256×18402，每段重叠 160 px），已逐项核对；'
         '店铺顺序与 01:49 那版不同，勿按行号对应。\n')
L.append('| # | 商品 | 规格 | 店铺 | 份数 | 单价 | 小计 | 用途 | 判定 |\n|---|---|---|---|---|---|---|---|---|')
for i, d in enumerate(cart_rows, start=1):
    L.append(f"| {i} | {d['name']} | {d['params']} | {d['shop']} | {d['qty']} | {d['price']} | "
             f"{d['amount']} | {d['use']} | {d['note'] or '保留'} |")
L.append(f"\n合计约 **¥{sum(x['amount'] for x in cart_rows):.2f}**。\n")
L.append('## 4. 须购缺口\n')
L.append('| 类别 | 缺什么 | 规格要求 | 用在哪儿 | 现状 |\n|---|---|---|---|---|')
for row_ in GAPS:
    L.append('| ' + ' | '.join(str(x) for x in row_) + ' |')
L.append('')
L.append('## 5. 2026-11-19 已裁定的旧不一致\n')
L.append('> 下列各条原文保留作历史记录，**结论已按 2026-11-19 的裁定更新**。\n')
L.append('1. 1nF 同一料号 `K102J15C0GF5TH5`，采购明细记 VISHAY，已有与未购买记 YAGEO —— 仍待实物核对')
L.append('2. 100nF 原按直插下单、实收 0805 贴片；100µF 同样买到 SMD —— '
         '**已裁定**：直插 100nF 由库存 104 覆盖，100µF 由购物车 16V 直插 20 只覆盖，缺口均按 0 计')
L.append('3. 953Ω 两平台均未购买（嘉立创已取消、淘宝未付款）；购物车芃赞 PY 953R ×10 为未付款')
L.append('4. 2.2kΩ / 3.3kΩ / 15kΩ / 30kΩ —— **已由 09:31 购物车补齐**（各 1 份，未付款），原缺口关闭')
L.append('5. 10Ω 0.1% 原记「仅 1 只」有误 —— 芃赞 SKU 为 10 只包邮，×1 份＝10 只，满足「≥5 只」')
L.append('6. CTUNE 固定段原写 30/39 pF（132-17L 460nH 时代）—— **470nH 起点应为 27/33 pF**；'
         '30/39 pF 转为电感角点备档')
L.append('7. ① 批（序号 1–10）只有合计 ¥62.11，无逐项单价，本表不完全分摊')
OUTM.write_text('\n'.join(L) + '\n', encoding='utf-8')

print('rows', len(allrows), 'cart', len(cart_rows), 'sum', round(sum(x['amount'] for x in cart_rows), 2))
print('gaps', [(d['name'], d['gap']) for d in allrows if isinstance(d['gap'], (int, float)) and d['gap'] > 0])
