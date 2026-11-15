"""Readable BOM/wiring manual, vector PDF export, and combined drawing book."""
from build_drawings import *
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4,landscape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
import fitz

INTERCONNECT=[
 {'线号':'X01','节点':'port','端A':'LC H16 (PORT)','端B':'RF F03 (PORT_IN)','工艺':'最短信号线；接入前拆RMEAS1/CEXT1/探头，重新加载核对'},
 {'线号':'X02','节点':'0','端A':'LC I16 (GPORT)','端B':'RF E03 (GPORT)','工艺':'贴近X01的短宽地回路；不要经电源长线绕回'},
 {'线号':'X03','节点':'out','端A':'RF J43 (BB_OUT)','端B':'BB L04 (DET_IN)','工艺':'与X04相邻，远离RF输入和线圈'},
 {'线号':'X04','节点':'0','端A':'RF K43 (GOUT)','端B':'BB M04 (GIN)','工艺':'基带信号地回路；不接ref'},
 {'线号':'X05','节点':'vcc','端A':'BB D02 (RF_9V)','端B':'RF B02 (VCC)','工艺':'9 V供电，配合两端就地去耦'},
 {'线号':'X06','节点':'0','端A':'BB E02 (RF_GND)','端B':'RF C02 (GND)','工艺':'供电回流，与X05相邻；所有0是同一地'},
 {'线号':'X07','节点':'input / 0','端A':'50 Ω信号源同轴芯 / 屏蔽','端B':'LC H03 / I03 (JRF1)','工艺':'入口不另并50 Ω；按源开路幅度口径校准'},
 {'线号':'X08','节点':'vcc / 0','端A':'外部9 V电源+ / -','端B':'BB A02 / B02 (JPOWER1)','工艺':'检查极性；本轮不焊整机、不上电'},
 {'线号':'X09','节点':'final / 0','端A':'BB H24 / I24 (JOUT1)','端B':'基带测量输入 / 地','工艺':'反馈在ROUT1前；输出总测试负载1 MΩ∥100 pF，计入仪器'}]
table('板间连接表.csv',INTERCONNECT)

GUIDE='''# S05-11 A+G22 施工图 r1

绘图始于2026-10-30，完成于2026-10-31。交付范围为图纸、接线表和核对证据。信号参数未修改，未运行 ngspice，未焊接，未提交或推送 Git。当前接线版本已核对；机械落点和测量资格仍受下列明确条件约束。

## 从哪一份开始

- 完整接收机：`pdf/01_receiver.pdf`、`svg/01_receiver.svg`、`kicad/01_receiver.kicad_sch`。
- 首块 LC 小板：`pdf/02_lc_module.pdf`，再看 `03_LC_top` / `04_LC_bottom` 的孔位与跳线。
- 后续 RF / 基带板：`05_RF_top` / `06_RF_bottom`、`07_BB_top` / `08_BB_bottom`。本轮不制作整机。
- 模型与测试边界：`09_model_and_test_boundaries`，必须与主图一起使用。
- `S05_A_G22_完整图册.pdf` 汇集图纸、说明、BOM及全部接线表。SVG/PDF均为矢量；洞洞板图是放大示意，不能当1:1钻孔模板。
- `kicad/` 是真正的 KiCad 7+ 可编辑原理图，含内嵌符号、电气引脚、导线和节点标签。已用 KiCad 7.0.11 CLI 导出网表核对，不是图片包装。未生成 Multisim 原生工程，也没有声称其存在。

## 1. 版本锁定与历史排除

最终连接依据是 `lc_parts_20261030/netlists/T_sq50_six_source.cir`，另用 `T_sq10_six_source.cir` 交叉核对。对应结果 JSON 登记的 source、wrapper、日志及原始 raw SHA-256 均核验；两个输入占空比的实际器件连接和值一致。

`T_sq50_six.cir` 本身只是控制包装，source 指向另一个文件，不能只读包装就作图。`filters/NOM_132.cir` 是有效器件 LC 模型；`netlists/NOM_132.cir` 是带RF测试负载的 AC 夹具，不是完整接收机。

根目录的 `S05_A2_G22_candidate.cir` 仍是 S05-06 的470 nH历史候选，本图没有拿它的LC值作为实物采购参数。未采用R2、B方案、CSEL开放匹配版本、5 V无效初值试验、`attempt01_aborted`、并发冲突目录或失败角点。S05-05～10及勘误均已查阅；测量操作以S05-10及其仪器补充为准。

冻结方案：9 V；CSEL=15 pF、CK=2.4 pF、COUT=11 pF；LSEL1/2=460 nH；原Q1/Q2及QBUF；BAT85模型检波；OPA197，RFB=210 kΩ、RG=10 kΩ，G22；RVT/RVB=20 kΩ/10 kΩ产生约3 V参考；ROUT=100 Ω。

## 2. 网表到实物的转换规则

原网表全59个顶层元件已列在 `tables/原始网表全部元件.csv`，包含数值和源文件行号。图纸为满足KiCad位号规则，对无尾号的名称加1，例如CSEL→CSEL1、RFB→RFB1、QBUF→QBUF1；已有Q1、CIN1等不变。XOPA→U1，XDET→DDET1。BOM同时列出原名称。

- `RLOSS1/2 + LSEL1/2 + CSELF1/2` 是两只真实线圈的损耗、自电容模型。实物各装一只132-17L，不另焊1.21911483406 Ω或0.476348275737 pF。
- `RCT1/2 + CTUNE1/2` 是有损调谐支路。原CTUNE为41.609801788/47.1490753446 pF，已包含各1 pF的布局预算。固定30/39 pF后，微调模型起点为10.609801788/7.1490753446 pF。实物不加一个“布局1 pF电容”。这些小数是模型分解，不能靠旋钮角度设定。
- S05-08文字中11.61/8.15 pF的微调口径与代码中“ct+board”的定义不一致；本图依有效网表和`ac_cases.json`明确减去布局预算，采用S05-10约10.61/7.15 pF起点。没有修改历史文件或仿真值。
- `RCONNECT=0.1 Ω` 是连接等效，主图保留独立位号和rf/an两个节点，用短连线实现。它不作为采购电阻。模型图保留原说明；这属于实现映射，不声称实物短线恰好为0.1 Ω。
- `RLOAD=1e15 Ω` 不安装。`VMOD/BSIG/RSOURCE/VSUP` 是激励/源阻抗/电源环境。`.ic/.nodeset` 不是实物预充电电路。
- `RBBLOAD=1 MΩ、CLOAD=100 pF` 是输出总测试负载，单列模型图，不永久叠加到未知示波器输入上。RF AC夹具的RTEST/CTEST不属于整链，不装到本图中。
- CDQ1、CDQ2、CDBUF1、CDU1各100 nF及CPWR1=10 μF，是S05-10已列出的实物电源配套。它们已单独分类；没有声称它们在原理想电源仿真中出现。信号通道、偏置和反馈值未改。

物理原理图是对模型的可施工映射；线圈损耗、布局寄生和真实器件特性不可能由“逐节点一致”证明。核对通过仅表示没有发现电气连接、参数抄写、引脚映射或跳线端点错误。

## 3. 实际引脚、极性与机械条件

|器件|本图采用的实际引脚|机械/资格状态|
|---|---|---|
|Q1/Q2/QBUF1|onsemi 2N3904 TO-92：1=E、2=B、3=C。SPICE顺序是C/B/E，不能当实物1/2/3。|实购厂牌/后缀/脚型待确认；其他厂牌先查对应手册。图示2.54 mm落点需短引脚成形核实。|
|U1|TI OPA197ID/IDR，D/SOIC-8：2=负输入、3=正输入、4=GND、6=输出bbo、7=9 V；1/5/8不连接。|采用SOIC→DIP逐脚直通转接；转接板料号、同号脚映射和本地去耦位置待逐脚核实。不能套用SOT-23-5脚号。|
|DDET1|Nexperia BAT85，SOD68/DO-34：物理1=K阴极/色环→det；物理2=A阳极→an。|宏模型XDET第1参数为A、第2参数为K，恰好与实物编号相反。实购批次待确认。BAT85S仍未资格化。|
|CT1/CT2|Vishay BFC280905003：厂家标S定片、R动片。本图自定义1=S→tank、2=R→GND。|2–18 pF，脚距5.08 mm，端子孔图约Ø1.2 mm。到货按厂家孔位图确认视角和S/R；不是厂家数字脚号。调节寿命按厂家最多10个180°循环理解。|
|LSEL1/2|Coilcraft132-17L：本图自定义1=热端、2=地端；器件无二极管式极性。|两引脚方向间距约7.37×3.96 mm，非整2.54网格。图示是引出落点，须核实短引线成形或增开孔。不要强拉线圈来凑孔。|
|CVREF1 / CPWR1|1为正，2为负；CVREF1正端ref，CPWR1正端vcc，负端均GND。|10 μF，建议≥16 V。实购物料脚距待核实。|
|其他R/C|按图纸1/2端对应节点，无电气极性。|电阻1%、≥1/8 W，小型金属膜/薄膜；RF电容C0G/NP0、≥50 V。具体完整订货号与外形未锁定。|

RF小电容包括CSEL1、CK1、COUT1、CFIX1/2、CIN1/2、CBUF1、COBUF1、CEB1/2、CDET1、CFILT1。前端15/11/30/39 pF取≤±2%，CK2.4 pF取≤±0.1 pF。其余RF电容建议≤±5%；这些是备料规格，不是已经购买。CCOUP1=100 nF无极性，可用合适介质、≥16 V器件；去耦100 nF按实际封装就近安装。

厂家依据（访问核对日期2026-10-30）：[onsemi 2N3904](https://www.onsemi.com/pdf/datasheet/2n3904-d.pdf)，[TI OPA197](https://www.ti.com/lit/ds/symlink/opa197.pdf)，[Nexperia BAT85](https://assets.nexperia.com/documents/data-sheet/BAT85.pdf)，[Vishay微调](https://www.vishay.com/docs/28529/bfc280905.pdf)，[Coilcraft132-17](https://www.coilcraft.com/en-us/products/rf/air-core-inductors/maxi-spring/132/132-17/)。本地`sources`保存已取得的PDF及原始整链网表；403下载失败的2N3904/BAT85以已读取的官方网页PDF为出处，不假称已下载存档。

## 4. 洞洞板读图和布线

三块板均为独立孔。坐标格式H16代表从元件面看第H行、第16列；焊接面图已左右镜像，列号也反序，不能再次自行镜像。图中元件体的01、02等是右侧索引，不是芯片脚号；实际脚号印在落点旁，并逐条列在孔位表。

除明确标出的地铜带外，所有跳线只在两端焊点接通。跨线、经过其他孔的位置不相连，需完整绝缘；不要沿整段用焊锡桥接。黑色表示地，红色表示9 V，其余颜色区分信号节点。RF板背面D/M两行以及第2/15/27/44列的D至M段为约1.2 mm窄地铜带，覆盖孔全部是GND；已核对这些行列没有信号引脚。其他跨带线必须绝缘。其余板没有默认整行连通。线号对应`逐根跳线表.csv`，其中工艺列区分地铜带段和绝缘线。有些孔共享同一节点的两条引线，按实物孔径调整焊接工艺；若必须换孔，先更新逐脚表并重新核对，不能凭邻孔默认连通。

地回路应紧贴相应信号路径，用短、低阻抗连接；可在确认不接触信号焊盘的位置加地铜带。不要在两线圈下方随意铺大块地铜或绕一圈地线；地铜、手、金属工具和探头线的位置都会改变LC。地与ref不得混接。CDQ1/CDQ2/CDBUF1靠近各级，CDU1靠近SOIC的7/4脚；DIP落点上的电容不能代替芯片脚边旁路。

LC初始两线圈轴向近似正交，留调整空间；图示间距不保证k=0，也不采用“必须架高5 mm”或“带宽合适就证明互感消失”的旧表述。LC入口与输出分开走，CK及tank引线保持短小。LC与RF板相邻放置，port不经长杜邦线/同轴高阻段。RF输入远离Q2集电极及输出。实际寄生、增益、稳定性和加载响应仍须后续实测。

首块LC板的RMEAS1和CEXT1是可拆测试件；整链阶段拆掉它们及探头/缓冲，同时移除不需要的长支线。RPORT1永久保留。拆装后必须重新核对加载，不能认为独立板的调谐值原封不动适用。

## 5. LC测量接线的明确边界

测点是COUT之后、CIN1/Q1之前的`port`。QBUF在Q2之后，不能把LC出口写成射随输入。独立板用953 Ω、原RPORT1 MΩ、实际测量接口输入电阻构成并联负载，电容预算是`CEXT + 探头尖端电容 + 连接寄生 ≈ 14 pF`。

例如探头3 pF、连接1 pF，CEXT算术起点10 pF；若10 pF探头和1 pF连接，算术起点3 pF。两者只是预算示例，不是采购定值或探头资格已通过。当前探头型号与尖端R/C未知，CEXT明确标TBD。若探头加连接已经超过14 pF，无法靠追加并联电容补救。

禁止直接把普通10 pF探头接tank并验收；1–3 pF探头也不是对tank无扰动。S05-09的10 pF tank加载偏频约1.49 MHz是历史模型结果。S05-09关于rf的“6.81 dB固定衰减”和“抑制变好”表述已被S05-10勘误纠正，本图不使用它们作补偿。

信号源先确认28–34 MHz正弦覆盖与实际50 Ω源阻抗。高阻/50 Ω菜单通常改变幅度口径，不能据此认定源内阻改变。先在校准端接下校准，再移走端接接LC；LC入口不额外并50 Ω，tank/port也不直连DS2102E的50 Ω输入。普通10×探头一般用1 MΩ端接，最终按实际探头手册。DS2102E关闭20 MHz限带。现有发生器型号仍待核实。

独立port的历史参考为边界中点约31.030 MHz、连续-3 dB带宽约1.885 MHz，29/33 MHz相对抑制约13.39/11.84 dB；不同于rf参考1.920 MHz。工程窗口1.85–1.95 MHz保留，但总C误差±1 pF足以造成约45–52 kHz带宽变化；无误差预算不能写通过。这是电压传递，不是S21、S11、线圈Q31或互感测量。

## 6. 测试点与后续断电核对

|测点|对应节点/孔位|用途与限制|
|---|---|---|
|RF_IN|input，LC H03|源幅度口径校准；不是已匹配50 Ω输入。|
|TP_PORT|port，LC H16|独立LC唯一受控负载测点；禁止开路负载套用原曲线。|
|tank1/tank2|元件自身短焊点|不装测试柱、不接普通探头验收。|
|TP_C1/TP_C2|c1/c2，RF F11/F23|射频级诊断点；直接接探头会增加负载，须单独评估。|
|TP_RF|rf，RF J33|QBUF经COBUF隔直后的RF；保留RRF，不按旧简单RC公式修正。|
|TP_DET / TP_ENV|det / out，RF J37 / J43|包络检波、低通后；探头负载仍需记录。|
|TP_REF|ref，BB F06|约3 V参考；与地不相同。|
|TP_BBIN / TP_BBO|bbin / bbo，BB H12 / H18|OPA正输入和隔离前输出；反馈取bbo。|
|TP_FINAL|final，BB H24|ROUT后基带输出；含直流，不是逻辑电平。|
|9 V / GND|BB A02/B02|电源正负；无源LC自身不接电源。|

后续焊接时：先按逐根线号用通断档核对铜线端点，再核对电阻、半导体和极性；不能要求隔着电容、电阻或PN结的同功能模块都蜂鸣。重点检查vcc与0未被直接桥接、ref与0未短接、OPA 1/5/8未接、反馈在100 Ω之前、DDET色环朝det。LC线圈在直流下低阻到地是正常路径，不能把tank对地低阻误判为焊锡短路。RCONNECT短连线使实物rf/an近似同节点，是本图明确允许的映射。

## 7. 核对证据与放行范围

**KiCad 8.0.9 原生 ERC：三张图均为 0 Error / 0 Warning。** 原始报告在`qa/kicad_native_20261031/erc_*.rpt`，未删改。

ERC 显示零警告的前提是 KiCad 能找到昵称`S05`的符号库：本目录提供`kicad/S05.kicad_sym`与`kicad/sym-lib-table`。**若未在你自己的 KiCad 中注册该库，ERC 会重新报出 87 条`lib_symbol_issues`**（每个已放置符号一条）。这不影响图纸本身——符号内嵌，图纸仍可正常打开、导出网表和出图。

`qa/verification.json`记录逐脚/逐值比较、三块洞洞板落点与跳线图连通性、6条板间线与25个全局网络划分、历史文件哈希和有效源/raw哈希；本文件与最终图在同一轮生成后重跑，为最新结果。

`qa/geometry_check.json`是早期补位证据：当时本机无 KiCad，只能直接解析`.kicad_sch`几何重建连通性，并含一条自检——故意从某网络删除一个真实引脚，必须被抓到。**现已由 KiCad 原生导出网表取代**，该文件保留作历史。

**机械项未全部闭合**：`qa/mechanical_open_items.json`登记了 132-17L 落点与手册相差 5.20 mm（`BLOCKED_PENDING_PHYSICAL_PART`）、Vishay 孔径资料矛盾，以及 LC 测量接口未定。**目前不能判定可以开焊。**

图纸与表格的连接核对不等于器件封装资格或RF布局已实测。完整接收机的性能结论仍受S05-06～S05-10已登记缺口约束；本轮修订见`S05-13 施工图最小收尾`（路径：simulation/v4_hardware/stage5_receiver/S05_13_施工图最小收尾.md）。

核对期间，工作区中的S05-10仪器补充由其他工作追加了“收尾记录”。其原有正文前缀与开始时哈希一致，追加内容没有改网表、参数或测量条件，已单列在`qa/reviewed_external_changes.json`，没有回滚或覆盖该更新。本轮绘图只新增交付目录和脚本目录。

仍待核实：实际2N3904厂牌/后缀、BAT85采购型号（BAT85S未通过）、OPA197转接板、所有未锁定无源件外形、微调R/S识别和孔径、线圈落孔方式、探头与信号源参数。以上未定部分没有伪装成已确认封装。可先按本图核对备料与独立LC制作条件；完整接收机仍暂不焊。

未关闭的历史性能边界：冷启动、20 mV过载、实际天线/50 Ω匹配、无线距离、温度/批次与全占空比矩阵。没有用本轮绘图重新宣告任何硬件性能通过。
'''
(OUT/'README_施工说明.md').write_text(GUIDE,encoding='utf-8')

def loadcsv(name):
    with (OUT/'tables'/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def grouped_bom():
    groups=defaultdict(list)
    for p in parts.values():
        if p['kind']=='W':continue
        key=(p['kind'],p['value'],p['group']);groups[key].append(nref(p['ref']))
    rows=[]
    for (kind,val,group),refs in groups.items():
        spec='见逐器件表；封装待核实'
        if kind=='R':spec='1%，≥1/8 W，小型金属膜/薄膜'
        elif kind=='C':spec='RF用C0G/NP0≥50 V；100n耦合/去耦≥16 V，详说明'
        elif kind=='P':spec='10u ≥16 V，核对正负极与脚距'
        rows.append({'类型':group,'数值/型号':val,'数量':len(refs),'图纸位号':', '.join(refs),'规格/状态':spec})
    rows += [dict(类型='可拆LC夹具',**{'数值/型号':'953 Ω','数量':1,'图纸位号':'RMEAS1','规格/状态':'1%；仅独立板测试，整链拆除'}),dict(类型='可拆LC夹具',**{'数值/型号':'CEXT TBD','数量':1,'图纸位号':'CEXT1','规格/状态':'C0G，按总14pF预算选配；未定值，不盲购'}),dict(类型='外部测试边界',**{'数值/型号':'1 MΩ∥100 pF','数量':'1组','图纸位号':'RBBLOAD1 / CLOAD1','规格/状态':'输出总负载，可由仪器及补偿构成，不默认额外焊上'}),dict(类型='结构附件',**{'数值/型号':'SOIC8→DIP8转接、洞洞板、短同轴、绝缘线/地铜带','数量':'1套','图纸位号':'U1转接及结构','规格/状态':'转接逐脚通断与机械尺寸待核实；不含未资格化ADA4817缓冲器'})]
    table('BOM_汇总.csv',rows)
grouped_bom()

pdfmetrics.registerFont(TTFont('S05CJK','C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
def fixfont(n):
    if hasattr(n,'fontName'):n.fontName='S05CJK'
    for v in getattr(n,'contents',[]):fixfont(v)

for f in sorted((OUT/'svg').glob('*.svg')):
    drawing=svg2rlg(str(f));fixfont(drawing);renderPDF.drawToFile(drawing,str(OUT/'pdf'/(f.stem+'.pdf')))
    doc=fitz.open(OUT/'pdf'/(f.stem+'.pdf'));doc[0].get_pixmap(matrix=fitz.Matrix(.85,.85)).save(OUT/'qa'/(f.stem+'_preview.png'))

styles={
 'normal':ParagraphStyle('normal',fontName='S05CJK',fontSize=9.3,leading=15,spaceAfter=7,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='S05CJK',fontSize=7.3,leading=10,wordWrap='CJK'),
 'h1':ParagraphStyle('h1',fontName='S05CJK',fontSize=19,leading=27,spaceAfter=14,keepWithNext=True),
 'h2':ParagraphStyle('h2',fontName='S05CJK',fontSize=12,leading=19,spaceBefore=10,spaceAfter=7,keepWithNext=True),
}
def p(t,style='normal'):
    t=html.escape(str(t));t=t.replace('`','')
    return Paragraph(t,styles[style])
def tab(rows,widths):
    cells=[[p(x,'small') for x in row] for row in rows]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2edf2')),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#aab7bd')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    return t

story=[];lines=GUIDE.splitlines();i=0
while i<len(lines):
    line=lines[i].strip()
    if not line:i+=1;continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            if not set(lines[i].replace('|','').replace('-','').replace(' ',''))==set():rows.append([v.strip() for v in lines[i].strip('|').split('|')])
            i+=1
        if rows:story.append(tab(rows,[500/len(rows[0])]*len(rows[0])))
        continue
    if line.startswith('# '):story.append(p(line[2:],'h1'))
    elif line.startswith('## '):story.append(p(line[3:],'h2'))
    else:story.append(p(line))
    i+=1

def footer(c,d):
    c.setFont('S05CJK',8);c.setFillColor(colors.HexColor('#667b85'));c.drawString(42,24,'S05-11 | 接线图纸，非硬件验收 | 2026-10-31');c.drawRightString(d.pagesize[0]-42,24,str(d.page))
manual=OUT/'pdf/10_施工说明.pdf'
SimpleDocTemplate(str(manual),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=36,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)

ts=[]
for filename,cols,widths in [
 ('BOM_汇总.csv',['类型','数值/型号','数量','图纸位号','规格/状态'],[70,135,35,230,270]),
 ('BOM_逐器件.csv',['图纸位号','原网表位号','数值','引脚与节点','封装与资格','说明'],[65,70,75,140,180,210]),
 ('逐节点接线表.csv',['节点','全部物理端点','注意'],[65,535,140]),
 ('板间连接表.csv',['线号','节点','端A','端B','工艺'],[45,65,150,150,330]),
 ('逐脚洞洞板孔位表.csv',['板','图纸位号','实际脚','孔坐标','节点'],[60,220,100,120,240]),
 ('逐根跳线表.csv',['线号','板','节点','端A','端B','直线跨度mm','工艺'],[85,40,70,60,60,70,355]),
 ('原始网表全部元件.csv',['位号','数值','节点顺序','源文件行','处理'],[85,210,130,65,250])]:
    if ts:ts.append(PageBreak())
    ts.append(p(filename.removesuffix('.csv'),'h1'));rows=loadcsv(filename)
    ts.append(tab([cols]+[[r[k] for k in cols] for r in rows],widths))
SimpleDocTemplate(str(OUT/'pdf/11_BOM与接线表.pdf'),pagesize=landscape(A4),rightMargin=40,leftMargin=40,topMargin=35,bottomMargin=40).build(ts,onFirstPage=footer,onLaterPages=footer)

book=fitz.open()
for f in sorted((OUT/'pdf').glob('*.pdf')):
    d=fitz.open(f);book.insert_pdf(d)
book.save(OUT/'S05_A_G22_完整图册.pdf',garbage=4,deflate=True)
for filename in ['10_施工说明','11_BOM与接线表']:
    d=fitz.open(OUT/'pdf'/(filename+'.pdf'))
    for i in range(len(d)):
        d[i].get_pixmap(matrix=fitz.Matrix(1.1,1.1)).save(OUT/'qa'/f'{filename}_{i+1:02}.png')
print('PDF book pages',len(book))
