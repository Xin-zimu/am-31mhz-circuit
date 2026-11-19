# -*- coding: utf-8 -*-
"""把 04_缺料台账_20261117.md 转成 Excel 工作簿。数据全部来自该 md。"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path

SRC_MD = "04_缺料台账_20261117.md"
OUT = "04_缺料台账_20261117.xlsx"

# 相对路径按脚本所在目录解析，避免在仓库根目录运行把产物写到错误位置
_HERE = Path(__file__).resolve().parent
SRC_MD = str(_HERE / SRC_MD)
OUT = str(_HERE / OUT)

FONT = "微软雅黑"

TITLE_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FILL = PatternFill("solid", fgColor="1F4E79")
SUB_FILL = PatternFill("solid", fgColor="D9E2F3")
BUY_FILL = PatternFill("solid", fgColor="FFC7CE")
OK_FILL = PatternFill("solid", fgColor="E2EFDA")
WARN_FILL = PatternFill("solid", fgColor="FFEB9C")
BLOCK_FILL = PatternFill("solid", fgColor="F8CBAD")

BUY_FONT = Font(name=FONT, size=10, color="9C0006", bold=True)
OK_FONT = Font(name=FONT, size=10, color="375623")
WARN_FONT = Font(name=FONT, size=10, color="9C6500", bold=True)
BLOCK_FONT = Font(name=FONT, size=10, color="843C0C", bold=True)
BODY = Font(name=FONT, size=10)
BODY_B = Font(name=FONT, size=10, bold=True)

thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

WRAP = Alignment(vertical="center", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def title(ws, text, sub, ncols):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(row=1, column=1, value=text)
    c.font = Font(name=FONT, size=15, bold=True, color="FFFFFF")
    c.fill = TITLE_FILL
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 30

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    c = ws.cell(row=2, column=2 - 1, value=sub)
    c.font = Font(name=FONT, size=9, color="404040", italic=True)
    c.fill = SUB_FILL
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20
    return 3


def header(ws, row, cols, widths):
    for i, (name, w) in enumerate(zip(cols, widths), start=1):
        c = ws.cell(row=row, column=i, value=name)
        c.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        c.fill = HDR_FILL
        c.alignment = CENTER
        c.border = BOX
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 26
    return row + 1


def body(ws, row, rows, numeric_cols=(), center_cols=()):
    for r in rows:
        for i, v in enumerate(r, start=1):
            c = ws.cell(row=row, column=i, value=v)
            c.font = BODY
            c.border = BOX
            c.alignment = CENTER if i in center_cols else WRAP
            if i in numeric_cols:
                c.number_format = "0"
        row += 1
    return row


def paint(ws, row_start, row_end, ncols, status_col, mapping):
    """按状态列着色整行。mapping: 关键字 -> (fill, font)"""
    for r in range(row_start, row_end):
        key = ws.cell(row=r, column=status_col).value
        for kw, (fill, font) in mapping.items():
            if key is not None and kw in str(key):
                for c in range(1, ncols + 1):
                    cell = ws.cell(row=r, column=c)
                    cell.fill = fill
                    cell.font = font
                break


def section_header(ws, row, specs):
    """按 [(标题, 起始列, 结束列)] 画可跨列合并的表头行。"""
    for text, c1, c2 in specs:
        if c1 != c2:
            ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)
        c = ws.cell(row=row, column=c1, value=text)
        c.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        c.alignment = CENTER
        for cc in range(c1, c2 + 1):
            cell = ws.cell(row=row, column=cc)
            cell.border = BOX
            cell.fill = HDR_FILL
    ws.row_dimensions[row].height = 26
    return row + 1


def gap_rows(ws, row, rows, need_idx, have_idx, out_idx):
    """缺口 = max(0, 需 - 在手)"""
    for i, r in enumerate(rows):
        need = r[need_idx - 1]
        have = r[have_idx - 1]
        ws.cell(row=row + i, column=out_idx, value=f"=MAX(0,{need}-{have})")


wb = Workbook()

# ============ 1 总览 ============
ws = wb.active
ws.title = "总览"
r = title(ws, "AM 31 MHz 缺料台账（2026-11-17）",
          "来源：项目管理/04_缺料台账_20261117.md ｜ 由 build_shortage_ledger.py 生成的数据，本表仅做转写与计算", 5)

W = [15, 26, 34, 44, 12]
for col_, w_ in zip("ABCDE", W):
    ws.column_dimensions[col_].width = w_


def band(text, color="1F4E79"):
    """整行合并的小节标题条"""
    global r
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    c = ws.cell(row=r, column=1, value=text)
    c.font = Font(name=FONT, size=11, bold=True, color=color)
    c.fill = PatternFill("solid", fgColor="DEEAF6")
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[r].height = 22
    r += 1


def kv(label, val, fill=None, color="000000", h=22, size=10, bold=False):
    """左标签 + 右侧合并说明"""
    global r
    c = ws.cell(row=r, column=1, value=label)
    c.font = BODY_B
    c.alignment = Alignment(horizontal="center", vertical="center")
    if fill:
        c.fill = fill
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    c = ws.cell(row=r, column=2, value=val)
    c.font = Font(name=FONT, size=size, bold=bold, color=color)
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
    if fill:
        c.fill = fill
    ws.row_dimensions[r].height = h
    r += 1


# 核心问题 / 结论
kv("核心问题", "按现有器材，能不能把发射机和接收机各装出一台？", h=24)
kv("结论", "不能。三处硬阻塞（与天线无关），外加一处接收链专项阻塞。",
   fill=BUY_FILL, color="C00000", h=26, size=11, bold=True)
kv("11-18 更新", "接收链“唯一没有替代方案”已更正：主候选改为 Bourns 78FR47K-RC（470 nH）＋ BFC280905217（2–18 pF），"
                 "OPA197 反馈改 430 kΩ（G=44）。仿真名义 4.18 Vpp，余量仅 4.08%；损耗压力点掉到 2.33 Vpp。"
                 "详见“替代候选”表。", fill=WARN_FILL, color="833C00", h=46, size=10, bold=True)
r += 1

band("一、三处硬阻塞")
r = header(ws, r, ["#", "阻塞", "现状", "后果", "对应章节"], W)
blockers = [
    [1, "2N3904 数量", "发射需 6、接收需 3，合计 9；在手 5", "差 4 只，任何一端都装不成完整链路", "§2"],
    [2, "10 Ω 取样电阻", "在手 0", "RSENSE 是全项目唯一电流测点，缺它测不了调谐、电流、功率", "§3.1"],
    [3, "SOIC-8→DIP-8 转接板", "在手 0", "OPA197 是 SOIC-8，万能板焊不上，接收检波后整级无法实现", "§1"],
]
start = r
r = body(ws, r, blockers, numeric_cols=(1,), center_cols=(1, 5))
for rr in range(start, r):
    for c_ in range(1, 6):
        cell = ws.cell(row=rr, column=c_)
        if c_ == 2:
            cell.font = BLOCK_FONT
        cell.fill = BLOCK_FILL
    ws.row_dimensions[rr].height = 34
r += 1

band("二、接收链专项（原判「无替代方案」，2026-11-19 已解除）")
r = header(ws, r, ["项", "要求", "现状", "说明", "对应章节"], W)
recv = [
    ["LSEL1/2", "Coilcraft 132-17L，460 nH ±5%，直插，2 只", "有货但贵（¥136/只，2 只 ¥272）；已改 Bourns 78FR47K-RC",
     "有货但贵：132-17L 原厂 ¥136/只，非无货源。已改 Bourns 78FR47K-RC；代价 G31 −1.75 dB（Q31=40）／−4.89 dB（Q31=25 压力点），4Vpp 余量按 −4.9 dB 评估", "§5"],
    ["CTUNE1/2 微调", "Vishay BFC280905003，2–18 pF", "淘宝无零售（分销件）；已改 CCW12 3.5–20 pF",
     "淘宝无零售（得捷/贸泽有货）。已改 CCW12 3.5–20 pF 陶瓷微调", "§5"],
    ["CT1/CT2 固定段", "470 nH 起点：CT1 27 pF、CT2 33 pF（∥ 微调 11.09 / 12.38 pF）",
     "27 pF 购物车 ×2 份；33 pF 在手 50 只",
     "2026-11-19 更正：30/39 pF 是 132-17L(460 nH) 旧起点，已改 27/33 pF。30/39 保留作电感 ±10% 角点（角点需 22/27/30/33/39 五档）", "§5"],
]
start = r
r = body(ws, r, recv, center_cols=(5,))
for rr in range(start, r):
    ws.cell(row=rr, column=1).font = BLOCK_FONT
    for c_ in range(1, 6):
        ws.cell(row=rr, column=c_).fill = WARN_FILL
    ws.row_dimensions[rr].height = 34
r += 1

band("三、数量小结")
# 指标列合并 A:B，数值列 C，说明列合并 D:E
r = section_header(ws, r, [("指标", 1, 2), ("数值", 3, 3), ("说明", 4, 5)])

summary = [
    ["须购电阻单值种数", 11, "10、50、150、200、1.25k、2.2k、3.3k、15k、30k、37k、40k Ω"],
    ["须购电容种数", 3, "2.4 pF、11 pF、47 pF"],
    ["在库但封装不符", 1, "100 nF 只有 0805 贴片，直插位需另补"],
    ["半导体缺口", 4, "仅 2N3904BU 一项，其余 IC 均在库"],
    ["天线与机械", "第三批", "等发射机通了再买，含 NanoVNA 一套"],
]
for label, num, note in summary:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
    c = ws.cell(row=r, column=1, value=label)
    c.font = BODY
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c = ws.cell(row=r, column=3, value=num)
    c.font = BODY
    c.alignment = CENTER
    if isinstance(num, int):
        c.number_format = "0"
    ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=5)
    c = ws.cell(row=r, column=4, value=note)
    c.font = BODY
    c.alignment = WRAP
    for cc in range(1, 6):
        ws.cell(row=r, column=cc).border = BOX
    ws.row_dimensions[r].height = 24
    r += 1
r += 1

ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
c = ws.cell(row=r, column=1,
            value="取值原则（用户 2026-11-17 确定）：电阻、电容一律买单个成品，不用串并联拼凑；"
                  "非标值改买最接近的 E24 标准值；需要可调的位置直接买微调器/电位器。")
c.font = Font(name=FONT, size=9, italic=True, color="7F6000")
c.fill = PatternFill("solid", fgColor="FFF2CC")
c.alignment = WRAP
ws.row_dimensions[r].height = 34

ws.freeze_panes = "A3"

# ============ 2 半导体与 IC ============
ws = wb.create_sheet("半导体IC")
r = title(ws, "§2 半导体与 IC", "需要量 = 发射网表 d05.cir + 接收网表 S05_A2_G22_candidate.cir 合并", 5)
cols = ["器件", "需要", "在手", "缺口", "备注"]
widths = [18, 9, 9, 9, 78]
r = header(ws, r, cols, widths)
semi = [
    ["2N3904BU", 9, 5, 4,
     "发射 6（Q1/QB/QG/QM/QCE/QEF）+ 接收 3（Q1/Q2/QBUF）。S9013 虽有 21 只，但无 SPICE 模型且 fT 偏低，不作替代"],
    ["LM393P", 1, 5, 0, "双比较器，振荡 + PWM 各用一半"],
    ["OPA197IDR", 1, 3, 0, "需 SOIC-8→DIP-8 转接板才能上板（转接板在手 0）"],
    ["BAT85S-TR", 1, 5, 0, "检波。DO-34 轴向件已停产，贴片件需自行转接"],
    ["31 MHz 晶振 49S", 1, 5, 0, "LIMING 31.000 MHz"],
]
start = r
r = body(ws, r, semi, numeric_cols=(2, 3, 4), center_cols=(2, 3, 4))
for rr in range(start, r):
    if ws.cell(row=rr, column=4).value > 0:
        for c_ in range(1, 6):
            ws.cell(row=rr, column=c_).fill = BUY_FILL
            ws.cell(row=rr, column=c_).font = BUY_FONT
r += 1
ws.cell(row=r, column=1, value="合计缺口仅 2N3904BU 一项（4 只）；LM393P、OPA197、BAT85、晶振均在库。").font = Font(name=FONT, size=9, italic=True)
ws.freeze_panes = "A4"

# ============ 3 电阻 ============
ws = wb.create_sheet("电阻")
r = title(ws, "§3 电阻（发射 + 接收合并）",
          "不使用串并联，只有「库存有该单值」或「须购该单值」两种状态。缺口 = MAX(0, 需 − 在手)", 6)
cols = ["阻值 Ω（网表）", "需", "在手", "缺口", "状态", "用途", "调试属性（详见“可调与换值件”表）"]
widths = [20, 7, 7, 7, 12, 46, 40]
r = header(ws, r, cols, widths)
res = [
    ["10", 1, 0, 0, "", "RSENSE 取样，全项目唯一电流测点", "精度件：±0.1% 不可降级"],
    ["33", 2, 50, 0, "", "REU1/2", "已定值"],
    ["50（买 51）", 1, 0, 0, "", "RSOURCE 测试源终端", "改值件：-2.0%，仅测试源"],
    ["56", 1, 50, 0, "", "REG", "已定值"],
    ["100", 1, 50, 0, "", "ROUT", "已定值"],
    ["150", 1, 0, 0, "", "RDE 末级发射极", "已定值（驱动冻结）"],
    ["200", 1, 0, 0, "", "REF 射随负载", "已定值（驱动冻结）"],
    ["220", 2, 50, 0, "", "REB1/2", "已定值"],
    ["330", 1, 50, 0, "", "REB", "已定值"],
    ["470", 2, 50, 0, "", "REBUF；RME", "已定值"],
    ["1k", 5, 50, 0, "", "RC1/2/RF；RCG；RMC", "已定值"],
    ["1.25k（买 1.2k）", 1, 0, 0, "", "RDC 末级负载", "改值件：-4.0%，影响 QCE 工作点"],
    ["2.2k", 2, 0, 0, "", "RPU1/RPU2 上拉", "已定值（AM-ALT.2 主候选）"],
    ["3.3k", 1, 0, 0, "", "RMB", "已定值"],
    ["4.7k", 6, 100, 0, "", "RBB1/2/DET/FILT；RDB；RG2", "已定值"],
    ["10k", 9, 50, 0, "", "RBB；RBT；RBTB/RBBB；RDB2；RHB/RDT；RPRE；RVB", "已定值；RPRE 为 AM-ALT.2 选定注入电阻"],
    ["15k", 1, 0, 0, "", "RMT", "已定值"],
    ["20k", 2, 50, 0, "", "RHF；RVT", "已定值"],
    ["22k", 4, 50, 0, "", "RBT1/2；RFIX；RG1", "已定值"],
    ["30k", 1, 0, 0, "", "RHT 迟滞", "已定值"],
    ["37k（买 36k）", 1, 0, 0, "", "RMINJ", "改值件：-2.7%，须实测复核调制度 m"],
    ["40k（买 39k）", 1, 0, 0, "", "RDB1 偏置", "改值件：-2.5%，影响 QCE 静态电流"],
    ["210k", 1, 50, 0, "", "RFB G22", "已定值"],
    ["1M", 1, 50, 0, "", "RPORT", "已定值"],
]
for i, row in enumerate(res):
    row[4] = "须购" if row[2] == 0 else "足够"
start = r
r = body(ws, r, res, numeric_cols=(2, 3, 4), center_cols=(1, 2, 3, 4, 5))
gap_rows(ws, start, res, 2, 3, 4)
paint(ws, start, r, 5, 5, {"须购": (BUY_FILL, BUY_FONT), "足够": (OK_FILL, OK_FONT)})
r += 1
ws.cell(row=r, column=1, value="须购电阻单值（11 种）：10、50、150、200、1.25k、2.2k、3.3k、15k、30k、37k、40k。每值建议各买 10 只。").font = Font(name=FONT, size=10, bold=True, color="9C0006")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
r += 2

ws.cell(row=r, column=1, value="§3.1 10 Ω 是特殊件").font = Font(name=FONT, size=11, bold=True, color="1F4E79")
r += 1
note = ("RSENSE 决定所有电流与功率读数的绝对值，要求 10.0 Ω ±0.1%、金属膜非绕线、≥0.25 W，建议买 5 只以上。"
        "用 1% 件会让每个功率数字带上 1% 的系统误差，与仿真 1e-7 的闭合精度完全不匹配。10 Ω 本身是 E24 标准值，容易买到。")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
c = ws.cell(row=r, column=1, value=note)
c.font = Font(name=FONT, size=10, color="9C0006")
c.fill = BUY_FILL
c.alignment = WRAP
ws.row_dimensions[r].height = 42
r += 2

ws.cell(row=r, column=1, value="§3.3 可调位置：直接买微调器，不搭串联串").font = Font(name=FONT, size=11, bold=True, color="1F4E79")
r += 1
r = section_header(ws, r, [("器件", 1, 1), ("数量", 2, 2), ("对应网表", 3, 7)])
trims = [
    ["20 kΩ 多圈微调", 1, "RVRF：网表值 15288.9 Ω（原为 22k 固定 + 微调串联）——实为两脚变阻用法，定 20 kHz 包络频率"],
    ["10 kΩ 微调", 1, "RVDT/RVDB：网表值 7362.5 / 2637.5 Ω 分压——三脚分压，两段和恰为 10000 Ω，动片在 73.6%"],
    ["20 kΩ 电位器", 1, "RVAT/RVAB：网表值 931.3 / 19068.7 Ω 幅度调节——三脚分压，两段和恰为 20000 Ω，动片在 4.66%"],
]
start = r
r = body(ws, r, trims, numeric_cols=(2,), center_cols=(2,))
for rr in range(start, r):
    ws.merge_cells(start_row=rr, start_column=3, end_row=rr, end_column=7)
r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
ws.cell(row=r, column=1, value="已有 100 kΩ 多圈微调 ×2、10 kΩ 微调 ×5，可先用于基带；天线/末级的调节位置建议另配 20 kΩ 档，避免用 100 kΩ 调到低端（分辨率差）。").font = Font(name=FONT, size=9, italic=True)
ws.cell(row=r, column=1).alignment = WRAP
ws.row_dimensions[r].height = 30
ws.freeze_panes = "A4"

# ============ 4 非标值换算 ============
ws = wb.create_sheet("电阻_非标值换算")
r = title(ws, "§3.2 非标值改买最接近的 E24",
          "网表用的是精确计算值，市售件只能按标准档买；下表列出建议采购值与它带来的偏差", 5)
cols = ["网表值 Ω", "用途", "建议买 Ω", "偏差", "影响"]
widths = [14, 26, 13, 10, 62]
r = header(ws, r, cols, widths)
e24 = [
    ["50", "RSOURCE 测试源终端", "51", "+2.0%", "仅测试源终端，可用 51 Ω；也可用 49.9 Ω（E96）"],
    ["1.25k", "RDC 末级负载", "1.2k", "-4.0%", "末级集电极负载，偏小会让 QCE 工作点电流略升"],
    ["37k", "RMINJ", "36k", "-2.7%", "包络注入深度，直接影响调制度 m，须实测复核"],
    ["40k", "RDB1 偏置", "39k", "-2.5%", "末级偏置分压，影响 QCE 静态电流"],
]
start = r
r = body(ws, r, e24, center_cols=(1, 3, 4))
r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
c = ws.cell(row=r, column=1, value="买标准值意味着网表与实物不再逐位一致。装配后必须实测各管静态工作点并记录实际阻值，不能把仿真表格直接当实测基线。")
c.font = Font(name=FONT, size=10, color="9C6500")
c.fill = WARN_FILL
c.alignment = WRAP
ws.row_dimensions[r].height = 32
ws.freeze_panes = "A4"

# ============ 5 电容 ============
ws = wb.create_sheet("电容")
r = title(ws, "§4 电容（同样不使用并联拼凑）",
          "缺口 = MAX(0, 需 − 在手)；状态「封装不符」表示有料但装不上", 6)
cols = ["容值", "需", "在手", "缺口", "状态", "用途 / 备注", "调试属性（详见“可调与换值件”表）"]
widths = [10, 7, 7, 7, 12, 52, 44]
r = header(ws, r, cols, widths)
# [容值, 需, 在手, 状态覆盖(可选), 用途]
CAP_TAG = {
    "2.2p": "已定值；S04 晶体振荡板负载（非 S05），此前本表漏行",
    "2.7p": "换值件：CK 第二档，带宽<1.5 MHz 时替换 2.2 pF",
    "2.4p": "换值件：调试档 2.2/2.7 pF 已指定，须实测后定值；网表 2.485 pF 已不一致",
    "11p": "改值件：网表 10.81 pF，取整 11；可 10p∥1p 但须重算焊盘",
    "15p": "标称件；另备 18/20 pF 做匹配-带宽权衡",
    "33p": "已定值（晶振负载）",
    "47p": "确值件：AM-ALT.2 已用 22/47/100/220 pF 对照选定，非估计",
    "100p": "已定值",
    "330p": "已定值",
    "1n": "已定值",
    "10n": "已定值；须 C0G（信号路径）",
    "100n": "库存覆盖；0805 贴片 ×10 + 老师件直插 104 ×1，2026-11-19 裁定不另购",
    "10u": "已定值；须直插件",
    "30p": "备档；470nH 新起点用 27/33pF，30p 用于电感偏低角点（low_high CT2）",
    "39p": "备档；用于电感偏低角点（low_low CT2=39p、high_low CT2=39p）",
    "4.7n": "备用；老师件瓷片 472",
    "100u": "库存覆盖；SMD ×10 + 老师件 10V ×2（仅 ≤10V 节点），直插位由购物车 16V 20 只覆盖",
    "27p": "★470nH 起点 CT1 固定段（27p ∥ 微调 11.09p）；购物车 ×2 份",
    "33p": "★470nH 起点 CT2 固定段（33p ∥ 微调 12.38p）；亦作 C1/C2 晶振负载",
}

caps_raw = [
    ["2.2p", 1, 10, None, "S04 晶体振荡板负载；CK 两档的低档"],
    ["2.4p", 1, 0, None, "CK 腔间耦合"],
    ["2.7p", 1, 0, None, "CK 第二档（换值件）"],
    ["11p", 1, 0, None, "COUT 输出耦合"],
    ["15p", 2, 10, None, "CINPUT；CSEL 输入串联"],
    ["27p", 2, 0, None, "★CT1 固定段（470nH 起点：27p ∥ 微调 11.09p）"],
    ["30p", 0, 10, None, "备档：电感偏低角点（low_high CT2）"],
    ["33p", 3, 50, None, "C1/C2 晶振负载；CT2 固定段（470nH 起点）"],
    ["39p", 0, 10, None, "备档：电感偏低角点（low_low/high_low CT2）"],
    ["47p", 1, 0, None, "CENV 包络滤波"],
    ["100p", 4, 20, None, "CIN2/CBUF/CDET/CFILT"],
    ["330p", 2, 10, None, "CEB1/2"],
    ["1n", 5, 10, None, "CIN/COUTB/CME；CIN1/COBUF"],
    ["10n", 3, 10, None, "CG/COUTG/C_DRV"],
    ["100n", 4, 11, "库存覆盖", "CCOUP1 直插；去耦。0805 贴片 ×10 + 老师件直插 104 ×1；2026-11-19 用户裁定由库存覆盖，不另购"],
    ["10u", 3, 10, None, "CVREF；去耦（直插件）"],
    ["4.7n", 0, 1, None, "备用（老师件瓷片 472）"],
    ["100u", 3, 12, "库存覆盖", "CVREF 等。SMD ×10 + 老师件 10V ×2；直插位由购物车 16V 20 只覆盖"],
]
caps = []
for cap, need, have, override, use in caps_raw:
    status = override if override else ("须购" if have == 0 else "足够")
    caps.append([cap, need, have, None, status, use, CAP_TAG.get(cap, "")])
start = r
r = body(ws, r, caps, numeric_cols=(2, 3), center_cols=(1, 2, 3, 4, 5))
for i, row in enumerate(caps):
    if row[4] not in ("封装不符", "库存覆盖"):
        ws.cell(row=start + i, column=4, value=f"=MAX(0,B{start + i}-C{start + i})")
    else:
        ws.cell(row=start + i, column=4, value=0)
paint(ws, start, r, 5, 5, {"须购": (BUY_FILL, BUY_FONT), "足够": (OK_FILL, OK_FONT),
                          "封装不符": (WARN_FILL, WARN_FONT), "库存覆盖": (OK_FILL, OK_FONT)})
r += 1
ws.cell(row=r, column=1, value="须购电容 4 种（2.4/11/27/47 pF；2.2 pF 已在手 10 只可作 CK 第一档，2.7 pF 为第二档）。"
        "**2026-11-19 更正：直插 100nF 与 100µF 改判「库存覆盖」，不再列入须购**（用户裁定）。"
        "27p/33p 为 470nH 新起点的 CT 固定段；30p/39p 转为电感角点备档。").font = Font(name=FONT, size=10, bold=True, color="9C0006")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
r += 2

ws.cell(row=r, column=1, value="§4.1 须购电容与标准值").font = Font(name=FONT, size=11, bold=True, color="1F4E79")
r += 1
r = section_header(ws, r, [("网表值 pF", 1, 1), ("用途", 2, 3), ("建议买 pF", 4, 5), ("说明", 6, 6)])
capbuy = [
    ["2.4", "CK 腔间耦合", "2.4", "C0G ±0.25 pF 档；±0.1 pF 直插件几乎不存在，须多买筛选"],
    ["11", "COUT 输出耦合", "11", "C0G ±2%"],
    ["27", "CT1 固定段（470nH 起点）", "27", "C0G ±5%（±2% 无货源，降级须记录）"],
    ["47", "CENV 包络滤波", "47", "C0G ±5%、50 V 以上；CENV 影响调制度，须实测"],
]
for val, use, buy, note in capbuy:
    for c1, c2, v, al in [(1, 1, val, CENTER), (2, 3, use, WRAP), (4, 5, buy, CENTER), (6, 6, note, WRAP)]:
        if c1 != c2:
            ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
        c = ws.cell(row=r, column=c1, value=v)
        c.font = BODY
        c.alignment = al
        for cc in range(c1, c2 + 1):
            ws.cell(row=r, column=cc).border = BOX
    ws.row_dimensions[r].height = 26
    r += 1
r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
c = ws.cell(row=r, column=1, value="2.4 pF 是最需要留意的一项：普通 C0G 的容差是 ±0.25 pF，而 CK 决定两腔耦合。"
                                   "**2.2 pF 已在手 10 只**（网表 2.485 pF，−11%）可作第一档，2.7 pF 为第二档。"
                                   "若须覆盖 2.4–2.7 pF，需另购 2–6 pF 微调——现有 CCW12（3.5–20 pF）与 CYM1（3–18 pF）都到不了。")
c.font = Font(name=FONT, size=10, color="9C6500")
c.fill = WARN_FILL
c.alignment = WRAP
ws.row_dimensions[r].height = 32
ws.freeze_panes = "A4"

# ============ 6 采购单 ============
ws = wb.create_sheet("采购单")
r = title(ws, "§7 采购单（按阻塞顺序）",
          "※ 行尾标「11-18 替换」的，按“替代候选”表的新料号下单；md §7 尚未同步这些改动", 7)
cols = ["项", "规格", "数量", "单位", "估价", "依据 / 说明", "11-18 变更"]
widths = [26, 38, 8, 7, 18, 40, 26]
r = header(ws, r, cols, widths)

NEW = "11-18 替换"
batches = [
    ("第一批", [
        ["2N3904BU", "onsemi TO-92", 10, "只", "¥1.27@10 量级", "§2，缺口 4 只，多买备用", ""],
        ["10 Ω 电阻", "±0.1%、金属膜非绕线、≥0.25 W", 5, "只", "略高于普通 1% 件", "§3.1，RSENSE，精度不可降级", ""],
        ["SOIC-8→DIP-8 转接板", "1.27 mm 间距，逐脚直通", 5, "块", "¥10 / 5 片", "③序号37，挂账两轮未下单；OPA197 共 3 只，需 1 用+1 备+1 换档", "提为最高优先：先调 OPA197 小板"],
        ["953 Ω 电阻", "1%、1/4W", 10, "只", "¥0.25 / 10 只", "③序号36，S05 独立 LC 板可拆负载 RMEAS", ""],
        ["电阻套件（10 种 × 10 只）", "见“第一批电阻单值”表", 1, "套", "低价", "§3，取消拼凑后的新增需求", ""],
        ["20 kΩ 多圈微调", "±10%、多圈", 2, "只", "—", "§3.3，RVRF 与幅度调节", ""],
        ["430 kΩ 电阻", "1%、1/4W，单个不串并联", 2, "只", "—", "OPA197 反馈 RFB，G=44", "＋新增（G44 主候选）"],
        ["390 kΩ 电阻", "1%、1/4W", 2, "只", "—", "OPA197 反馈 RFB，G=40", "＋新增（G40 对照，不达标）"],
    ]),
    ("第二批", [
        ["78FR47K-RC 470 nH", "Bourns，±10%、轴向直插，Q≥40@25 MHz", 2, "只", "—", "替代 132-17L，§5 更正", NEW + "（原 132-17L）"],
        ["BFC280905217 微调", "Vishay，2–18 pF、直插", 2, "只", "—", "替代 BFC280905003，核对孔距与引脚", NEW + "（原 05003）"],
        ["27 pF C0G", "±5%（±2% 无货源）、50 V、直插", 3, "只", "—", "CT1 固定段，470 nH 起点（购物车 ×2 份＝20 只）", "＋新增"],
        ["33 pF C0G", "±2%、50 V、直插", 1, "只", "—", "CT2 固定段，470 nH 起点（在手 50 只覆盖）", "改：由库存覆盖"],
        ["22 pF C0G", "±5%、50 V、直插", 2, "只", "—", "电感偏高角点的 CT1 固定段 + 天线匹配（购物车 ×1 份）", "＋新增"],
        ["30 / 39 pF C0G", "±2%、50 V、直插", 0, "只", "库存覆盖", "电感偏低角点的 CT2 备档；在手 30p×10、39p×10，不另购", "改：转备档"],
        ["2.4 pF C0G", "±0.25 pF（C 档）、50 V", 10, "只", "—", "CK，§4.1；±0.1 pF 无依据；2.2 pF 在手可作第一档", "降规格：±0.1→±0.25"],
        ["11 pF C0G", "±2%、50 V", 5, "只", "—", "COUT", ""],
        ["47 pF C0G", "±5%、50 V 以上", 10, "只", "—", "CENV（已确值，非换值件）", ""],
        ["直插 100 nF", "X7R 或 C0G、50 V、直插", 0, "只", "不下单", "③序号85；**2026-11-19 用户裁定由库存直插 104 覆盖，缺口按 0 计**", "11-19 复核：库存覆盖，不下单"],
        ["直插 100 µF", "16 V、5×11 mm、直插，脚距 2.5 mm", 5, "只", "—", "③序号86；现有为 SMD，直插位由购物车 16V 20 只覆盖（未付款）", "11-19 改：数量 10→5，规格补脚距"],
    ]),
    ("第三批", [
        ["天线与机械", "见“天线机械”表（含 NanoVNA 一套）", 1, "批", "—", "§6，等发射机能输出稳定载波与包络之后再买", ""],
        ["L_match 可调电感", "2.2–4.4 µH 连续可调，或抽头＋细调", 1, "只", "—", "AM-ALT.3 §7.1：固定 2.96 µH 不成立", "＋新增（原表缺失）"],
    ]),
]
for name, items in batches:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
    c = ws.cell(row=r, column=1, value=f"　{name}")
    c.font = Font(name=FONT, size=11, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor="2E75B6")
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[r].height = 22
    r += 1
    for it in items:
        for i, v in enumerate(it, start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = BODY
            c.border = BOX
            c.alignment = CENTER if i in (3, 4) else WRAP
            if i == 3:
                c.number_format = "0"
        tag = it[6]
        if tag:
            fill = BUY_FILL if tag.startswith("11-18") else PatternFill("solid", fgColor="FCE4D6")
            ws.cell(row=r, column=7).fill = fill
            ws.cell(row=r, column=7).font = BUY_FONT if tag.startswith("11-18") else Font(name=FONT, size=10, color="833C00")
        ws.row_dimensions[r].height = 30
        r += 1
ws.freeze_panes = "A4"

# ============ 7 第一批电阻单值 ============
ws = wb.create_sheet("第一批电阻单值")
r = title(ws, "第一批电阻单值（每值 10 只）",
          "10 Ω 已单列在采购单中，不重复计入；953 Ω 属 S05 独立 LC 板，同样单列", 4)
cols = ["网表值 Ω", "买 Ω", "数量", "备注"]
widths = [14, 12, 9, 44]
r = header(ws, r, cols, widths)
rlist = [
    ["50", "51", 10, "E24；也可用 49.9 Ω（E96），偏差 ±2.0%"],
    ["150", "150", 10, "E24 标准值"],
    ["200", "200", 10, "E24 标准值"],
    ["1.25k", "1.2k", 10, "偏差 −4.0%，影响 QCE 工作点"],
    ["2.2k", "2.2k", 10, "E24 标准值"],
    ["3.3k", "3.3k", 10, "E24 标准值"],
    ["15k", "15k", 10, "E24 标准值"],
    ["30k", "30k", 10, "E24 标准值"],
    ["37k", "36k", 10, "偏差 −2.7%，影响调制度 m，须实测复核"],
    ["40k", "39k", 10, "偏差 −2.5%，影响 QCE 静态电流"],
]
start = r
r = body(ws, r, rlist, numeric_cols=(3,), center_cols=(1, 2, 3))
paint(ws, start, r, 4, 1, {})
r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
c = ws.cell(row=r, column=1, value="合计 10 种 × 10 只 = 100 只电阻（不含单列的 10 Ω 与 953 Ω）。")
c.font = BODY_B
c.fill = SUB_FILL
c.alignment = WRAP
ws.freeze_panes = "A4"

# ============ 8 天线机械 ============
ws = wb.create_sheet("天线机械")
r = title(ws, "§6 天线与机械（第三批）", "等发射机通了再买", 4)
cols = ["项", "规格", "数量", "说明"]
widths = [20, 46, 12, 60]
r = header(ws, r, cols, widths)
ant = [
    ["可伸缩拉杆", "1 m 级，端部可改 SMA", "1", "手台拉杆 27–39 MHz ¥31–39，多为 1.3 m，需截到 1.000 m"],
    ["裸铜线", "Ø1.0 mm 实心", "6 m", "辐射体 1 m + 8×0.5 m 径向 + 裁切余量"],
    ["加载电感", "1812CS-392（C40634571）、1812CS-332（C38021502）", "各 1–2", "392 先上，332 做 A/B"],
    ["C0G 电容", "8.2 / 10 / 22 / 68 pF（单只，不拼）", "各若干", "8.82 pF 与 58.85 pF 需按实际容值重算电容串"],
    ["同轴跳线", "SMA 转 SMA，30–50 cm", "2", "外皮参与共模，长度须记录"],
    ["非金属底座", "PTFE / 尼龙 / 干木板，60×60×10 mm 级", "1", "正端与地网汇接端绝缘分离"],
    ["垫高柱", "Ø30 mm 尼龙", "8", "径向线末端离桌，汇点高度 0.83 m"],
    ["黄铜夹线件", "M3 级", "2", "正端 1 组 + 地网汇接 1 组，汇接区尽量 ≤10 mm"],
    ["尼龙拉线", "Ø0.3–0.5 mm", "5 m", "3 条扶正 1 m 导体，禁用金属拉线"],
    ["桌面锚点", "非金属可移除", "3", "防止触碰倾倒"],
    ["NanoVNA", "H4 或同类，含开路/短路/负载校准件", "1 套", "没有它测不出 31 MHz 复数阻抗"],
]
start = r
r = body(ws, r, ant, center_cols=(3,))
for rr in range(start, start + len(ant) - 1):
    ws.row_dimensions[rr].height = 30
for c_ in range(1, 5):
    ws.cell(row=r - 1, column=c_).fill = BUY_FILL
    ws.cell(row=r - 1, column=c_).font = BUY_FONT
r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
ws.cell(row=r, column=1, value="SMA 母座已有 3 只（KH-SMA-K513-G），不必再买。").font = Font(name=FONT, size=9, italic=True)
r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
c = ws.cell(row=r, column=1, value="注意：C_ant 的 8.913 pF 与 392/332 的匹配电容原是按“可并联”设计的。改为单只电容后，可用档位变稀疏，调谐精度下降，必须靠微调电容补偿。")
c.font = Font(name=FONT, size=10, color="9C6500")
c.fill = WARN_FILL
c.alignment = WRAP
ws.row_dimensions[r].height = 32
ws.freeze_panes = "A4"

# ============ 9 阻塞与待决 ============
ws = wb.create_sheet("阻塞与待决")
r = title(ws, "§5 / §8 阻塞与待决事项", "2026-11-19 更正：132-17L 与 BFC280905217 均非“无货源”，而是“有货但贵/无零售”，替代方案已定", 4)
cols = ["类别", "项", "现状 / 内容", "影响 / 待决"]
widths = [16, 24, 58, 46]
r = header(ws, r, cols, widths)
items = [
    ["已解除·有货但贵", "LSEL1/2",
     "原要求 Coilcraft 132-17L，460 nH ±5%，直插 2 只（配对需 6 只）。2026-11-19 查实：淘宝「栀庐清坐优选」有原厂现货，¥136/只，2 只 ¥272、6 只约 ¥816 —— 不是无货源，是单价过高",
     "已改判：选 Bourns 78FR47K-RC 470 nH（±10%，轴向，¥2.58/只），接收链不再阻塞"],
    ["已解除·无零售", "CTUNE1/2 微调",
     "原要求 Vishay BFC280905003 / 05217（2–18 pF）。属分销渠道件（得捷/贸泽有货），淘宝无零售；0.5 系列两者容量相同，差异在防助焊剂罩",
     "已改判：用 CCW12 陶瓷微调 3.5–20 pF（¥18.8/10 只）覆盖，定型后再考虑原厂件"],
    ["替代方案不成立", "7×7 骨架自绕", "骨架标称量程 200–370 nH，且不含线圈；31 MHz 下 Q 与插芯后 SRF 无任何数据",
     "自绕 460 nH 在量程外且 Q 未知，不构成可用替代"],
    ["出路 1（已执行）", "改 Bourns 78FR47K-RC", "470 nH ±10% 轴向，购物车 ×5（未付款）；代价 G31 −1.75 dB（Q31=40）／−4.89 dB（Q31=25 压力点），见「替代候选」风险①", "已采纳"],
    ["出路 2", "买 146-07J08L", "231–350 nH，Q≥72@50 MHz，作细调件", "量程不足 460 nH，不能单独替代"],
    ["出路 3", "改接收拓扑", "提高中频或改单调谐", "属仿真工作，与“暂停大规模仿真”的决定冲突"],
]
start = r
r = body(ws, r, items, center_cols=(1,))
for rr in range(start, r):
    ws.row_dimensions[rr].height = 40
    ws.cell(row=rr, column=1).font = BODY_B
r += 1

ws.cell(row=r, column=1, value="§8 本台账没有解决的事").font = Font(name=FONT, size=11, bold=True, color="1F4E79")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
r += 1
r = section_header(ws, r, [("#", 1, 1), ("事项", 2, 2), ("说明", 3, 4)])
unresolved = [
    [1, "价格未核查", "除标注者外沿用原台账快照"],
    [2, "132-17L 已查实有货（¥136/只）", "贵而不缺；若后续要求原厂口径，可随时改回，金额约 ¥272（2 只）或 ¥816（6 只配对）"],
    [3, "S9013 未验证", "无 SPICE 模型，不做 31 MHz 替代 2N3904 的假设"],
    [4, "网表与实物不一致", "买标准值会使 §3.2 的偏差影响偏置点与调制度，装配后须实测工作点并把实际阻值/容值回填，不能沿用仿真数值当验收基线"],
    [5, "调谐余量下降", "取消并联后匹配电容可选档位变少，须靠微调电容补偿，不能靠“多并几只”解决"],
]
start = r
r = body(ws, r, unresolved, numeric_cols=(1,), center_cols=(1,))
for rr in range(start, r):
    ws.merge_cells(start_row=rr, start_column=3, end_row=rr, end_column=4)
    ws.row_dimensions[rr].height = 30
ws.freeze_panes = "A4"

# ============ 10 可调与换值件 ============
ws = wb.create_sheet("可调与换值件")
r = title(ws, "可调件与实测后换值件清单",
          "每一行都注明证据出处；「无证据」指文档里找不到依据、按普通定值件处理", 6)

LEGEND = ("证据分级：A=文档明写可调/微调；B=文档明确指定备选值、实测后换；"
          "C=仿真校准值、实物须回填；D=精度/筛选件，非换值但须挑；E=无证据、按定值件")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
c = ws.cell(row=r, column=1, value=LEGEND)
c.font = Font(name=FONT, size=9, italic=True, color="7F6000")
c.fill = PatternFill("solid", fgColor="FFF2CC")
c.alignment = WRAP
ws.row_dimensions[r].height = 32
r += 2

cols = ["侧", "位号 / 器件", "网表值", "类别", "证据等级", "证据出处与说明"]
widths = [7, 22, 20, 16, 10, 78]
r = header(ws, r, cols, widths)

groups = [
    ("发射端 · 可调件（A 级：文档明写必须可调）", "2E75B6", [
        ["发射", "RVRF", "20 kΩ 多圈微调\n网表 15288.9 Ω", "可调（两脚变阻）", "A",
         "§3.3；定 20 kHz 包络频率（RFIX 22k 串联 + CT 1n）。用在 76.4% 处，须多圈"],
        ["发射", "RVDT/RVDB", "10 kΩ 电位器\n7362.5 / 2637.5 Ω", "可调（三脚分压）", "A",
         "§3.3；两段和 = 10000 Ω 整，动片 73.6%。定 PWM 占空比阈值。已持有 10 kΩ 微调 ×5"],
        ["发射", "RVAT/RVAB", "20 kΩ 电位器\n931.3 / 19068.7 Ω", "可调（三脚分压）", "A",
         "§3.3；两段和 = 20000 Ω 整，动片 4.66%。定调制度 m。AM-ALT.2 §4 给出四档校准位置："
         "15101.8/9897.6/5049.1/931.3 Ω = 1/2/3/4 Vpp。单圈件在此处分辨率不足，须多圈"],
        ["发射", "L_match（天线调谐）", "2.9572 µH 定值", "★必须改为可调", "A",
         "AM-ALT.3 §7.1：C_ant 偏 ±15% 使天线电流掉到约 1/3，**固定 2.96 µH 不成立**，"
         "需 2.2–4.4 µH 连续可调。02_勘误 §7.1 明确“按定值采购会造成误购”"],
    ]),
    ("发射端 · 确值件（实测/对照后已定，不必再换）", "548235", [
        ["发射", "CENV", "47 pF", "已确值", "B+",
         "AM-ALT.2 §5 做过 22/47/100/220 pF 四档对照：47 pF 过冲 1.32% 最佳，100/220 pF 削窄脉冲。"
         "这是**有实验依据的定值**，不是估计值——台账说“须实测”但对照已经做过了"],
        ["发射", "RMINJ", "37k（买 36k）", "改值件", "C",
         "AM-ALT.2 §5；37k 可用 36k+1k 串联，但用户已定“不串并联”，故买 36k（−2.7%）。"
         "影响调制度 m，装配后须实测复核"],
        ["发射", "RPRE", "10k", "已确值", "B",
         "AM-ALT.2 §9.3 主候选；曾对比 1.5k/10k、100k 注入、OPA197 跟随器三条路线，10k 胜出"],
        ["发射", "RPU1/RPU2", "2.2k", "已确值", "B",
         "AM-ALT.2 §4 主候选；1.5k 上拉仅作对照未采用"],
    ]),
    ("接收端 · 可调件（A 级）", "2E75B6", [
        ["接收", "CTUNE1/2", "39.59 / 45.83 pF\n（含 1 pF 布局预算）", "可调电容", "A",
         "S05_11/S05_09 §6.2；**2026-11-19 更正：470 nH 起点的实物 = 固定 27/33 pF ∥ 微调 11.09/12.38 pF**"
         "（30/39 pF 是 132-17L 时代旧值，保留作电感角点）。"
         "**寿命仅 10 次全行程**（Vishay 手册），不是扫频旋钮"],
        ["接收", "L1/L2", "470 nH（网表）\n460 nH（采购）", "★必须可调/配对", "A",
         "S05_09 §6.1：备 6 只做配对（两只 Q 接近时双调谐最对称）；S05_08 §8.2 给出 19 组重调条件"
         "所需微调位置 5.84–14.97 / 5.67–11.12 pF"],
    ]),
    ("接收端 · 换值件（B 级：文档已指定备选值，实测后换）", "BF8F00", [
        ["接收", "CK", "2.485 pF（网表）\n2.4 pF（采购）", "换值件", "B",
         "S05_09 §6.3/§4.5：另备 2.2/2.7 pF 各 3 只；判据“带宽<1.5 MHz → 换 2.7 pF”。"
         "**不能与原 CK 并联**（B1 §138）。注：网表 2.485 pF 与采购 2.4 pF 已不一致"],
        ["接收", "CSEL", "14.529 pF（网表）\n15 pF（采购）", "换值件", "B",
         "S05_08 §8.1：另备 18/20 pF 观察匹配-带宽权衡。放开 CSEL 可做到回波损耗 20.08 dB，"
         "但带宽 1.9201→1.6479 MHz，未替换进主网表"],
        ["接收", "COUT", "10.81 pF（网表）\n11 pF（采购）", "改值件", "C",
         "S05_09 §6.3：或 10 pF∥1.0 pF，但须重算焊盘"],
        ["接收", "CT1 固定段", "27 pF（470 nH 起点）", "换值件", "B",
         "**2026-11-19 更正：27 pF 是 470 nH 起点**（原写 30 pF 属 132-17L 旧值）。"
         "S05_09 §4.5 判据“调不到 31 MHz → 换固定档 22/27/30/33/36 pF”"],
        ["接收", "CT2 固定段", "33 pF（470 nH 起点）", "换值件", "B",
         "**2026-11-19 更正：33 pF 是 470 nH 起点**（原写 39 pF 属 132-17L 旧值）；"
         "在手 33 pF 50 只、39 pF 10 只，覆盖电感角点"],
        ["接收", "CEXT（测试夹具）", "TBD（未定值）", "★未定值", "B",
         "S05_10 §19：买 C0G 10/11/12/13 pF 各 3 + 0.5/1 pF 补偿，**按实际探头电容选配**。"
         "S05_11 §107 明确标 TBD，不是采购定值"],
    ]),
    ("接收端 · 筛选/精度件（D 级：不换值但要挑）", "9C0006", [
        ["接收", "CK（若坚持 ±0.1 pF）", "—", "筛选件", "D",
         "台账 §4.1 写“±0.1 pF”，但 S05_09 原文是“精度**尽量** ±0.1 pF”，无计算依据。"
         "标准 C0G 容差为 ±0.25 pF（C 档）；±0.1 pF（B 档）需按料号去 DigiKey 订或买 20 只实测筛"],
        ["接收", "RPORT", "1 MΩ 1%", "精度件", "D", "S05_09 §6.3；1% 金属膜"],
        ["接收", "RSENSE（TX）", "10 Ω", "精度件", "D",
         "台账 §3.1；±0.1%、金属膜非绕线、≥0.25 W，决定全部功率读数绝对值，不可降级为 1%"],
    ]),
    ("两侧 · 无换值证据（E 级：按定值件处理，别再猜）", "7F7F7F", [
        ["两侧", "其余全部电阻", "见“电阻”表", "定值", "E",
         "驱动级 RDC/RDB1/RDB2/RDE/REF 在 06_ABCDE 报告中明确“保持不变/冻结”；"
         "接收侧 Q1/Q2 偏置（22k/4.7k/33/220/330p）未见任何换值表述"],
        ["两侧", "其余全部电容", "见“电容”表", "定值", "E",
         "33 p 晶振负载、1n/100p/330p/10n 等在手件，文档无备选值、无换值判据"],
    ]),
]

grade_fill = {"A": WARN_FILL, "B": PatternFill("solid", fgColor="FCE4D6"),
              "C": PatternFill("solid", fgColor="FFF2CC"), "D": BUY_FILL, "E": OK_FILL, "B+": OK_FILL}
grade_font = {"A": WARN_FONT, "B": Font(name=FONT, size=10, color="833C00"),
              "C": Font(name=FONT, size=10, color="7F6000"), "D": BUY_FONT, "E": OK_FONT,
              "B+": OK_FONT}

for gname, gcolor, rows in groups:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    c = ws.cell(row=r, column=1, value="　" + gname)
    c.font = Font(name=FONT, size=11, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=gcolor)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[r].height = 24
    r += 1
    for row in rows:
        for i, v in enumerate(row, start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = BODY
            c.border = BOX
            c.alignment = CENTER if i in (1, 4, 5) else WRAP
        g = row[4]
        ws.cell(row=r, column=5).fill = grade_fill.get(g, OK_FILL)
        ws.cell(row=r, column=5).font = grade_font.get(g, BODY)
        if "★" in row[3] or "★" in row[1]:
            for cc in range(1, 7):
                ws.cell(row=r, column=cc).fill = BUY_FILL
            ws.cell(row=r, column=2).font = BUY_FONT
        ws.row_dimensions[r].height = 46
        r += 1

r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
c = ws.cell(row=r, column=1,
            value="结论：真正“必须可调”的只有 5 项（RVRF、RVDT/RVDB、RVAT/RVAB、L_match、CTUNE1/2），"
                  "加 L1/L2 配对；真正“实测后换值”的 6 项（CK、CSEL、COUT、CT1/CT2 固定段、CEXT）。"
                  "其余都是定值件。台账原文把 CENV 也写成“须实测”，但 AM-ALT.2 的 22/47/100/220 pF 对照已经做过，"
                  "它属确值件不是换值件。")
c.font = Font(name=FONT, size=10, bold=True, color="833C00")
c.fill = PatternFill("solid", fgColor="FCE4D6")
c.alignment = WRAP
ws.row_dimensions[r].height = 46

ws.freeze_panes = "A6"

# ============ 11 替代候选（2026-11-18） ============
ws = wb.create_sheet("替代候选")
r = title(ws, "2026-11-18 替代候选（Codex 会话 01a1ecb7）",
          "来源：replacement_20261118/{README,RESULTS}.md ｜ 均为仿真，未采购、未焊接、未做 6 m 实测", 6)

ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
c = ws.cell(row=r, column=1,
            value="背景：台账 §5 原写“本项目唯一没有替代方案的阻塞”。2026-11-18 更正为“原料号缺货，不是没有替代方案”；2026-11-19 再更正为“有货但贵（¥136/只）/ 淘宝无零售”，替代方案已落地。"
                  "本节记录新料号与验证结果，并列出核对时发现的三处风险。")
c.font = Font(name=FONT, size=9, italic=True, color="7F6000")
c.fill = PatternFill("solid", fgColor="FFF2CC")
c.alignment = WRAP
ws.row_dimensions[r].height = 32
r += 2

VW = [17, 23, 26, 8, 11, 62]
for col_, w_ in zip("ABCDEF", VW):
    ws.column_dimensions[col_].width = w_

band("一、料号变更对照", "2E75B6")
r = section_header(ws, r, [("位置", 1, 1), ("原料号 / 值", 2, 2), ("新料号 / 值", 3, 3),
                           ("数量", 4, 4), ("状态", 5, 5), ("说明", 6, 6)])
swaps = [
    ["LSEL1/2", "Coilcraft 132-17L\n460 nH ±5%", "Bourns 78FR47K-RC\n470 nH ±10%", "2", "主候选",
     "Q≥40@25 MHz、SRF≥270 MHz、DCR≤0.11 Ω、轴向直插。31 MHz 的 Q 无厂家数据，仿真按 Q31=40，另设 25 压力点"],
    ["CTUNE1/2", "Vishay BFC280905003", "Vishay BFC280905217", "2", "主候选",
     "同为 2–18 pF，差别是不带防助焊剂罩；须核对孔距与引脚，并用低残留助焊剂＋焊后清洁"],
    ["RFB", "210 kΩ", "430 kΩ", "1", "主候选",
     "OPA197 反馈电阻，G = 1+430/10 = 44。另备 390 kΩ 作 G40 对照"],
    ["RFB（对照）", "—", "390 kΩ", "1", "不达标",
     "G40 名义输出 3.80 Vpp < 4 V，不作为达标档"],
    ["（已撤销）", "Vishay IRF24ERR47M", "—", "—", "已排除",
     "列入 Vishay 2026-08-21 停产通知，撤下主选；证据 sources/vishay_irf_termination.pdf。此自我纠正正确"],
]
start = r
r = body(ws, r, swaps, center_cols=(4, 5))
for i in range(start, r):
    st = ws.cell(row=i, column=5).value
    fill = OK_FILL if "主候选" in str(st) else (WARN_FILL if "不达标" in str(st) else PatternFill("solid", fgColor="D9D9D9"))
    ws.cell(row=i, column=5).fill = fill
    ws.row_dimensions[i].height = 44
r += 1

band("二、仿真结果（RESULTS.md，RF 激励 9.60438 mV 峰值、m=26.449%、9 V）", "2E75B6")
r = section_header(ws, r, [("用例", 1, 1), ("原始 Vpp", 2, 2), ("稳健 Vpp (2%–98%)", 3, 3),
                           ("最低 V", 4, 4), ("最高 V", 5, 5), ("备注", 6, 6)])
sims = [
    ["G22_D50", 2.0919, 2.0908, 1.945, 4.037, "原增益 22 基准；注意：本轮 G22 只有 2.09 Vpp，而台账/汇报用的是 2.427 Vpp（见风险①）"],
    ["G40_D50", 3.8024, 3.8009, 1.082, 4.884, "G40 未达 4 Vpp，不作为达标档"],
    ["G44_D10", 4.1825, 4.1633, 2.560, 6.742, "★ 最高电压 6.742 V，全表最高，已逼近 9 V 供电上限（见风险③）"],
    ["G44_D10_half", 2.1117, 2.1009, 2.779, 4.891, "半幅：比例误差 0.927%"],
    ["G44_D30", 4.1879, 4.1856, 1.723, 5.911, "三档中幅度最高"],
    ["G44_D50", 4.1830, 4.1812, 0.890, 5.073, "★ 主候选名义点，对 4 V 余量仅 4.08%"],
    ["G44_D50_fine_retry", 4.1868, 4.1850, 0.890, 5.077, "步长 0.25 ns 对照，与 0.5 ns 差 0.0904%"],
    ["G44_D50_half", 2.1153, 2.1133, 1.934, 4.049, "半幅：比例误差 1.086%"],
    ["G44_D50_loss", 2.3268, 2.3259, 1.826, 4.152, "★ 损耗压力点（Q31=25、电容 Q=200）掉到 2.33 Vpp，−44%"],
]
start = r
r = body(ws, r, sims, numeric_cols=(2, 3), center_cols=(1, 2, 3, 4, 5))
for i, row in enumerate(sims):
    ws.cell(row=start + i, column=2).number_format = "0.0000"
    ws.cell(row=start + i, column=3).number_format = "0.0000"
    ws.cell(row=start + i, column=4).number_format = "0.000"
    ws.cell(row=start + i, column=5).number_format = "0.000"
    ws.row_dimensions[start + i].height = 28
r += 1

band("三、核对发现的风险（本表补充，Codex 报告未并列呈现）", "C00000")
r = section_header(ws, r, [("#", 1, 1), ("风险", 2, 2), ("依据", 3, 5), ("说明", 6, 6)])
risks = [
    [1, "增益提升被换电感的损耗抵掉一部分",
     "RESULTS 2.0919→4.1830 = 2.000 倍；电阻比 430/210 = 2.048 倍", "",
     "", "差的 2.4% 来自 Bourns 电感。同口径 AC：Bourns 470 nH nominal G31=34.90；原 132-17L 在 Q31=66 时 G31=42.7"
     "（S05-07 §83）。换件后整腔增益低约 1.8 dB，两个型号不能按“都是 470 nH”等价"],
    [2, "余量 4.08% 承载不起未验证项",
     "G44_D50 稳健 4.1812 Vpp；压力点 2.3259 Vpp（−44%）", "", "",
     "4% 余量要覆盖：电感 ±10% 容差、Q31 真实值、微调电容 Q、布局寄生、温度、BAT85 批次。任何一项没测准都会吃掉"],
    [3, "10% 占空比最高电压 6.742 V 未单独核查",
     "G44_D10 最高 6.742 V，比 G44_D50 的 5.073 V 高 1.67 V", "", "",
     "9 V 供电、约 3 V 参考，6.742 V 逼近上限。10% 占空比是最易先削顶的档位，而它恰好是唯一没做半幅对照的档位"],
    [4, "4 Vpp 门槛本身有适用范围歧义",
     "性能指标要求_N31_M50.md:58 / :145；P0_课程v3验收口径确认单.md:99", "", "",
     "表3 原文“v2 峰峰值不小于 4 V”，但 v1 降到 2 Vpp 时 v2 应为 2.4 Vpp < 4 V，同时执行自相矛盾；"
     "该事项已列为待教师答复。Codex 全程按 4 Vpp 硬指标优化，未引用这三处标注"],
    [5, "Q31 假设由 66 降为 40，基准被移动",
     "S05-08 用 Q31=66；本轮 78FR47K-RC 无 31 MHz 数据，取 Q31=40", "", "",
     "换电感后增益基准与历史报告不可直接比较；需补一份同 Q 假设下的 G22 vs G44 对照"],
]
start = r
for row in risks:
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=5)
    for i, v in enumerate([row[0], row[1], row[2], None, None, row[5]], start=1):
        if i in (4, 5):
            continue
        c = ws.cell(row=r, column=i, value=v)
        c.font = BODY
        c.border = BOX
        c.alignment = CENTER if i == 1 else WRAP
    for cc in range(1, 7):
        ws.cell(row=r, column=cc).border = BOX
    ws.cell(row=r, column=2).font = BUY_FONT
    ws.cell(row=r, column=2).fill = BUY_FILL
    ws.row_dimensions[r].height = 52
    r += 1
r += 1

band("四、尚未闭合的事项", "7F7F7F")
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
c = ws.cell(row=r, column=1,
            value="未采购、未焊接、未实测；冷启动、长时间稳定、6 m 无线、电池端功耗全部待实测。"
                  "md §7 采购单尚未同步本表的新料号（Codex 在 §5 自己也写了“配套旧 XLSX 尚未据新候选重制”）。"
                  "本表的“采购单”页已按新料号标注，以本表为准下单。")
c.font = Font(name=FONT, size=10, color="833C00")
c.fill = PatternFill("solid", fgColor="FCE4D6")
c.alignment = WRAP
ws.row_dimensions[r].height = 44

ws.freeze_panes = "A6"

# ============ 12 购物车核对（2026-11-18） ============
ws = wb.create_sheet("购物车核对")
r = title(ws, "淘宝购物车核对（2026-11-18 12:30 截图，共 54 项）",
          "逐项对照台账 §2–§7 与 11-18 替代候选；“判定”列可直接照做", 7)
cols = ["判定", "商家", "商品 / 选中规格", "数量", "价格", "对应位号", "说明"]
widths = [12, 24, 42, 8, 10, 20, 44]
for col_, w_ in zip("ABCDEFG", widths):
    ws.column_dimensions[col_].width = w_

KEEP = ("保留", OK_FILL, OK_FONT)
DEL = ("删除", BUY_FILL, BUY_FONT)
BUY = ("补购", WARN_FILL, WARN_FONT)
DUP = ("二选一", PatternFill("solid", fgColor="FCE4D6"), Font(name=FONT, size=10, color="833C00"))
CHK = ("核对", PatternFill("solid", fgColor="DDEBF7"), Font(name=FONT, size=10, color="1F4E79"))

groups = [
    ("一、建议保留（规格对、位置对）", "548235", [
        [KEEP, "天猫 zave旗舰店", "3296W 电位器 203（20K）×5只装", "×2", "¥3.7", "RVRF / RVAT",
         "20 kΩ 多圈，正是 §3.3 两只 20 kΩ 的位置。非重复，与下一行 103 阻值不同"],
        [KEEP, "天猫 zave旗舰店", "3296W 电位器 103（10K）×5只装", "×1", "¥3.7", "RVDT/RVDB",
         "10 kΩ 三脚分压。台账备注“已有 10 kΩ 微调 ×5”，此项可留可删，不重复"],
        [KEEP, "天猫 zave旗舰店", "2N3904 直插 NPN（50只）", "×1", "¥3.69", "全部 2N3904",
         "★ 硬阻塞第 1 条。标题写 S8550/SS8050 但选中规格是 2N3904，注意别改错规格"],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 39K", "×1", "¥2.13", "RDB1 40k→39k", ""],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 15K", "×1", "¥2.13", "RMT 15k", ""],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 3.3K", "×1", "¥2.13", "RMB 3.3k", ""],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 2.2K", "×1", "¥2.13", "RPU1/RPU2", "AM-ALT.2 主候选值"],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 1.2K", "×1", "¥2.13", "RDC 1.25k→1.2k", ""],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 200欧", "×1", "¥2.13", "REF 200", ""],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 150欧", "×1", "¥2.13", "RDE 150", ""],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 51欧", "×1", "¥2.13", "RSOURCE 50→51", ""],
        [KEEP, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 10欧", "×1", "¥2.13", "RSENSE 10Ω",
         "⚠ 1% 精度。台账 §3.1 要求 ±0.1%，此项仅作粗用；精密件见下方“补购”"],
        [KEEP, "淘宝 好博特", "云母电容 CMDB2A11PJ 100V 11PF", "×1", "¥2.2", "COUT 11 pF", "云母件，温漂优于 C0G"],
        [KEEP, "天猫 仁十众旗舰店", "(10只) NP0 100V 47pF ±5%", "×2", "¥7.66", "CENV 47 pF",
         "AM-ALT.2 已做 22/47/100/220 pF 对照，47 pF 为确值件"],
        [KEEP, "天猫 仁十众旗舰店", "(10只) NP0 100V 68pF ±5%", "×1", "¥7.66", "天线 C0G 档（§6）", ""],
        [KEEP, "天猫 仁十众旗舰店", "(10只) NP0 100V 22pF ±5%", "×1", "¥7.66", "CT 备用档 / 天线 22 pF", ""],
        [KEEP, "天猫 仁十众旗舰店", "(10只) NP0 100V 10pF ±5%", "×1", "¥7.66", "天线 C0G 档（§6）", ""],
        [KEEP, "天猫 仁十众旗舰店", "(10只) NP0 100V 8.2pF ±0.5", "×1", "¥8.33", "天线 8.2 pF（§6）", ""],
        [KEEP, "天猫 仁十众旗舰店", "(10只) NP0 100V 33pF ±5%", "×1", "¥7.66", "C1/C2 晶振负载", "台账在手 50，可少买"],
        [KEEP, "淘宝 老虎鱼官方店", "贴片 SOIC8 转直插转换板 LHY A（两个插针一块板）", "×1", "¥2", "OPA197 转接",
         "★ 硬阻塞第 3 条。注意“两个插针一个转换板”的表述，确认是 8 脚全通"],
        [KEEP, "淘宝 南京精密电阻厂", "高精度 0.1% 3W 5W BWL3W 14.8×5.2mm — 10R", "×1", "¥5.5", "RSENSE 10Ω",
         "★ 这才是 §3.1 要的 ±0.1% 金属膜。需确认“非绕线”——BWL 系列为绕线封装，须核对"],
        [KEEP, "淘宝 南京新飞凡", "RJ15 铜脚 0.5W 真正1% 金属膜 — 【10R】档 10只", "×1", "¥2.68", "RSENSE 备用", "1%，同 zave 的 10 欧，冗余"],
        [KEEP, "淘宝 南京新飞凡", "陶瓷微调电容 CCW12 10只 100V 3–5~20pF 黄点", "×1", "¥18.8", "CTUNE1/2",
         "★ 覆盖 2–18 pF 需求，接近 BFC280905217 规格。五选一里最合适"],
        [KEEP, "淘宝 栀庐清坐优选", "Coilcraft(线艺) 132-17L", "×1", "¥136", "LSEL1/2",
         "★ 原厂件确实有货！台账 §5 记“无货源”实为“贵”。买 1 只不够，需 2 只 = ¥272"],
        [KEEP, "天猫 特加特数码专营店", "TEJIATE SMA 转接线 0.3m SMA内螺内针转SMA内螺内针", "×1", "¥6.67", "SMA 跳线",
         "§6 要 30–50 cm ×2，此项 0.3m 偏短且只 1 条"],
        [KEEP, "淘宝 猎芯商城", "1812CS-332X_（1812 3.3µH）", "×2", "¥2.5", "加载电感 332", "§6 要 332 做 A/B，对"],
        [KEEP, "淘宝 猎芯商城", "1812CS-392X_（1812 3.9µH）", "×2", "¥4.5", "加载电感 392", "§6 要 392 先上，对"],
        [KEEP, "天猫 道冠旗舰店", "T2 紫铜丝 直径1mm × 1米", "×6", "¥1.75", "裸铜线 6 m",
         "6 根 = 6 米，满足 §6 要求（辐射体 1m + 8×0.5m + 余量）"],
        [KEEP, "淘宝 华诺铜材加工", "黄铜棒 直径3mm × 1米", "×1", "¥13.5", "黄铜夹线件（§6）",
         "§6 要 M3 级夹线件 2 组；3mm 棒料可加工，但需自行裁切"],
        [KEEP, "淘宝 芃赞企业店", "高精密金属膜 PY 千分之一 — 953R/欧姆", "×60", "¥0.25", "953 Ω RMEAS",
         "0.1% 953 Ω，正合 §7 第一批“953 Ω”一项，60 只远超 10 只需求"],
    ]),
    ("二、建议删除（规格错 / 量纲错 / 已足够）", "C00000", [
        [DEL, "淘宝 HK集科电子元件商城", "可调中周电感 通用型 5MH–82MH (7.4*8.2mm)", "×1", "¥28", "—",
         "★ 量纲错 1000 倍。项目要 460–470 nH（0.00046 mH），这个是 5–82 mH，完全不能用"],
        [DEL, "淘宝 深圳市万品佳科技", "可调电感 7*7-26T 2.1µH–6.8µH (2100nH–6800nH)", "×1", "¥0.66", "L_match（TX）",
         "下限 2100 nH 高于 470 nH，也不能做接收 LC。但 2.1–6.8 µH 覆盖 AM-ALT.3 的 L_match 2.2–4.4 µH 需求，可挪用途"],
        [DEL, "天猫 硕骑士旗舰店", "200nH–370nH 可调微调线圈 7*7 2.1µH~6.8µH（5只）", "×1", "¥7.85", "—",
         "台账 §5 已明确否定：量程 200–370 nH 不含 460 nH，且不含线圈。标题与规格自相矛盾"],
        [DEL, "天猫 risym旗舰店", "0307 色环电感 0.47µH（50个）", "×1", "¥3.51", "—",
         "0.47 µH 接近 470 nH，但色环电感 Q 与 SRF 无数据，不能替代 132-17L。若作实验备件可留"],
        [DEL, "淘宝 蜜蜂芯城", "10欧;1%;1/2W（50个）", "×1", "¥1.28", "RSENSE",
         "与 zave 的 10 欧重复；且仍为 1%，不能替代 ±0.1% 件"],
        [DEL, "天猫 硕骑士旗舰店", "1/4W 金属膜 1%【100个】10欧", "×1", "¥2.72", "RSENSE",
         "第三个 10 欧，重复"],
        [DEL, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 1M", "×1", "¥2.13", "RPORT 1M",
         "台账在手 50 只，已足够"],
        [DEL, "天猫 zave旗舰店", "1/4W 金属膜 1% 100只 — 22K", "×1", "¥2.13", "RBT1/2 22k",
         "台账在手 50 只，已足够"],
        [DEL, "天猫 硕骑士旗舰店", "5.5–6MM 可变电容 20PF（10个）", "×1", "¥6.44", "CTUNE（重复）",
         "与 CCW12 冲突，五选一"], 
    ]),
    ("三、微调电容五选一（只能留一个）", "BF8F00", [
        [KEEP, "淘宝 南京新飞凡", "CCW12 3–5~20pF 黄点 10只", "×1", "¥18.8", "CTUNE1/2",
         "★ 推荐留这个：覆盖 2–18 pF，容差与温度系数有标注"],
        [DUP, "淘宝 南京新飞凡", "微调电容 5P/10P/20P/30P/50P 铜芯 Φ5 100V 5~20P 黄", "×1", "¥15", "CTUNE（重复）",
         "同店第二个微调，与 CCW12 重叠，删"],
        [DUP, "淘宝 深圳赛格和泰电子", "CYM1 可调电容 3/18P 薄膜微调", "×1", "¥0.6", "CTUNE（重复）",
         "3–18 pF 范围可用，但单只 ¥0.6 寿命/温漂未知；作为备用可留 2 只，否则删"],
        [DUP, "天猫 海雀数码专营店", "可调电容 塑封6mm 20P 红色【一件5个】", "×1", "¥4.05", "CTUNE（重复）",
         "单一 20 pF 档，非连续可调，不能替代 2–18 pF 微调，删"],
        [DUP, "天猫 硕骑士旗舰店", "5.5–6MM 可变电容 20PF（10个）", "×1", "¥6.44", "CTUNE（重复）",
         "同上，删"],
    ]),
    ("四、必须补购（购物车里完全没有）", "2E75B6", [
        [BUY, "—", "78FR47K-RC 470 nH（Bourns）", "2", "—", "LSEL1/2（11-18 新主候选）",
         "★ Codex 替代方案的核心件，一个都没买。淘宝少有，需 DigiKey/Mouser"],
        [BUY, "—", "430 kΩ 1% 1/4W", "2", "—", "RFB（G=44）",
         "★ 11-18 替代方案第二个核心件。购物车电阻档位里没有 430K"],
        [BUY, "—", "390 kΩ 1% 1/4W", "2", "—", "RFB（G=40 对照）", "对照档，可与 430 kΩ 一起买"],
        [BUY, "—", "2.4 pF C0G（±0.25 pF, 50 V）", "10", "—", "CK",
         "须购件，全车无。仁十众那家若有 2.4p 可直接加"],
        [BUY, "—", "27 pF C0G ±2% 50 V", "3", "—", "CT1 固定段",
         "470 nH 的新调谐起点（原 30/39 pF 已不适用）"],
        [BUY, "—", "39 pF C0G ±2% 50 V", "3", "—", "CT2 固定段", "同上；注意车里 68p 不是 39 p"],
        [BUY, "—", "直插 100 nF（X7R 或 C0G, 50 V）", "10", "—", "CCOUP1 等",
         "库存只有 0805 贴片，直插位装不上"],
        [BUY, "—", "直插 100 µF（35 V）", "10", "—", "CVREF 等", "库存为 SMD"],
        [BUY, "—", "NanoVNA-H4 或同类（含校准件）", "1", "—", "§6 测量仪器",
         "★ 没有它测不出 31 MHz 复数阻抗，天线调谐无法进行"],
        [BUY, "—", "SMA 转 SMA 跳线 30–50 cm", "2", "—", "§6 同轴跳线",
         "车里只有 0.3 m ×1，长度不够、数量不够"],
        [BUY, "—", "尼龙垫高柱 Ø30 mm / 尼龙拉线 Ø0.3–0.5 mm / 非金属底座", "各 1 批", "—", "§6 机械件",
         "整批机械件全车无"],
    ]),
    ("五、需要核对（读数存疑或规格待确认）", "7F7F7F", [
        [CHK, "淘宝 南京精密电阻厂", "BWL3W 14.8×5.2mm 10R 0.1%", "×1", "¥5.5", "RSENSE",
         "BWL 为绕线封装，台账 §3.1 明写“非绕线”。★ 下单前必须问清是否金属膜非绕线"],
        [CHK, "淘宝 老虎鱼官方店", "贴片 SOIC8 转直插 LHY A", "×1", "¥2", "OPA197",
         "标题“两个插针一个转换板”，需确认是完整 8 脚 SOIC-8→DIP-8，非半板"],
        [CHK, "淘宝 栀庐清坐优选", "Coilcraft 132-17L", "×1", "¥136", "LSEL1/2",
         "§5 要 2 只（+ 配对需 6 只）。1 只不够，且 ¥136×2 需评估是否走 Bourns 替代"],
        [CHK, "天猫 特加特", "SMA 转接线 0.3m", "×1", "¥6.67", "SMA 跳线",
         "§6 要求 30–50 cm，0.3 m 在下限；且需 2 条"],
    ]),
]

for gname, gcolor, rows in groups:
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
    c = ws.cell(row=r, column=1, value="　" + gname)
    c.font = Font(name=FONT, size=11, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=gcolor)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[r].height = 24
    r += 1
    for tag, seller, item, qty, price, ref, note in rows:
        for i, v in enumerate([tag[0], seller, item, qty, price, ref, note], start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = BODY
            c.border = BOX
            c.alignment = CENTER if i in (1, 4, 5) else WRAP
        ws.cell(row=r, column=1).fill = tag[1]
        ws.cell(row=r, column=1).font = tag[2]
        ws.row_dimensions[r].height = 34
        r += 1

r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
c = ws.cell(row=r, column=1,
            value="结论：购物车 54 项里，因规格错或量纲错必须删的有 3 个（HK 的 mH 电感、万品佳的 2.1–6.8µH、硕骑士的 200–370nH）；"
                  "同件多买需二选一的有 4 组（10 Ω 电阻三份、微调电容五份、可调电感三份、拉杆天线两份）；"
                  "真正缺失的硬缺口是 78FR47K-RC 470 nH、430/390 kΩ、2.4 pF、27/39 pF、直插 100nF/100µF、NanoVNA、机械件。"
                  "★ 最重要两条：132-17L 原厂其实有货（¥136/只，非无货源）；2N3904 已在车内（zave，选中规格正确）。")
c.font = Font(name=FONT, size=10, bold=True, color="C00000")
c.fill = BUY_FILL
c.alignment = WRAP
ws.row_dimensions[r].height = 62

ws.freeze_panes = "A6"

wb.save(OUT)
print("saved", OUT)
