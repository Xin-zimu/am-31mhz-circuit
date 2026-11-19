from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import fitz

O=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('CN',r'C:\Windows\Fonts\simsun.ttc',subfontIndex=0))
W,H=1600,1120
c=canvas.Canvas(str(O/'焊接原理图_基带与载波.pdf'),pagesize=(W,H))
ink='#172638';blue='#146bb0';red='#c53531';orange='#b66b00';purple='#883cad'
def line(x,y,X,Y,col=ink,width=2):
 c.setStrokeColor(HexColor(col));c.setLineWidth(width);c.line(x,H-y,X,H-Y)
def text(x,y,s,size=21,col=ink):
 c.setFont('CN',size);c.setFillColor(HexColor(col));c.drawString(x,H-y,s)
def rect(x,y,w,h,fill=None):
 c.setStrokeColor(HexColor(ink));c.setLineWidth(2)
 c.setFillColor(HexColor(fill or '#ffffff'));c.rect(x,H-y-h,w,h,fill=1,stroke=1)
def dot(x,y,col=ink):
 c.setFillColor(HexColor(col));c.circle(x,H-y,4,fill=1,stroke=0)
def ground(x,y):
 line(x,y,x,y+12)
 for a,b in [(12,0),(7,7),(3,14)]:line(x-a,y+12+b,x+a,y+12+b)
def rv(x,y,Y,label):
 m=(y+Y)/2;line(x,y,x,m-28);rect(x-11,m-28,22,56);line(x,m+28,x,Y);text(x+24,m+7,label,20)
def rh(x,X,y,label):
 m=(x+X)/2;line(x,y,m-33,y);rect(m-33,y-11,66,22);line(m+33,y,X,y);text(m-50,y-27,label,20)
def cv(x,y,Y,label,polar=False):
 m=(y+Y)/2;line(x,y,x,m-8);line(x-20,m-8,x+20,m-8);line(x-20,m+8,x+20,m+8);line(x,m+8,x,Y);text(x+29,m+6,label,20)
 if polar:text(x+24,m-19,'+',20)
def ch(x,X,y,label):
 m=(x+X)/2;line(x,y,m-8,y);line(m-8,y-20,m-8,y+20);line(m+8,y-20,m+8,y+20);line(m+8,y,X,y);text(m-50,y-32,label,20)
def arrow(x,y,X,Y):
 import math
 line(x,y,X,Y);a=math.atan2(Y-y,X-x)
 for d in [-.45,.45]:line(X,Y,X-14*math.cos(a+d),Y-14*math.sin(a+d))
def comp(x,y,name,pplus,pminus,pout):
 line(x,y-100,x,y+100);line(x,y-100,x+220,y);line(x,y+100,x+220,y)
 text(x+15,y-32,'+',25);text(x+15,y+47,'-',25);text(x+65,y+7,name,24)
 text(x-28,y-53,str(pplus),18);text(x-28,y+65,str(pminus),18);text(x+227,y-15,str(pout),18)
def npn(x,y,name):
 line(x,y-45,x,y+45);line(x,y-25,x+75,y-90);line(x,y+25,x+75,y+90);arrow(x+30,y+51,x+61,y+78)
 text(x+98,y-8,name,23);text(x+98,y+24,'2N3904BU',20)
 text(x+86,y-100,'3 C',18);text(x-48,y+27,'2 B',18);text(x+86,y+88,'1 E',18)
def page(n,title,sub):
 c.setFillColor(HexColor('#112e43'));c.rect(0,H-145,W,145,fill=1,stroke=0)
 text(55,69,f'0{n}   '+title,36,'#ffffff');text(55,119,sub,20,'#d7e3ed')
 text(55,1091,'31 MHz AM 项目 · 实验接线版 · 2026-11-17 · 同名网络必须相连；黑点表示连接',17,'#65788c');text(1450,1091,f'{n} / 3',18)
def note(y,s):text(60,y,s,20)

page(1,'基带振荡器：先获得 20 kHz','U1A、U1B 属于同一颗 TI LM393P（DIP-8）；本页与第 2 页共同组成一块基带板。')
# Schmitt threshold divider
text(150,214,'+5 V',23,red);line(150,240,460,240,red)
rv(280,240,410,'RHT 30 kΩ');dot(280,410)
rv(280,410,640,'RHB 10 kΩ');ground(280,640)
line(280,410,780,410,blue);text(405,395,'HYST',23,blue)
comp(780,450,'U1A',3,2,1)
line(670,490,780,490,blue);text(590,497,'RAMP',23,blue)
line(1000,450,1240,450,orange);dot(1160,450);text(1020,495,'OSC / TP_OSC',21,orange)
rv(1160,240,450,'');text(985,330,'RPU1 2.2 kΩ',20);text(1125,215,'+5 V',23,red)
# feedback, routed above comparator with no crossing
line(1160,450,1160,620,orange);line(1160,620,650,620,orange)
rh(430,650,620,'RHF 20 kΩ');line(430,620,430,410,blue);dot(430,410)
# power explicit separate block
text(1320,215,'U1 电源',23)
line(1350,245,1350,285,red);text(1380,263,'+5 V',20,red);text(1310,310,'8脚（VCC）',20)
text(1310,360,'4脚（GND）',20);line(1350,370,1350,400);ground(1350,400)
text(1320,460,'芯片缺口朝上',20);text(1320,492,'顶视图左上为1脚',18)
# timing network bottom
text(100,752,'OSC（接1脚）',22,orange);line(180,780,260,780,orange)
rh(260,520,780,'RFIX 22 kΩ');rh(520,820,780,'RVRF 可调')
# rheostat wiper tied to left, explicit
line(550,780,550,856);line(550,856,670,856);arrow(670,856,670,795);dot(550,780)
text(525,903,'滑端与左端短接',19);text(525,933,'100 kΩ多圈；先调15.3 kΩ',19)
line(820,780,1080,780,blue);dot(970,780);text(880,752,'RAMP（接2、6脚）',22,blue)
cv(970,780,930,'CT 1 nF C0G');ground(970,930)
# decoupling
text(1220,725,'靠近芯片放去耦',20)
line(1220,760,1460,760,red);text(1220,748,'+5 V',18,red)
cv(1250,760,900,'100 nF');cv(1450,760,900,'10 µF',True)
ground(1250,900);ground(1450,900)
note(998,'现有料配值：30 kΩ = 20 kΩ + 10 kΩ；每个2.2 kΩ = 1 kΩ + 1 kΩ + 100 Ω + 100 Ω（串联）。')
note(1030,'先用5 V限流供电；在1脚测频率，调RVRF至20 kHz。100 kΩ替代原20 kΩ变阻器仅扩大调节范围，需实测标定。')
c.showPage()

page(2,'占空比＋幅度：20 kΩ电位器现在用上','接续第1页；RAMP接同一颗LM393的2脚/6脚。V1是基带输出，不是31 MHz射频输出。')
text(220,220,'+5 V',24,red);rv(300,245,425,'RDT 10 kΩ')
line(300,425,300,480);rect(288,480,24,150);line(300,630,300,680)
text(100,545,'RVD 10 kΩ',23);text(95,578,'占空比电位器',21)
arrow(480,555,315,555);line(480,555,580,555,blue);text(410,610,'DUTY / 滑端',20,blue)
rv(300,680,850,'RDB 4.7 kΩ');ground(300,850)
text(325,450,'外端A',18);text(325,669,'外端B',18)
comp(760,500,'U1B',5,6,7)
line(630,460,760,460,blue);text(600,432,'DUTY（接滑端）',21,blue)
line(630,540,760,540,blue);text(600,570,'RAMP（接第1页）',19,blue)
line(980,500,1320,500,orange);dot(1120,500);text(980,541,'PWM_RAW / TP_PWM',21,orange)
rv(1120,250,500,'RPU2 2.2 kΩ');text(1080,222,'+5 V',24,red)
line(1320,500,1320,575);rect(1308,575,24,150);line(1320,725,1320,850);ground(1320,850)
text(1190,900,'RVA 20 kΩ 幅度电位器',23)
arrow(1410,650,1335,650);line(1410,650,1510,650,purple);dot(1510,650,purple)
text(1430,618,'V1 / TP_V1',21,purple);text(1380,701,'滑端输出',21,purple)
text(1345,560,'外端A',18);text(1345,773,'外端B',18)
text(610,740,'U1B供电与U1A共用：8脚接+5 V，4脚接GND。',22)
text(610,785,'RVD、RVA的滑端必须用万用表确认，勿猜脚序。',22)
text(610,830,'RVA不是固定20 kΩ电阻；必须是三端电位器。',22)
note(970,'调试顺序：先20 kHz → 再10/30/50%占空比 → 再V1调1/2/3/4 Vpp。改变设置后复查另外两项。')
note(1002,'示波器用10X、高阻输入；地夹接GND。V1先仅接示波器，接入调制级后重新做带载幅度校准。')
note(1034,'本页不焊仿真仪器等效的1 MΩ/15 pF负载；实际探头本身会加载。此图尚不是实物验收结果。')
c.showPage()

page(3,'载波扩展：射随缓冲＋共射增益','沿用现有C1/d05载波连接；先调通原晶体振荡板，再逐级接入。本页两只管均为onsemi 2N3904BU。')
# two separate blocks connected by explicit BO labels for clean layout
text(70,210,'A  射随缓冲',27);line(110,260,670,260,red);text(120,244,'+5 V',22,red)
npn(470,490,'QB');line(545,260,545,400,red)
rv(320,260,490,'RBT 10 kΩ');dot(320,490);line(320,490,470,490,blue)
rv(320,490,810,'RBB 10 kΩ')
text(60,400,'原振荡板 E 节点',20,blue);line(80,420,80,490,blue);ch(80,280,490,'CIN 1 nF');line(280,490,320,490,blue)
line(545,580,545,630,orange);dot(545,630);rv(545,630,810,'REB 330 Ω')
ch(545,750,630,'COUTB 1 nF');text(705,680,'BO',24,purple)
line(150,810,670,810);ground(150,810)
text(80,865,'取原板E节点，不取2.2 pF弱耦合TP1。',20)
# gain right
text(850,210,'B  共射增益',27);line(870,260,1450,260,red);text(880,244,'+5 V',22,red)
npn(1190,520,'QG')
rv(1020,260,520,'RG1 22 kΩ');dot(1020,520);line(1020,520,1190,520,blue)
rv(1020,520,810,'RG2 4.7 kΩ')
text(830,452,'BO（接左侧）',20,purple);line(850,470,850,520,purple);ch(850,1000,520,'CG 10 nF');line(1000,520,1020,520,blue)
rv(1265,260,430,'RCG 1 kΩ');dot(1265,430)
line(1265,610,1265,650,orange);rv(1265,650,810,'');text(1100,750,'REG 56 Ω',20)
line(870,810,1460,810);ground(870,810)
ch(1265,1510,430,'COUTG 10 nF');line(1510,430,1510,500,purple);text(1370,490,'OUT / TP_OUT',21,purple)
rv(1510,500,810,'');text(1370,720,'测试负载2 kΩ',20);text(1370,750,'1 kΩ＋1 kΩ',19);line(1460,810,1510,810)
text(860,865,'REG不加旁路电容；OUT负载不是50 Ω。',20)
note(930,'两级均在供电附近各加100 nF去耦，板入口加10 µF（正端接+5 V）；地与原振荡板GND相连。')
note(962,'实际管脚：1=E、2=B、3=C；按厂家封装图确认方向，勿把SPICE的C/B/E顺序当实物脚序。')
note(994,'先测B/E/C直流，再测BO、OUT频率和幅度。单测BO时可加2 kΩ负载；接QG时拆掉BO的临时负载。')
note(1026,'用10X高阻探头、短地弹簧；RF级短线相邻布置。OUT约2 Vpp是旧仿真对照，不是实物保证或课程门槛。')
c.showPage();c.save()
doc=fitz.open(O/'焊接原理图_基带与载波.pdf')
for i,p in enumerate(doc):p.get_pixmap(matrix=fitz.Matrix(1.35,1.35),alpha=False).save(O/f'0{i+1}_schematic.png')
print(O)
