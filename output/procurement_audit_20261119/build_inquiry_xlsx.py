# -*- coding: utf-8 -*-
"""生成对外《器件询价单》Excel（客观版，无背景叙述）。

内容只保留：型号、规格要求、封装、用量、询价量、工艺备注，
以及留给报价方填写的厂家/料号/单价/交期列，小计自动计算。
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = r"D:\实验报告文件夹\电路2\output\procurement_audit_20261119\器件询价单_20261119.xlsx"

INK = "172D41"
HEAD = "173B55"
STRIPE = "F2F6F9"
SOFT = "607486"
FILLIN = "FFF0DB"
BROWN = "9C4500"
GREEN = "EAF4EC"
GREY = "EDEFF1"
FONT = "Microsoft YaHei"

thin = Side(style="thin", color="D8DEE4")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def shell(wb, name, title, note, headers, widths, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = name
    ws.sheet_view.showGridLines = False
    last = get_column_letter(len(headers))

    ws["A2"] = title
    ws["A2"].font = Font(name=FONT, size=15, bold=True, color=INK)
    ws.merge_cells(f"A2:{last}2")
    ws.row_dimensions[2].height = 26

    ws["A4"] = note
    ws["A4"].font = Font(name=FONT, size=10, color=SOFT)
    ws.merge_cells(f"A4:{last}4")
    ws["A4"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[4].height = 32

    r = 6
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=HEAD)
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = BORDER
    ws.row_dimensions[r].height = 34

    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w

    ws.freeze_panes = ws.cell(row=r + 1, column=1)
    return ws, r


def rows_out(ws, start, rows, height=58, center=()):
    for i, row in enumerate(rows):
        rr = start + i
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=rr, column=c, value=v)
            cell.font = Font(name=FONT, size=10, color=INK)
            cell.alignment = Alignment(
                wrap_text=True, vertical="center",
                horizontal="center" if c in center else "left",
            )
            cell.border = BORDER
            if i % 2 == 1:
                cell.fill = PatternFill("solid", fgColor=STRIPE)
        ws.row_dimensions[rr].height = height
    return start + len(rows) - 1


wb = Workbook()

# ───────────────────────── 询价单 ─────────────────────────
H1 = ["序号", "器件类别", "型号 / 参考型号", "规格要求", "封装要求",
      "单套用量", "建议询价量", "工艺备注",
      "厂家（待填）", "完整料号（待填）", "询价数量", "单价 元（待填）", "小计 元",
      "交期（待填）", "规格书 / 实物照（待填）"]
W1 = [6, 17, 27, 40, 18, 14, 14, 42, 13, 21, 12, 12, 10, 11, 17]

R1 = [
    ["1", "射频电感", "Bourns 78FR47K-RC",
     "470 nH（0.47 µH）；±10%；Q≥40 @25 MHz；SRF≥270 MHz；DCR≤0.11 Ω",
     "原生轴向插件", "2 只", "5 只",
     "料号须为 78FR47K-RC。无 -RC 后缀者规格不同（650 mA / 100 mΩ / SRF 330 MHz），不接受。到货逐只测量电感值。",
     None, None, 5, None, None, None, None],

    ["2", "微调电容", "Vishay BFC280905003 或 BFC280905217",
     "2–18 pF；300 V；tanδ≤25×10⁻⁴ @100 MHz；Cmax 时 fres≥360 MHz",
     "插件径向；S 左定片、R 右动片；孔距 5.08 mm", "3 只", "3 只（二选一）",
     "两型号电气等效，217 无防助焊剂罩，须用低残留助焊剂并焊后清洁。旋转寿命 10 次全行程。",
     None, None, 3, None, None, None, None],

    ["3", "射频电容 COUT", "插件 C0G/NP0（未指定厂家）",
     "11 pF；≥50 V；±2% 或更紧；介质须为 C0G/NP0",
     "插件双引脚", "1 只", "5 只",
     "与第 5 项云母 11 pF 二选一。",
     None, None, 5, None, None, None, None],

    ["4", "射频电容 CK", "插件 C0G/NP0（未指定厂家）",
     "2.4 pF；≥50 V；±0.1 pF 优先",
     "插件双引脚", "1 只", "10 只",
     "如仅能提供 ±0.25 pF，请单独列出该档。",
     None, None, 10, None, None, None, None],

    ["5", "射频电容 CFIX1", "插件 C0G/NP0（未指定厂家）",
     "27 pF；≥50 V；±2% 或更紧",
     "插件双引脚", "1 只", "10 只",
     "需提供介质与精度说明；容差如需放宽请注明。",
     None, None, 10, None, None, None, None],

    ["6", "射频电感", "Coilcraft 1812CS-392XJRC（贴片参考）",
     "3.9 µH；±5% 或更紧；须提供 30–32 MHz 的 L/Q 曲线、SRF、DCR",
     "需原生插件型号（1812CS 为贴片，不接受贴片加引脚）", "1 只", "2 只",
     "请报等效的插件型号，不要直接按 1812CS 供货。",
     None, None, 2, None, None, None, None],

    ["7", "射频电感", "Coilcraft 1812CS-332XJRC（贴片参考）",
     "3.3 µH；±5% 或更紧；须提供 31 MHz 附近 L/Q、SRF、DCR",
     "需原生插件型号", "0–1 只", "2 只",
     "可与第 6 项同时报，不必同时供货。",
     None, None, 2, None, None, None, None],

    ["8", "射频电感", "Coilcraft 1812CS-472XJRC（贴片参考）",
     "4.7 µH；±5% 或更紧；须提供 31 MHz 附近 L/Q、SRF、DCR",
     "需原生插件型号", "0（可选）", "可另报 2 只",
     "可选项，仅报价。",
     None, None, 2, None, None, None, None],

    ["9", "云母电容", "CMDB2A11PJ",
     "11 pF；100 V",
     "插件；脚距 6 mm", "1 只", "5 只",
     "请注明容差与完整厂家料号。",
     None, None, 5, None, None, None, None],

    ["10", "陶瓷微调电容", "CCW12",
     "3.5–20 pF",
     "插件", "3 只", "10 只",
     "请提供厂家、准确型号、实物脚位与 Q/损耗。",
     None, None, 10, None, None, None, None],

    ["11", "陶瓷微调电容", "EW GKG20015",
     "5–20 pF；100 V",
     "插件", "0（备选）", "可另报",
     "备选，仅报价。",
     None, None, 0, None, None, None, None],

    ["12", "精密电阻", "按参数供货（未指定厂家）",
     "10 Ω；±0.1%；≥0.25 W；金属膜非绕线",
     "插件", "2 只", "10 只",
     "不接受 1%（J）档替代。",
     None, None, 10, None, None, None, None],
]

ws1, hdr1 = shell(
    wb, "询价单",
    "器件询价单",
    "请按项填写厂家、完整料号、单价、交期，并附规格书或实物照片；缺项可空。数量为建议询价量，可按包装规格调整。",
    H1, W1, first=True,
)
last1 = rows_out(ws1, hdr1 + 1, R1, height=60, center=(1, 6, 7, 11, 12, 13, 14))

# 小计 + 待填列高亮
for i in range(len(R1)):
    r = hdr1 + 1 + i
    c = ws1.cell(row=r, column=13)
    c.value = f'=IFERROR(IF(AND(ISNUMBER(K{r}),ISNUMBER(L{r})),K{r}*L{r},""),"")'
    c.number_format = "0.00"
    c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right")
    c.font = Font(name=FONT, size=10, bold=True, color=INK)
    c.border = BORDER
    c.fill = PatternFill("solid", fgColor=STRIPE if i % 2 == 1 else "FFFFFF")
    for col in (11, 12, 14, 15):
        ws1.cell(row=r, column=col).fill = PatternFill("solid", fgColor=FILLIN)
        ws1.cell(row=r, column=col).font = Font(name=FONT, size=10, bold=True, color=BROWN)

dv_qty = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                        allow_blank=True, showErrorMessage=True,
                        errorTitle="请填数字", error="此列只填数字，例如 5。")
dv_price = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                          allow_blank=True, showErrorMessage=True,
                          errorTitle="请填数字", error="此列只填单价数字，例如 1.82。")
ws1.add_data_validation(dv_qty)
ws1.add_data_validation(dv_price)
dv_qty.add(f"K{hdr1 + 1}:K{last1}")
dv_price.add(f"L{hdr1 + 1}:L{last1}")

# 汇总
tot = last1 + 2
ws1.cell(row=tot, column=2, value="报价汇总").font = Font(name=FONT, size=11, bold=True, color=INK)
ws1.merge_cells(start_row=tot, start_column=2, end_row=tot, end_column=4)

summary = [
    ("已填写项数", f'=COUNT(L{hdr1 + 1}:L{last1})', "0"),
    ("金额合计 元", f'=SUM(M{hdr1 + 1}:M{last1})', "0.00"),
    ("未填单价项数", f'=COUNTIF(L{hdr1 + 1}:L{last1},"")', "0"),
]
for k, (label, formula, fmt) in enumerate(summary):
    r = tot + 1 + k
    lc = ws1.cell(row=r, column=2, value=label)
    lc.font = Font(name=FONT, size=10, color=INK)
    lc.alignment = Alignment(horizontal="left", vertical="center")
    lc.fill = PatternFill("solid", fgColor=GREY)
    lc.border = BORDER
    ws1.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)

    vc = ws1.cell(row=r, column=5, value=formula)
    vc.number_format = fmt
    vc.font = Font(name=FONT, size=11, bold=True, color=INK)
    vc.alignment = Alignment(horizontal="center", vertical="center")
    vc.fill = PatternFill("solid", fgColor=GREEN)
    vc.border = BORDER
    ws1.row_dimensions[r].height = 22

# ───────────────────── 通用要求 ─────────────────────
H2 = ["项目", "要求"]
W2 = [30, 96]
R2 = [
    ["报价内容", "每项请给出厂家、完整料号、单价、交期、最小包装量与包装形式。"],
    ["随附资料", "规格书（含 Q、SRF、DCR、容差、耐压、介质）与实物照片；无资料项可注明。"],
    ["电感封装", "须为原生插件件。不接受贴片件加焊引脚或飞线改制。"],
    ["电感参数", "需提供 31 MHz 附近的 L/Q、SRF 与 DCR；仅有 25 MHz 或 50 MHz 数据时请注明测试频率。"],
    ["电容介质", "射频位要求 C0G/NP0，请注明介质与容差；不得以 X7R/Y5V 替代。"],
    ["容差标注", "实际可供容差与报价一并注明；若劣于本单要求，请单独列出该档，不要默认替代。"],
    ["替代型号", "可提替代型号，但须先提供参数（Q/SRF/DCR/容差/介质），确认后再换货。"],
    ["数量", "数量为建议询价量，可按最小包装调整，请同时给出整包价。"],
]
ws2, hdr2 = shell(wb, "通用要求", "通用要求", "以下为全部器件的共同要求，适用于本单每一项。", H2, W2)
rows_out(ws2, hdr2 + 1, R2, height=40)

# ──────────────────── 转发文字（可复制） ────────────────────
ws3 = wb.create_sheet("转发文字")
ws3.sheet_view.showGridLines = False
ws3.column_dimensions["A"].width = 4
ws3.column_dimensions["B"].width = 108

ws3["B2"] = "可直接复制的询价文字"
ws3["B2"].font = Font(name=FONT, size=15, bold=True, color=INK)
ws3.row_dimensions[2].height = 26

ws3["B4"] = "复制下方 B6 单元格内容即可（已换行）。"
ws3["B4"].font = Font(name=FONT, size=10, color=SOFT)

FORWARD = """以下器件请报价，注明厂家、完整料号、单价、交期与最小包装，并附规格书。电感须为原生插件件，不接受贴片加引脚。

1. Bourns 78FR47K-RC，470nH ±10%，轴向插件，Q≥40@25MHz、SRF≥270MHz、DCR≤0.11Ω，5只。
2. Vishay BFC280905003 或 BFC280905217，2～18pF、300V 插件微调电容，3只，二选一。
3. 插件C0G/NP0：11pF、≥50V、±2%或更紧，5只；2.4pF、≥50V、±0.1pF优先，10只；27pF、≥50V、±2%或更紧，10只。
4. 3.9µH、3.3µH 插件高Q射频电感，各2只，需提供31MHz附近L/Q、SRF、DCR；4.7µH 可另报2只。
5. 11pF、100V 插件云母电容（CMDB2A11PJ），5只，请注明容差。
6. CCW12 插件微调 3.5～20pF，10只；EW GKG20015 5～20pF 可另报。
7. 10Ω、±0.1%、≥0.25W 插件非绕线精密电阻，10只。

替代型号请先发参数再确认。缺项可空。"""

cell = ws3["B6"]
cell.value = FORWARD
cell.font = Font(name=FONT, size=10, color=INK)
cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
cell.fill = PatternFill("solid", fgColor="F7F9FB")
cell.border = BORDER
ws3.row_dimensions[6].height = 268

ws3["B8"] = "附：数量为建议询价量，可按最小包装调整。"
ws3["B8"].font = Font(name=FONT, size=9, color=SOFT)
ws3["B8"].alignment = Alignment(wrap_text=True, vertical="top")
ws3.row_dimensions[8].height = 22

for ws in wb.worksheets:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True

wb.save(OUT)
print("saved:", OUT)
print("sheets:", wb.sheetnames)
