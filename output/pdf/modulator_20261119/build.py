from pathlib import Path
import math
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
O=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('CN',r'C:\Windows\Fonts\msyh.ttc',subfontIndex=0))
W,H=1600,1120
PDF=O/'基极调制级_焊接原理图与接线表_R1.pdf'
c=canvas.Canvas(str(PDF),pagesize=(W,H));c.setTitle('基极调制级：原理图、端点接线、上电测试')
ink='#172d41';blue='#146fa5';red='#c43c36';purple='#8240a5'
def line(x,y,X,Y,col=ink):
 c.setStrokeColor(HexColor(col));c.setLineWidth(2);c.line(x,H-y,X,H-Y)
def text(x,y,s,size=20,col=ink):
 c.setFont('CN',size);c.setFillColor(HexColor(col));c.drawString(x,H-y,s)
def box(x,y,w,h,fill='#ffffff'):
 c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(ink if w<=60 else '#dce5ec'));c.rect(x,H-y-h,w,h,fill=1,stroke=1)
def dot(x,y):
 c.setFillColor(HexColor(ink));c.circle(x,H-y,3.8,fill=1,stroke=0)
def ground(x,y):
 line(x,y,x,y+10)
 for a,b in [(12,0),(8,6),(3,12)]:line(x-a,y+10+b,x+a,y+10+b)
def rv(x,y,Y,label=''):
 m=(y+Y)/2;line(x,y,x,m-25);box(x-10,m-25,20,50);line(x,m+25,x,Y)
 if label:text(x+20,m+6,label,19)
def rh(x,X,y,label):
 m=(x+X)/2;line(x,y,m-28,y);box(m-28,y-10,56,20);line(m+28,y,X,y);text(m-65,y-25,label,19)
def cv(x,y,Y,label=''):
 m=(y+Y)/2;line(x,y,x,m-7);line(x-17,m-7,x+17,m-7);line(x-17,m+7,x+17,m+7);line(x,m+7,x,Y)
 if label:text(x+24,m+5,label,19)
def ch(x,X,y,label):
 m=(x+X)/2;line(x,y,m-7,y);line(m-7,y-17,m-7,y+17);line(m+7,y-17,m+7,y+17);line(m+7,y,X,y)
 text(m-pdfmetrics.stringWidth(label,'CN',19)/2,y-26,label,19)
def header(n,title,sub):
 box(0,0,W,133,'#112e43');text(50,61,title,34,'#ffffff');text(50,107,sub,19,'#dbe8ee')
 text(50,1090,'31 MHz AM | 调制板装配版 R1 | 2026-11-19 | 现有仿真拓扑转绘，实物接口与幅度待联调',16,'#607486');text(1460,1090,f'{n} / 3',17)
def note(y,s):text(55,y,s,20)
header(1,'新增模块：单管基极调制级','接现有载波 OUT 与基带 V1；输出 TP3 供后续驱动级使用。本页不是天线功率输出电路。')
text(65,200,'RF_IN：接载波板 OUT',22,blue)
line(90,225,90,390,blue);rh(90,350,390,'RMRF 2.2 kΩ');dot(350,390)
rv(350,390,630,'RMRG 10 Ω');ground(350,630)
text(245,350,'RF_TAP',19,blue);ch(350,620,390,'CMRF 100 pF');line(620,390,740,390,blue);line(740,390,740,510,blue)
text(65,726,'BB_IN：接基带 V1 滑端',22,purple)
line(90,755,90,810,purple);rh(90,350,810,'RPRE 10 kΩ');dot(350,810)
cv(350,810,940,'CENV 47 pF');ground(350,940)
rh(350,650,810,'RMINJ 37 kΩ');line(650,810,740,810,purple);line(740,810,740,510,purple)
text(370,855,'ENV',19,purple)
line(800,245,1510,245,red);text(800,218,'+5 V（与两块前级板共电源参考、共地）',21,red)
rv(850,245,510,'RMT 15 kΩ');rv(850,510,860,'RMB 3.3 kΩ');ground(850,860)
line(740,510,1000,510,blue);dot(740,510);dot(850,510);text(755,480,'MB',20,blue)
# QM: NPN with physical pin numbering.
line(1000,470,1000,550);line(1000,490,1070,425);line(1000,530,1070,595)
line(1058,584,1040,578);line(1058,584,1051,567)
text(1090,511,'QM 2N3904BU',22);text(945,548,'2 B',18);text(1085,423,'3 C',18);text(1085,601,'1 E',18)
rv(1070,245,425,'RMC 1 kΩ');dot(1070,425);text(985,365,'MC',18)
line(1070,595,1070,650);dot(1070,650);text(1000,646,'ME',19)
rv(1070,650,860,'RME 470 Ω');ground(1070,860)
line(1070,650,1270,650);cv(1270,650,860,'');text(1130,818,'CME 1 nF',19);ground(1270,860)
ch(1070,1450,425,'CMOUT 100 pF');dot(1450,425);text(1370,392,'TP3 / AM_OUT',21,purple)
rv(1450,425,860,'');ground(1450,860);text(1325,740,'RTP3 1 kΩ',20);text(1325,773,'保留到地',18)
text(1325,898,'输出未接天线',19,purple)
note(1008,'去耦另见第2页：100 nF + 10 µF 跨 +5 V/GND。黑点为连接；所有接地符号为同一 GND。')
note(1040,'RMINJ 原模型为37 kΩ；若按采购表用36 kΩ，须记录替代并实测校准，不视为完全等效。')
c.showPage()

header(2,'逐端点接线表与备料','按网络连接，不套用旧振荡板孔号。此版不规定万能板孔位；实物引脚以 onsemi 封装定义核对。')
rows=[
('电源','板上 +5 V 接 RMT、RMC 以及去耦电容正端；全部 GND 与两块前级板共地。'),
('载波输入','OUT → RMRF 2.2 kΩ → RF_TAP；RF_TAP → RMRG 10 Ω → GND。'),
('载波耦合','RF_TAP → CMRF 100 pF → MB（QM 基极，2脚）。'),
('基带整形','V1 → RPRE 10 kΩ → ENV；ENV → CENV 47 pF → GND。'),
('基带注入','ENV → RMINJ 37 kΩ → MB；基带支路不串隔直电容。'),
('基极偏置','+5 V → RMT 15 kΩ → MB；MB → RMB 3.3 kΩ → GND。'),
('集电极','+5 V → RMC 1 kΩ → MC（QM 集电极，3脚）。'),
('发射极','ME（QM 发射极，1脚）→ RME 470 Ω → GND；CME 1 nF 也跨 ME/GND。'),
('调制输出','MC → CMOUT 100 pF → TP3；TP3 → RTP3 1 kΩ → GND。'),
('本板去耦','100 nF 就近跨 +5 V/GND；10 µF 入口跨 +5 V/GND，电解正极接 +5 V。'),
]
for i,(a,b) in enumerate(rows):
 y=160+i*61;box(50,y,1500,61,'#f1f6f9' if i%2==0 else '#ffffff');text(68,y+38,a,20);text(255,y+38,b,19)
note(825,'备料（均各1）：2N3904BU；2.2 kΩ、10 Ω、15 kΩ、3.3 kΩ、10 kΩ、37 kΩ、470 Ω；1 kΩ×2。')
note(862,'电容：100 pF×2、47 pF×1、1 nF×1，优先 C0G/NP0；100 nF去耦×1、10 µF电解×1。')
note(910,'接入规则：拆掉载波 OUT 原来的临时2 kΩ；本板 RMRF/RMRG 支路构成新的实际负载。')
note(947,'TP3 的1 kΩ属于当前调制电路，先保留；后续驱动从TP3接入，不能把TP3当50 Ω或天线接口。')
note(984,'摆件：QM、CMRF、RMRG、RMC、CME、CMOUT相邻短线；分压器地就近回地，勿用长杜邦线串RF。')
note(1021,'板上预留 MB、MC、ME、TP3 和 GND 测点；端子标 RF_IN、BB_IN、+5 V、GND、TP3。')
c.showPage()

header(3,'首次上电与两块前级的接入顺序','先验证调制板本身，再接载波，最后接基带。每次改接线先断电；每步记录条件。')
sections=[
('1 断电检查与单板上电',[
'核对QM脚号1=E、2=B、3=C；确认供电无持续短路、去耦与电解极性正确。',
'先不接载波和基带；把本板BB_IN暂接GND。单板用5 V、10 mA限流起步。',
'用万用表测MB、ME、MC：B-E通常约0.6~0.8 V，C应高于E；贴近两端电源时先查偏置。',
'空输入时基极约0.8 V、发射极约0.1~0.3 V、集电极约4~5 V只作粗查参考，不是验收线。']),
('2 接入现有载波板，先看有没有射频',[
'断电后拆掉OUT临时2 kΩ；OUT接RF_IN，共地。BB_IN仍接GND，TP3保留1 kΩ。',
'逐板已排查正常后，载波板+调制板可先用5 V、20 mA限流；进入恒流先排查，不直接加限流。',
'示波器实体与通道倍率均10X、高阻输入、关闭20 MHz限带、短地弹簧。先在OUT复测输入。',
'再测TP3，用10 ns/div，逐步调小垂直档。记录频率/Vpp，不直接探晶体两脚。']),
('3 接入基带，观察AM包络',[
'断电，拆掉BB_IN临时接地线；基带V1接BB_IN，三板共地。三板5 V限流可先设30 mA。',
'基带先20 kHz、50%、1 Vpp。接入后在V1重新测量并调幅；不能沿用空载旋钮位置。',
'TP3先用10 µs/div观察两档包络，并用基带V1触发（两探头地都接GND）；再10 ns/div看载波。',
'若能分辨高低平台，分别记录平台RF峰峰值A高/A低；m=(A高-A低)/(A高+A低)。',
'先做1 Vpp/50%一组，确认包络随V1变化且无停振/明显削顶，再扩展幅度和占空比组合。']),
]
y=175
for title,items in sections:
 box(50,y,1500,43,'#edf4f8');text(68,y+29,title,24);y+=73
 for s in items:text(68,y,s,20);y+=35
 y+=20
box(50,940,1500,105,'#fff5e8')
text(68,972,'关键限制：本板保留原2.2 kΩ/10 Ω载波衰减器；240 mVpp输入在RF_TAP理想分压后仅约1.1 mVpp。',20)
text(68,1005,'原输入约2 Vpp的仿真不能直接套用。TP3可能很小；若不可测，先查输入/偏置/探头，再决定接口调整。',20)
text(68,1034,'依据：AM-ALT.3.4/joint/h100_392.cir 的调制支路；未新增仿真，未保证实物幅度或最终发射性能。',17)
c.showPage();c.save()
doc=fitz.open(PDF)
for i,p in enumerate(doc):p.get_pixmap(matrix=fitz.Matrix(1.2,1.2),alpha=False).save(O/f'page_{i+1}.png')
print(PDF)
