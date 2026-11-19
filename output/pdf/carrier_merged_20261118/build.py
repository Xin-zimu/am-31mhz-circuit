from pathlib import Path
import math
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape

O = Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('CN', r'C:\Windows\Fonts\msyh.ttc', subfontIndex=0))
W,H=2400,1550
PW,PH=landscape(A3)
PDF=O/'C518062_载波三级拼接原理图_R1.pdf'
c=canvas.Canvas(str(PDF),pagesize=(PW,PH))
c.setTitle('C518062 + 射随缓冲 + 共射增益：三级载波原理图')
ink='#172d41'; red='#c43c36'; blue='#146fa5'; orange='#b36b00'; purple='#8240a5'
def start(): c.saveState(); c.scale(PW/W,PH/H)
def line(x,y,X,Y,col=ink,w=2.5):
 c.setStrokeColor(HexColor(col)); c.setLineWidth(w); c.line(x,H-y,X,H-Y)
def text(x,y,s,size=24,col=ink):
 c.setFont('CN',size); c.setFillColor(HexColor(col)); c.drawString(x,H-y,s)
def box(x,y,w,h,fill='#ffffff',stroke=ink):
 c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke)); c.setLineWidth(2); c.rect(x,H-y-h,w,h,fill=1,stroke=1)
def dot(x,y,col=ink):
 c.setFillColor(HexColor(col));c.circle(x,H-y,4.5,fill=1,stroke=0)
def ground(x,y):
 line(x,y,x,y+13)
 for a,b in [(15,0),(10,8),(4,16)]:line(x-a,y+13+b,x+a,y+13+b)
def rv(x,y,Y,label='',side=24):
 m=(y+Y)/2;line(x,y,x,m-32);box(x-12,m-32,24,64);line(x,m+32,x,Y)
 if label:text(x+side,m+8,label,23)
def cv(x,y,Y,label='',side=24):
 m=(y+Y)/2;line(x,y,x,m-9);line(x-22,m-9,x+22,m-9);line(x-22,m+9,x+22,m+9);line(x,m+9,x,Y)
 if label:text(x+side,m+8,label,23)
def ch(x,X,y,label):
 m=(x+X)/2;line(x,y,m-9,y);line(m-9,y-22,m-9,y+22);line(m+9,y-22,m+9,y+22);line(m+9,y,X,y)
 tw=pdfmetrics.stringWidth(label,'CN',22);text(m-tw/2,y-38,label,22)
def npn(x,y,name):
 line(x,y-45,x,y+45);line(x,y-25,x+75,y-90);line(x,y+25,x+75,y+90)
 a=math.atan2(65,75); X,Y=x+62,y+79
 for d in [-.45,.45]:line(X,Y,X-18*math.cos(a+d),Y-18*math.sin(a+d))
 text(x+96,y-5,name,26);text(x+96,y+30,'2N3904',22)
 text(x+87,y-95,'3 C',20);text(x-47,y+31,'2 B',20);text(x+87,y+90,'1 E',20)
def header(title,sub,n):
 box(0,0,W,155,'#112e43','#112e43');text(65,70,title,43,'#ffffff');text(65,121,sub,25,'#dbe8ee')
 text(65,1510,'31 MHz AM 项目 | 拼接接线版 R1 | 2026-11-18 | 保留原图参数，联合带载性能待验证',22,'#607486')
 text(2200,1510,f'{n} / 2',23)
def end():c.restoreState();c.showPage()

start()
header('C518062 晶体振荡器 + 射随缓冲 + 共射增益','信号从左向右；实线已接通；黑点为连接点；全部 +5 V 与 GND 分别共网。基带模块不在此信号链内。',1)
for x,w,s in [(65,780,'① C518062 晶体振荡器'),(980,530,'② 射随缓冲'),(1690,640,'③ 共射增益')]:
 box(x,185,w,65,'#edf4f8','#edf4f8');text(x+20,229,s,29)
# Shared supply and return.
line(90,310,2300,310,red,3);text(90,291,'J1+ / +5 V',26,red)
line(90,920,2300,920,ink,3);ground(90,920);text(120,964,'J1- / GND（三级共地）',24)
# Oscillator.
npn(470,510,'Q1');line(545,310,545,420,red)
rv(335,310,510,'');text(180,410,'R1 10 kΩ',23);rv(335,510,920,'R2 10 kΩ')
line(160,510,470,510,blue);dot(335,510);text(160,480,'B / 晶体节点',23,blue)
line(160,510,160,685,blue);line(132,685,188,685);box(147,702,26,44);line(132,763,188,763);line(160,763,160,920)
text(65,806,'X1 C518062',23);text(65,841,'31 MHz',23)
line(545,600,545,650,orange);rv(545,650,920,'R3 4.7 kΩ');dot(545,650)
# Feedback branches: B -- C1 -- E -- C2 -- GND.
line(410,510,410,380,blue);dot(410,510);line(410,380,530,380,blue)
c.setStrokeColor(HexColor(blue));p=c.beginPath();p.moveTo(530,H-380);p.curveTo(530,H-360,560,H-360,560,H-380);c.drawPath(p)
line(560,380,735,380,blue)
cv(735,380,650,'C1 33 pF');cv(735,650,920,'C2 33 pF');dot(735,650)
line(545,650,850,650,orange);text(575,690,'E / 接扩展输入',23,orange)
# Original weak sample, separate from extension input.
line(900,650,900,700,orange);dot(900,650);cv(900,700,820,'');text(930,765,'C5 2.2 pF',23,purple)
line(900,820,900,860,purple);dot(900,860,purple);text(930,859,'TP1',24,purple)
text(650,1004,'TP1 仅弱耦合观察',22,purple)
text(650,1044,'拱桥跨线处不相连',22,blue)
# Extension input from E, routed outside feedback branch.
line(850,650,940,650,orange);line(940,650,940,510,orange);ch(940,1100,510,'CIN 1 nF');line(1100,510,1250,510,blue)
rv(1140,310,510,'RBT 10 kΩ');rv(1140,510,920,'RBB 10 kΩ');dot(1140,510)
npn(1250,510,'QB');line(1325,310,1325,420,red);line(1325,600,1325,650,orange);dot(1325,650)
rv(1325,650,920,'REB 330 Ω')
line(1325,650,1480,650,orange);line(1480,650,1480,510,orange)
ch(1480,1620,510,'COUTB 1 nF');dot(1620,510,purple);text(1575,575,'BO',26,purple)
ch(1620,1780,510,'CG 10 nF');line(1780,510,1950,510,blue)
rv(1820,310,510,'RG1 22 kΩ');rv(1820,510,920,'RG2 4.7 kΩ');dot(1820,510)
npn(1950,510,'QG');rv(2025,310,420,'');text(2070,330,'RCG 1 kΩ',23)
dot(2025,420);ch(2025,2240,420,'COUTG 10 nF');line(2240,420,2240,520,purple);dot(2240,520,purple)
text(2175,571,'OUT',27,purple);text(2160,607,'TP_OUT',22,purple)
rv(2240,520,920,'');text(2090,770,'RL 2 kΩ',24);text(2090,809,'1 kΩ + 1 kΩ',20)
line(2025,600,2025,650,orange);rv(2025,650,920,'');text(1840,800,'REG 56 Ω',23)
text(1720,1004,'REG 不加旁路电容；RL 为测试负载。',23)
text(1720,1044,'OUT 不接示波器 50 Ω 输入。',23)
# Explicit local decoupling strip.
box(65,1090,2270,167,'#f5f8fa','#dce5ec')
text(90,1128,'供电去耦（与上方 +5 V / GND 同名相连；放在对应级附近）',25)
for x,label in [(220,'C3 100 nF / Q1'),(780,'CB 100 nF / QB'),(1340,'CGD 100 nF / QG'),(1900,'C4 10 µF / 电源入口')]:
 line(x,1160,x+180,1160,red);cv(x,1160,1220,'');ground(x,1220);text(x+38,1207,label,22)
 if x==1900:text(x+28,1179,'+',20,red)
text(90,1310,'连接重点：原板 E（F6 / H6 / I5 / J5 / K6 同网）→ CIN → QB；COUTB → BO → CG → QG。',27)
text(90,1360,'本图保留 COUTB、CG 两只级间电容；接上 QG 后拆掉 BO 的临时测试负载，仅保留 OUT 的 RL。',25)
text(90,1410,'图纸为原电路拼接，尚未完成三级联合实物验证；频率、幅度、启动及晶体激励须在接入后重新确认。',24)
end()

start()
header('接线核对与基带模块的边界','本页说明如何把旧板接到扩展级；原 C518062 万能板孔位与原有跳线不因本图改变。',2)
text(90,230,'三级载波接线表',33)
rows=[
 ('原振荡板 → 扩展输入','E 节点引线 → CIN 1 nF → QB 基极偏置节点。优先就近取 F6 / H6 / I5。'),
 ('缓冲级 → 增益级','QB 发射极 → COUTB 1 nF → BO → CG 10 nF → QG 基极偏置节点。'),
 ('公共供电与地','原板 J1+、QB 与 QG 的 +5 V 共接；原板 J1-、两级 GND、仪器参考地共接。'),
 ('原板 TP1 保留','TP1 位于 C5 2.2 pF 之后，仍作弱耦合观察；它不作为 CIN 的信号源。'),
 ('输出与负载','COUTG 10 nF 后为 OUT；调试时接 2 kΩ 到 GND。用 10X 高阻探头测量。'),
 ('引脚和去耦','三只管按原图 onsemi 定义：1=E、2=B、3=C；QB/QG 各加 100 nF 就地去耦。'),
]
for i,(a,b) in enumerate(rows):
 y=263+i*79;box(90,y,2220,79,'#f2f6f9' if i%2==0 else '#ffffff','#dce5ec');text(112,y+48,a,25);text(500,y+48,b,24)
text(90,805,'基带是独立模块：现在不接入上述三个射频级',33)
box(90,845,2220,210,'#edf4f8','#dce5ec')
text(120,891,'基带板：LM393 振荡器（20 kHz）→ 占空比调节 → 幅度调节 → V1 输出',29)
text(120,944,'载波板：C518062（31 MHz）→ QB 射随缓冲 → QG 共射增益 → OUT 输出',29)
text(120,1000,'后续：V1 与载波 OUT 分别进入调制级。当前这三段没有基带调制输入，V1 暂时悬空。',26)
text(90,1120,'调试顺序与适用范围',31)
for y,s in [
 (1170,'1. 原振荡板先单独工作；接 QB 后复查启动、频率与波形，再接 QG 并复查带载输出。'),
 (1220,'2. 原册 5 mA 限流步骤只针对独立振荡板；三级接齐后，需按新增偏置电流重新设置限流。'),
 (1270,'3. 基带可单独用 5 V 调试；以后共用电源时要共地并保留各自去耦，信号通过调制级结合。'),
 (1320,'4. 本次核对的是图纸网络与元件值；未新增仿真或实物验收，不承诺 OUT 约 2 Vpp。')]:text(112,y,s,25)
text(90,1390,'来源：C518062_万能板实验图册_R1.pdf 第 1 页；焊接原理图_基带与载波.pdf 第 3 页。',22,'#607486')
text(90,1430,'基带说明依据后一份图纸第 1-2 页。电阻/电容沿用原位号；CB、CGD 为本图新增的去耦位号。',22,'#607486')
end();c.save()
doc=fitz.open(PDF)
for i,p in enumerate(doc):p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(O/f'preview_{i+1}.png')
print(PDF)
