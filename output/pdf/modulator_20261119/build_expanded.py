from pathlib import Path
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
O=Path(__file__).resolve().parent
ROOT=O.parents[2]
pdfmetrics.registerFont(TTFont('CN',r'C:\Windows\Fonts\msyh.ttc',subfontIndex=0))
rf=fitz.open(ROOT/'output/pdf/carrier_merged_20261118/C518062_载波三级拼接原理图_R1.pdf')
bb=fitz.open(ROOT/'output/pdf/tomorrow_schematics_20261117/焊接原理图_基带与载波.pdf')
mod=fitz.open(O/'基极调制级_焊接原理图与接线表_R1.pdf')
# Local in-memory RF copy: remove only the temporary output load, retaining COUTG and OUT.
rp=rf[0];sx=rp.rect.width/2400;sy=rp.rect.height/1550
def rr(a):return fitz.Rect(a[0]*sx,a[1]*sy,a[2]*sx,a[3]*sy)
for a in [(2200,525,2270,918),(2080,730,2210,830),(1700,980,2315,1055),(2150,540,2330,630),(55,1330,2320,1375)]:
 rp.add_redact_annot(rr(a),fill=(1,1,1))
rp.apply_redactions()
rp.insert_text((2160*sx,580*sy),'OUT / TP_OUT',fontsize=10,color=(.5,.25,.65))
rp.insert_text((65*sx,1360*sy),'COUTB and CG retained. Remove temporary loads at BO and OUT for modulator connection.',fontsize=9,color=(.08,.42,.69))
for p in bb:
 p.add_redact_annot(fitz.Rect(45,950,1570,1050),fill=(1,1,1))
 p.apply_redactions()
# Complete the original PWM sheet's DUTY wire: wiper endpoint to U1B non-inverting input.
p=bb[1];shape=p.new_shape()
shape.draw_polyline([fitz.Point(580,555),fitz.Point(600,555),fitz.Point(600,460),fitz.Point(630,460)])
shape.finish(color=(.08,.42,.69),width=2,closePath=False);shape.commit()
out=fitz.open();page=out.new_page(width=4200,height=2600)
def place(doc,n,src,dst,logical=None):
 p=doc[n]
 clip=fitz.Rect(src)
 if logical:clip=fitz.Rect(src[0]*p.rect.width/logical[0],src[1]*p.rect.height/logical[1],src[2]*p.rect.width/logical[0],src[3]*p.rect.height/logical[1])
 page.show_pdf_page(fitz.Rect(dst),doc,n,clip=clip,keep_proportion=False)
place(rf,0,(50,170,2340,1260),(50,180,2340,1270),(2400,1550))
place(mod,0,(50,160,1550,970),(2500,200,4000,1010))
place(bb,0,(50,175,1550,960),(50,1420,1550,2205))
place(bb,1,(50,175,1550,960),(1700,1420,3200,2205))
# Overlay at the same coordinate scale for visible cross-module wires and notes.
tmp=O/'expanded_overlay.pdf';c=canvas.Canvas(str(tmp),pagesize=(4200,2600))
def text(x,y,s,size=28,col='#172d41'):
 c.setFont('CN',size);c.setFillColor(HexColor(col));c.drawString(x,2600-y,s)
def wire(points,col):
 c.setStrokeColor(HexColor(col));c.setLineWidth(4)
 p=c.beginPath();p.moveTo(points[0][0],2600-points[0][1])
 for x,y in points[1:]:p.lineTo(x,2600-y)
 c.drawPath(p)
def dot(x,y,col):
 c.setFillColor(HexColor(col));c.circle(x,2600-y,6,fill=1,stroke=0)
def cap(x,y,label,polar=False):
 wire([(x,y),(x,y+30)],'#c43c36');wire([(x-20,y+30),(x+20,y+30)],'#172d41')
 wire([(x-20,y+45),(x+20,y+45)],'#172d41');wire([(x,y+45),(x,y+80)],'#172d41')
 for d,k in [(15,0),(10,7),(4,14)]:wire([(x-d,y+80+k),(x+d,y+80+k)],'#172d41')
 text(x+30,y+46,label,22)
 if polar:text(x+25,y+21,'+',21,'#c43c36')
text(55,65,'完整联调原理图：三级载波 + LM393 基带 + 基极调制',49)
text(55,113,'RF_IN、BB_IN 已展开为完整前级；同名 +5 V、GND、OSC、RAMP、DUTY 分别相连。拱桥跨线不相连。',27)
text(2550,175,'调制级（保留原模型元件值）',31)
wire([(2240,430),(2430,430),(2430,265),(2540,265)],'#146fa5');dot(2240,430,'#146fa5')
text(2260,480,'OUT → RF_IN',23,'#146fa5')
text(2080,795,'OUT 的临时',25);text(2080,833,'2 kΩ 不装',25)
wire([(3160,1895),(3350,1895),(3350,1130),(2460,1130),(2460,795),(2540,795)],'#8240a5')
dot(3160,1895,'#8240a5');text(3375,1770,'V1 → BB_IN',27,'#8240a5')
text(60,1380,'基带A：振荡器（U1A）',32);text(1710,1380,'基带B：占空比 + 幅度（U1B）',32)
text(650,2245,'RAMP = U1 的2脚/6脚；两处 RAMP 必须短接。OSC = U1 的1脚。',25,'#146fa5')
text(1710,2290,'U1A、U1B 是同一颗 LM393P，不是两颗芯片。',26)
text(3375,1370,'调制板就地去耦',28)
wire([(3420,1420),(3970,1420)],'#c43c36');text(3420,1400,'+5 V',24,'#c43c36')
cap(3450,1420,'CDM 100 nF');cap(3780,1420,'CBM 10 µF',True)
text(3375,1585,'GND 与所有前级板共地。',25)
text(3375,1630,'全部模块使用 +5 V。',25)
text(70,2350,'装配状态：原载波板保留晶体、Q1、QB、QG及原去耦；BO无临时负载；TP3的1 kΩ保留。',29)
text(70,2400,'接口待核：先确认探头实体/通道倍率，再决定2.2 kΩ / 10 Ω衰减支路；本图不擅自调整该支路。',29,'#a55613')
text(70,2450,'RMINJ标称37 kΩ；用36 kΩ时记录替代并实测校准。联调图不包含后续驱动级和天线。',27)
text(70,2515,'2026-11-19 | R2 完整展开版 | 总图可放大；后附模块原尺寸细节及接线/测试表 | 尚未完成整体实物验证',25,'#607486')
c.save();overlay=fitz.open(tmp);page.show_pdf_page(page.rect,overlay,0)
# Detail pages retain full original component information.
out.insert_pdf(rf,from_page=0,to_page=0)
out.insert_pdf(bb,from_page=0,to_page=1)
out.insert_pdf(mod,from_page=0,to_page=2)
# Clarify the modified RF detail page; original carrier footer is left as source revision.
detail=out[1]
detail.insert_textbox(rr((1690,980,2320,1055)), 'OUT temporary 2k load removed. Connect OUT to RMRF 2.2k.',fontsize=9,fontname='helv',color=(.08,.42,.69))
dest=O/'载波_基带_调制_完整展开原理图_R2.pdf'
out.save(dest,garbage=4,deflate=True)
check=fitz.open(dest)
for i in [0,1,2,3]:
 p=check[i];scale=min(2200/p.rect.width,1500/p.rect.height)
 p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(O/f'expanded_preview_{i+1}.png')
print(dest)
print('pages',len(check))
