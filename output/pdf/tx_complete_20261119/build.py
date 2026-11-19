from pathlib import Path
import math, json, csv
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
O=Path(__file__).resolve().parent; ROOT=O.parents[2]
pdfmetrics.registerFont(TTFont('CN',r'C:\Windows\Fonts\msyh.ttc',subfontIndex=0))
INK='#172d41'; RED='#c43c36'; BLUE='#146fa5'; PURPLE='#8240a5'
class Draw:
 def __init__(self,name,w,h):
  self.w=w;self.h=h;self.path=O/name;self.c=canvas.Canvas(str(self.path),pagesize=(w,h))
 def line(self,x,y,X,Y,col=INK,width=2.5):
  self.c.setStrokeColor(HexColor(col));self.c.setLineWidth(width);self.c.line(x,self.h-y,X,self.h-Y)
 def wire(self,pts,col=INK,width=2.5):
  for (x,y),(X,Y) in zip(pts,pts[1:]):self.line(x,y,X,Y,col,width)
 def text(self,x,y,s,size=23,col=INK):
  self.c.setFont('CN',size);self.c.setFillColor(HexColor(col));self.c.drawString(x,self.h-y,s)
 def box(self,x,y,w,h,fill='#ffffff',stroke=INK):
  self.c.setFillColor(HexColor(fill));self.c.setStrokeColor(HexColor(stroke));self.c.setLineWidth(2);self.c.rect(x,self.h-y-h,w,h,fill=1,stroke=1)
 def dot(self,x,y):
  self.c.setFillColor(HexColor(INK));self.c.circle(x,self.h-y,4,fill=1,stroke=0)
 def ground(self,x,y):
  self.line(x,y,x,y+10)
  for a,b in [(14,0),(9,7),(3,14)]:self.line(x-a,y+10+b,x+a,y+10+b)
 def rv(self,x,y,Y,s='',left=False):
  m=(y+Y)/2;self.line(x,y,x,m-27);self.box(x-11,m-27,22,54);self.line(x,m+27,x,Y)
  if s:self.text(x-190 if left else x+24,m+7,s,22)
 def rh(self,x,X,y,s):
  m=(x+X)/2;self.line(x,y,m-30,y);self.box(m-30,y-11,60,22);self.line(m+30,y,X,y)
  self.text(m-pdfmetrics.stringWidth(s,'CN',22)/2,y-30,s,22)
 def cv(self,x,y,Y,s='',polar=False):
  m=(y+Y)/2;self.line(x,y,x,m-8);self.line(x-21,m-8,x+21,m-8);self.line(x-21,m+8,x+21,m+8);self.line(x,m+8,x,Y)
  if s:self.text(x+28,m+7,s,22)
  if polar:self.text(x+25,m-18,'+',22,RED)
 def ch(self,x,X,y,s):
  m=(x+X)/2;self.line(x,y,m-8,y);self.line(m-8,y-21,m-8,y+21);self.line(m+8,y-21,m+8,y+21);self.line(m+8,y,X,y)
  self.text(m-pdfmetrics.stringWidth(s,'CN',22)/2,y-35,s,22)
 def arrow(self,x,y,X,Y):
  self.line(x,y,X,Y);a=math.atan2(Y-y,X-x)
  for d in [-.45,.45]:self.line(X,Y,X-15*math.cos(a+d),Y-15*math.sin(a+d))
 def npn(self,x,y,s):
  self.line(x,y-45,x,y+45);self.line(x,y-25,x+75,y-90);self.line(x,y+25,x+75,y+90);self.arrow(x+30,y+51,x+61,y+78)
  self.text(x+100,y+3,s,27);self.text(x+100,y+36,'2N3904BU',22)
  self.text(x+85,y-99,'3 C',19);self.text(x-50,y+28,'2 B',19);self.text(x+85,y+91,'1 E',19)
 def comp(self,x,y,s,pp,pm,po):
  self.wire([(x,y-100),(x,y+100),(x+220,y),(x,y-100)])
  self.text(x+17,y-31,'+',27);self.text(x+17,y+49,'-',27);self.text(x+70,y+7,s,27)
  self.text(x-28,y-49,str(pp),19);self.text(x-28,y+63,str(pm),19);self.text(x+225,y-14,str(po),19)
 def header(self,title,sub):
  self.box(0,0,self.w,135,'#112e43','#112e43');self.text(45,60,title,35,'#ffffff');self.text(45,108,sub,22,'#dbe8ee')
 def done(self):self.c.save();return fitz.open(self.path)

# Full continuous baseband, with no OSC/RAMP/DUTY input stubs.
d=Draw('module_bb.pdf',3900,1400)
d.header('基带：LM393 振荡 + 占空比 + 幅度调节','U1A/U1B 为同一颗 LM393P；实线连接完整。RVRF用100 kΩ多圈，先调约15.3 kΩ后实测定频。')
d.line(100,250,3550,250,RED);d.text(100,220,'+5 V',25,RED)
d.rv(150,250,410,'RHT 30 kΩ');d.rv(150,410,900,'RHB 10 kΩ');d.ground(150,900)
d.line(150,410,650,410,BLUE);d.dot(150,410);d.dot(400,410);d.text(430,385,'HYST',23,BLUE)
d.comp(650,450,'U1A',3,2,1);d.line(870,450,1300,450);d.dot(1150,450)
d.rv(1150,250,450,'RPU1 2.2 kΩ');d.text(920,495,'OSC / TP_OSC',23)
d.wire([(1150,450),(1150,650),(700,650)]);d.rh(400,700,650,'RHF 20 kΩ');d.line(400,650,400,410)
d.rh(1300,1550,450,'RFIX 22 kΩ');d.rh(1550,1850,450,'RVRF 100 kΩ可调')
d.wire([(1580,450),(1580,540),(1700,540)]);d.arrow(1700,540,1700,465);d.dot(1580,450)
d.text(1520,585,'滑端与左端短接；起调15.3 kΩ',22)
d.line(1850,450,2150,450,BLUE);d.dot(2050,450);d.cv(2050,450,900,'CT 1 nF C0G');d.ground(2050,900)
# Ramp to U1A: bridge over OSC return at x1150.
d.wire([(650,490),(610,490),(610,570),(1130,570)],BLUE)
d.c.setStrokeColor(HexColor(BLUE));p=d.c.beginPath();p.moveTo(1130,d.h-570);p.curveTo(1130,d.h-545,1170,d.h-545,1170,d.h-570);d.c.drawPath(p)
d.wire([(1170,570),(1200,570),(1200,1100),(2150,1100),(2150,450)],BLUE)
d.text(1230,1080,'RAMP：2脚、6脚与CT上端同网',23,BLUE)
d.dot(2150,1100);d.wire([(2150,1100),(2350,1100),(2350,1050),(2920,1050),(2920,490),(3000,490)],BLUE)
d.rv(2550,250,350,'RDT 10 kΩ');d.line(2550,350,2550,400);d.box(2538,400,24,200);d.line(2550,600,2550,650)
d.rv(2550,650,900,'RDB 4.7 kΩ');d.ground(2550,900);d.text(2360,375,'RVD 10 kΩ',23)
d.arrow(2730,500,2565,500);d.wire([(2730,500),(2800,500),(2800,410),(3000,410)],BLUE);d.text(2820,380,'DUTY / 滑端',23,BLUE)
d.comp(3000,450,'U1B',5,6,7);d.line(3220,450,3550,450);d.dot(3350,450);d.rv(3350,250,450,'RPU2 2.2 kΩ')
d.text(3225,500,'PWM_RAW / TP_PWM',22)
d.line(3550,450,3550,600);d.box(3538,600,24,150);d.line(3550,750,3550,900);d.ground(3550,900)
d.arrow(3700,675,3565,675);d.line(3700,675,3850,675,PURPLE);d.dot(3850,675);d.text(3700,640,'V1 / TP_V1',24,PURPLE)
d.text(3400,960,'RVA 20 kΩ 三端幅度电位器',23)
d.box(1400,160,520,165,'#f1f6f9','#dce5ec');d.text(1420,200,'U1 电源：8脚接 +5 V；4脚接GND',22)
d.text(1420,240,'100 nF 就近跨8/4脚；10 µF在入口',22);d.text(1420,280,'去耦实物见右下图（同名网络相连）',22)
d.line(3160,1110,3670,1110,RED);d.text(3160,1080,'+5 V / U1附近',22,RED)
d.cv(3200,1110,1260,'CDEC 100 nF');d.ground(3200,1260);d.cv(3580,1110,1260,'CBULK 10 µF',True);d.ground(3580,1260)
d.text(80,1200,'U1 LM393P 顶视脚号：1 OUTA；2 INA-；3 INA+；4 GND；5 INB+；6 INB-；7 OUTB；8 VCC。',24)
d.text(80,1250,'先20 kHz，再10/30/50%占空比，最后V1调1/2/3/4 Vpp；接调制板后重新校准。',24)
d.text(80,1300,'本图跨线用拱桥；无黑点交叉不相连。20 kΩ幅度电位器不能用固定电阻代替。',23)
bb=d.done()

# Driver: faithful frozen topology; QCE collector directly biases QEF base.
d=Draw('module_driver.pdf',1800,1200)
d.header('调制后的射频驱动：QCE + QEF','TP3 经 CDRV 接入；QCE集电极直连QEF基极，中间不串电容。元件值沿用冻结方案。')
d.line(400,250,1650,250,RED);d.text(400,218,'+5 V',26,RED)
d.text(55,470,'TP3输入',24,BLUE);d.line(80,480,80,510,BLUE);d.ch(80,420,510,'CDRV 10 nF');d.line(420,510,700,510,BLUE)
d.rv(550,250,510,'RDB1 40 kΩ');d.rv(550,510,1000,'RDB2 10 kΩ');d.dot(550,510)
d.npn(700,510,'QCE');d.rv(775,250,420,'');d.text(805,330,'RDC 1.25 kΩ',23);d.dot(775,420)
d.line(775,420,1250,420,BLUE);d.text(1000,388,'DRV_C → QEF基极',22,BLUE)
d.line(775,600,775,650);d.dot(775,650);d.rv(775,650,1000,'RDE 150 Ω',True)
d.line(775,650,1000,650);d.cv(1000,650,1000,'CDE 100 nF')
d.npn(1250,420,'QEF');d.line(1325,250,1325,330,RED);d.line(1325,510,1325,600);d.dot(1325,600)
d.rv(1325,600,1000,'REF 200 Ω');d.rh(1325,1660,600,'RSENSE 10 Ω');d.dot(1660,600);d.text(1560,655,'SENSE_OUT',24,PURPLE)
d.line(400,1000,1690,1000);d.ground(400,1000)
d.cv(1610,760,930,'');d.text(1410,770,'CDD 100 nF',22);d.text(1590,742,'+5 V',20,RED);d.ground(1610,930)
d.text(55,1090,'实物替代需记录：RDB1 40 kΩ → 39 kΩ；RDC 1.25 kΩ → 1.2 kΩ，替代后重测偏置和包络。',22)
d.text(55,1133,'源端 EF_E 在10 Ω之前；SENSE_OUT在10 Ω之后。取样测量时，两探头地均接GND。',22)
driver=d.done()

# Physical matching and radiator. No equivalent parasitic parts masquerade as BOM.
d=Draw('module_match.pdf',1800,1300)
d.header('取样后的匹配网络 + 实物天线','当前候选：90 cm拉杆，1812CS-392成品电感；CT与CF并联，整个电容组串入馈电路径。')
d.text(55,230,'接 SENSE_OUT',25,PURPLE);d.line(80,245,80,280);d.line(80,280,300,280)
d.text(335,205,'LFIX 3.9 µH',25);d.text(325,241,'Coilcraft 1812CS-392',22)
for i in range(5):
 x=300+i*70;p=d.c.beginPath();p.moveTo(x,d.h-280);p.curveTo(x,d.h-235,x+70,d.h-235,x+70,d.h-280);d.c.drawPath(p)
d.line(650,280,800,280);d.dot(800,280);d.wire([(800,280),(800,220)])
d.ch(800,1300,220,'CF 10 pF C0G');d.wire([(1300,220),(1300,280)]);d.dot(1300,280)
d.wire([(800,280),(800,450)]);d.ch(800,1300,450,'CTUNE 2~18 pF 微调');d.arrow(1020,495,1085,430);d.wire([(1300,450),(1300,280)])
d.line(1300,280,1470,280,BLUE);d.text(1325,250,'ANT_FEED',23,BLUE)
d.box(1470,220,250,360,'#f8fafb','#dce5ec');d.text(1485,615,'绝缘天线底座',24)
d.line(1470,280,1580,280,BLUE);d.line(1580,280,1580,210,BLUE)
d.line(1580,210,1540,175,BLUE);d.line(1580,210,1620,175,BLUE)
d.text(1420,690,'拉杆总展开长度90 cm',24);d.text(1420,730,'中心馈点与地端绝缘',23)
d.line(1470,520,1690,520);d.line(1690,520,1690,850);d.ground(1690,850)
d.text(1450,795,'地端 → RF GND',23)
# Radial ground shown as eight real conductors joined at one hub.
d.dot(1100,850);d.line(1100,850,1690,850)
for a in range(0,360,45):
 r=math.radians(a);d.line(1100,850,1100+170*math.cos(r),850+130*math.sin(r))
d.text(650,1055,'8根径向地网，每根50 cm；汇点与电路GND、底座地端相连。',24)
d.text(70,1110,'起调参考：CF 10 pF + CT约16.8 pF，总约26.8 pF；只对应当前90 cm候选，必须实测31 MHz调谐。',22)
d.text(70,1152,'CF取10 pF为便于实物采购的起调分配；模型8.8187 pF + 18 pF不是要求购买8.8187 pF电容。',22)
d.text(70,1194,'不另焊模型中的RANT/LANT/CANT、线圈ESR/自容、2 nH引线及0.5 pF底座电容。',22)
d.text(70,1236,'此候选尚未完成实物匹配/6 m验证；电感焊盘用短接转接，不自绕加载线圈。',22)
match=d.done()

d=Draw('module_power.pdf',1500,500)
d.header('供电：现阶段使用稳压5 V实验电源','这是完整发射信号链的5 V供电接法；9 V电池稳压器尚未定型，不把9 V直接接到5 V网络。')
d.box(60,190,250,180,'#f1f6f9','#dce5ec');d.text(80,233,'J_PWR 两针输入',25)
d.text(80,285,'1：+5 V',24,RED);d.text(80,335,'2：GND',24)
d.line(310,278,1390,278,RED);d.line(310,328,410,328);d.line(410,328,410,410);d.ground(410,410)
d.text(480,240,'+5 V → 载波、基带、调制、驱动全部同名供电点',24,RED)
d.cv(800,278,410,'CINP 100 nF');d.ground(800,410);d.cv(1190,278,410,'CBP 10 µF',True);d.ground(1190,410)
power=d.done()

# Existing original module drawings, fully retained at vector resolution.
rf=fitz.open(ROOT/'output/pdf/modulator_20261119/载波_基带_调制_完整展开原理图_R2.pdf')
mod=fitz.open(ROOT/'output/pdf/modulator_20261119/基极调制级_焊接原理图与接线表_R1.pdf')
mod[0].add_redact_annot(fitz.Rect(50,980,1545,1020),fill=(1,1,1));mod[0].apply_redactions()
# A larger modulator detail sheet includes both real decoupling capacitors.
md=Draw('mod_decoupling.pdf',1600,1350)
md.text(55,1008,'去耦完整画在本页下方；CDM 100 nF、CBM 10 µF分别跨接+5 V与GND。',20)
md.line(100,1160,1440,1160,RED);md.text(100,1138,'调制板就地 +5 V 去耦（与上方供电同网）',23,RED)
md.cv(250,1160,1290,'CDM 100 nF');md.ground(250,1290)
md.cv(950,1160,1290,'CBM 10 µF',True);md.ground(950,1290)
mdoc=md.done();mod_full=fitz.open();mp=mod_full.new_page(width=1600,height=1350)
mp.show_pdf_page(fitz.Rect(0,0,1600,1120),mod,0);mp.show_pdf_page(mp.rect,mdoc,0)
out=fitz.open();page=out.new_page(width=6500,height=3400)
def place(doc,n,src,dst,logical=None):
 p=doc[n];r=fitz.Rect(src)
 if logical:r=fitz.Rect(src[0]*p.rect.width/logical[0],src[1]*p.rect.height/logical[1],src[2]*p.rect.width/logical[0],src[3]*p.rect.height/logical[1])
 page.show_pdf_page(fitz.Rect(dst),doc,n,clip=r,keep_proportion=False)
place(rf,1,(50,170,2340,1260),(50,200,2340,1290),(2400,1550))
place(mod,0,(50,160,1550,970),(2500,200,4000,1010))
place(driver,0,(0,0,1800,1200),(4300,200,6100,1400))
place(bb,0,(0,0,3900,1400),(50,1650,3950,3050))
place(power,0,(0,0,1500,500),(2500,1200,4000,1620))
place(match,0,(0,0,1800,1300),(4300,1700,6100,3000))
a=Draw('overview_overlay.pdf',6500,3400)
a.text(55,70,'发射端完整原理图：基带 + 晶体载波 + 调制 + 两级驱动 + 匹配 + 天线',51)
a.text(55,125,'R3 / 2026-11-19 | 所有模块均展开；同名 +5 V 与 GND 共网；黑点相连、拱桥不相连。整机尚未完成实物验收。',29)
a.text(2520,178,'基极调制（完整元件见放大页）',31)
a.wire([(2240,450),(2430,450),(2430,265),(2540,265)],BLUE,4);a.dot(2240,450)
a.text(2260,495,'OUT → 调制',24,BLUE)
a.wire([(3900,465),(4160,465),(4160,710),(4380,710)],PURPLE,4);a.dot(3900,465)
a.text(4010,430,'TP3 → CDRV',23,PURPLE)
a.wire([(3900,2325),(4100,2325),(4100,1160),(2460,1160),(2460,795),(2540,795)],PURPLE,4);a.dot(3900,2325)
a.text(4125,2190,'V1 → 调制',25,PURPLE)
a.wire([(5960,800),(6200,800),(6200,1630),(4380,1630),(4380,1980)],PURPLE,4);a.dot(5960,800)
a.text(6220,1100,'10 Ω后',24,PURPLE);a.text(6220,1140,'送匹配网络',24,PURPLE)
a.box(1650,960,680,130,'#ffffff','#ffffff')
a.text(1800,1010,'OUT临时2 kΩ不装；',25);a.text(1800,1052,'TP3的1 kΩ保留。',25)
a.line(2670,1025,3850,1025,RED);a.text(2670,1003,'调制板 +5 V 就地去耦',23,RED)
a.cv(2730,1025,1110,'CDM 100 nF');a.ground(2730,1110)
a.cv(3400,1025,1110,'CBM 10 µF',True);a.ground(3400,1110)
a.text(4300,1500,'所有六只三极管：onsemi 2N3904BU，实物脚号1=E、2=B、3=C。',26)
a.text(80,3150,'装配依据：AM-ALT.3.4 h90_392冻结拓扑；基带使用100 kΩ频率微调；匹配采用实物起调值，需安装后实测。',29)
a.text(80,3210,'电阻优先用图中标称值；如按台账使用36 kΩ/39 kΩ/1.2 kΩ，记录替代并复测，不把旧仿真当实物保证。',29)
a.text(80,3270,'探头记录：RP2200实体10X、示波器菜单1X时，电压显示值×10；当前OUT约2.36 Vpp为该条件下换算值。',29)
a.text(80,3330,'完整指已展开当前全部发射模块；电池稳压、匹配实物、边沿失真与6 m链路尚未闭合。后附各模块放大图与接线表。',27)
ov=a.done();page.show_pdf_page(page.rect,ov,0)
out.insert_pdf(rf,from_page=1,to_page=1)
out.insert_pdf(bb)
out.insert_pdf(mod_full)
out.insert_pdf(driver)
out.insert_pdf(match)
out.insert_pdf(power)

# Wiring and BOM sheet, including important scope distinctions and measurement paths.
d=Draw('connections.pdf',2100,1450)
d.header('装配接线与版本说明','总图是当前5 V实验供电版；射频天线匹配为候选起调方案，不能称已定型或已保证6 m。')
rows=[('载波 → 调制','QG经COUTG后的OUT → RMRF 2.2 kΩ；拆OUT临时2 kΩ负载。'),
('基带 → 调制','RVA 20 kΩ滑端V1 → RPRE 10 kΩ；先20 kHz、50%、1 Vpp再逐步调节。'),
('调制 → 驱动','QM经CMOUT后的TP3 → CDRV 10 nF → DRV_B；TP3的1 kΩ保留。'),
('共射 → 射随','QCE集电极DRV_C直接接QEF基极；不另加级间电容或偏置分压。'),
('驱动 → 匹配','QEF发射极EF_E → RSENSE 10 Ω → SENSE_OUT → LFIX。'),
('匹配 → 天线','LFIX后接CT与CF并联组；电容组另一端接绝缘底座中心端/拉杆馈点。'),
('公共地','电源负端、各板GND、底座地端、8根地网汇点共接；底座中心端不能短接地。'),
('取样测电流','两探头分别测EF_E和SENSE_OUT，地均接GND；差分电压除以10 Ω。'),
('晶体与探头','X1用原C518062；TP1保留弱耦合；不额外焊晶体BVD模型元件或探头等效电容。')]
for i,(s,t) in enumerate(rows):
 y=165+i*67;d.box(50,y,2000,67,'#f1f6f9' if i%2==0 else '#ffffff','#dce5ec');d.text(70,y+42,s,24);d.text(360,y+42,t,24)
d.text(55,835,'图中保留冻结值：RMINJ=37 kΩ；RDB1=40 kΩ；RDC=1.25 kΩ。台账可购替代分别为36 kΩ、39 kΩ、1.2 kΩ。',23)
d.text(55,880,'基带：U1 LM393P×1；RVRF 100 kΩ多圈×1（有效阻值约15.3 kΩ起调）；RVD 10 kΩ×1；RVA 20 kΩ×1。',24)
d.text(55,925,'有源射频器件共6只：Q1、QB、QG、QM、QCE、QEF；均按onsemi 2N3904BU封装脚号装配。',24)
d.text(55,970,'匹配：LFIX成品1812CS-392（3.9 µH）；CT 2~18 pF；CF 10 pF C0G；拉杆90 cm；8根50 cm径向地网。',24)
d.text(55,1015,'新增就地去耦：调制板CDM 100 nF、CBM 10 µF；驱动板CDD 100 nF；电源入口CINP 100 nF、CBP 10 µF。',24)
d.text(55,1080,'设计边界：冻结模型已存在包络边沿塌陷；本次转绘不宣称修复。匹配损耗/寄生模型存在已记录差异，需实测回填。',23)
d.text(55,1125,'本次未设计9 V→5 V稳压器：现有证据只有其功耗假设，没有定型实物电路，因此图中明确使用外部稳压5 V。',23)
d.text(55,1170,'来源：stage_am_alt3_4_20261117/joint/h90_392.cir；03_匹配网络与补偿元件.md；原载波/基带/调制装配图。',22)
d.text(55,1230,'生成附件：physical_connections.tsv列出所有实物元件端点；build.py可重建图纸。图纸网络检查不等于实物或ERC验收。',23)
d.text(55,1300,'先分模块上电查偏置，再接调制/驱动；实物功耗最终从实际电源输入端测量，不用预算代替。',24)
out.insert_pdf(d.done())

# Physical net list for review, excludes semiconductor model internals and instrument equivalents.
parts=[]
def add(ref,value,*nodes):parts.append({'ref':ref,'value':value,'nodes':list(nodes)})
for ref,val,nodes in [
 ('R1','10k',('VCC','B')),('R2','10k',('B','GND')),('R3','4.7k',('E','GND')),('X1','C518062 31MHz',('B','GND')),
 ('Q1','2N3904BU',('VCC','B','E')),('C1','33p',('B','E')),('C2','33p',('E','GND')),('C3','100n',('VCC','GND')),('C4','10u',('VCC','GND')),
 ('C5','2.2p',('E','TP1')),('CIN','1n',('E','BF')),('RBT','10k',('VCC','BF')),('RBB','10k',('BF','GND')),('QB','2N3904BU',('VCC','BF','EF')),
 ('REB','330',('EF','GND')),('COUTB','1n',('EF','BO')),('CG','10n',('BO','BG')),('RG1','22k',('VCC','BG')),('RG2','4.7k',('BG','GND')),
 ('QG','2N3904BU',('CG_NODE','BG','EG')),('RCG','1k',('VCC','CG_NODE')),('REG','56',('EG','GND')),('COUTG','10n',('CG_NODE','OUT')),
 ('CB','100n',('VCC','GND')),('CGD','100n',('VCC','GND')),
 ('RHT','30k',('VCC','HYST')),('RHB','10k',('HYST','GND')),('RHF','20k',('OSC','HYST')),('RPU1','2.2k',('VCC','OSC')),
 ('RFIX','22k',('OSC','FSET')),('RVRF','100k rheostat init15.3k',('FSET','FSET','RAMP')),('CT','1n',('RAMP','GND')),
 ('RDT','10k',('VCC','DUTY_TOP')),('RVD','10k potentiometer',('DUTY_TOP','DUTY','DUTY_BOT')),('RDB','4.7k',('DUTY_BOT','GND')),
 ('RPU2','2.2k',('VCC','PWM_RAW')),('RVA','20k potentiometer',('PWM_RAW','V1','GND')),('U1','LM393P pins1..8',('OSC','RAMP','HYST','GND','DUTY','RAMP','PWM_RAW','VCC')),
 ('CDEC','100n',('VCC','GND')),('CBULK','10u',('VCC','GND')),
 ('RMRF','2.2k',('OUT','RF_TAP')),('RMRG','10',('RF_TAP','GND')),('CMRF','100p',('RF_TAP','MB')),('RMT','15k',('VCC','MB')),('RMB','3.3k',('MB','GND')),
 ('RPRE','10k',('V1','ENV')),('CENV','47p',('ENV','GND')),('RMINJ','37k',('ENV','MB')),('QM','2N3904BU',('MC','MB','ME')),
 ('RMC','1k',('VCC','MC')),('RME','470',('ME','GND')),('CME','1n',('ME','GND')),('CMOUT','100p',('MC','TP3')),('RTP3','1k',('TP3','GND')),
 ('CDM','100n',('VCC','GND')),('CBM','10u',('VCC','GND')),
 ('CDRV','10n',('TP3','DRV_B')),('RDB1','40k',('VCC','DRV_B')),('RDB2','10k',('DRV_B','GND')),('QCE','2N3904BU',('DRV_C','DRV_B','DRV_E')),
 ('RDC','1.25k',('VCC','DRV_C')),('RDE','150',('DRV_E','GND')),('CDE','100n',('DRV_E','GND')),('QEF','2N3904BU',('VCC','DRV_C','EF_E')),
 ('REF','200',('EF_E','GND')),('RSENSE','10',('EF_E','SENSE_OUT')),('CDD','100n',('VCC','GND')),
 ('LFIX','1812CS-392 3.9uH',('SENSE_OUT','COIL_OUT')),('CF','10p C0G',('COIL_OUT','ANT_FEED')),('CTUNE','2-18p init16.8p',('COIL_OUT','ANT_FEED')),
 ('ANT','90cm rod + 8x50cm radials',('ANT_FEED','GND')),('J_PWR','regulated5V',('VCC','GND')),('CINP','100n',('VCC','GND')),('CBP','10u',('VCC','GND'))
]:add(ref,val,*nodes)
with (O/'physical_connections.tsv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['Reference','Value','Nodes (Q=C,B,E; U1=physical1..8)']);w.writerows((p['ref'],p['value'],','.join(p['nodes'])) for p in parts)
refs=[p['ref'] for p in parts];assert len(refs)==len(set(refs))
assert sum(p['ref'] in ['Q1','QB','QG','QM','QCE','QEF'] for p in parts)==6
assert all(p['nodes']==['COIL_OUT','ANT_FEED'] for p in parts if p['ref'] in ['CF','CTUNE'])
dest=O/'发射端全模块连接原理图_R3.pdf';out.save(dest,garbage=4,deflate=True)
final=fitz.open(dest)
for i,p in enumerate(final):
 scale=min(2400/p.rect.width,1600/p.rect.height);p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(O/f'preview_{i+1}.png')
report={'pages':len(final),'physical_parts':len(parts),'unique_refs':True,'transistors':6,'matching_caps_parallel':True,'scope':'5V externally regulated full TX candidate; not hardware accepted'}
(O/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(dest);print(json.dumps(report,ensure_ascii=False))
