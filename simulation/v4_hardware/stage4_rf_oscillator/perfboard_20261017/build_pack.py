"""Generate a consistent, explicitly experimental through-hole assembly pack.

Coordinates, BOM, routing and connectivity checks share this data source.
No existing oscillator simulation or project file is modified.
"""
from pathlib import Path
import json, math
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / 'output/pdf/c518062_perfboard_r1'
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('CN', r'C:\Windows\Fonts\simsun.ttc', subfontIndex=0))
PARTS = [
 dict(ref='X1', value='C518062 / 31 MHz', kind='crystal', pins={'1':('D4','GND'),'2':('D6','B')}, spec='HC-49S 两脚；脚距约 4.88 mm，轻微调整至 5.08 mm；不分极性'),
 dict(ref='Q1', value='onsemi 2N3904', kind='q', pins={'1 E':('F6','E'),'2 B':('F7','B'),'3 C':('F8','VCC')}, spec='TO-92 直插；只适用于此脚序；三脚向外整形成 2.54 mm 间距'),
 dict(ref='R1', value='10 kΩ', kind='r', pins={'1':('C7','B'),'2':('C10','VCC')}, spec='1% 金属膜，1/4 W；跨 3 格，7.62 mm'),
 dict(ref='R2', value='10 kΩ', kind='r', pins={'1':('B1','GND'),'2':('E1','B')}, spec='1% 金属膜，1/4 W；跨 3 格，7.62 mm'),
 dict(ref='R3', value='4.7 kΩ', kind='r', pins={'1':('K6','E'),'2':('K9','GND')}, spec='1% 金属膜，1/4 W；跨 3 格，7.62 mm'),
 dict(ref='C1', value='33 pF', kind='c', pins={'1':('H6','E'),'2':('H7','B')}, spec='C0G/NP0，±5% 或更好，≥25 V；脚距 2.54 mm；竖装本体宽≤5 mm、厚≤2 mm'),
 dict(ref='C2', value='33 pF', kind='c', pins={'1':('I5','E'),'2':('I6','GND')}, spec='C0G/NP0，±5% 或更好，≥25 V；脚距 2.54 mm；竖装本体宽≤5 mm、厚≤2 mm'),
 dict(ref='C3', value='100 nF', kind='c', pins={'1':('E9','VCC'),'2':('F9','GND')}, spec='X7R 陶瓷，≥16 V，直插；脚距 2.54 mm；竖装本体宽≤5 mm、厚≤2 mm'),
 dict(ref='C4', value='10 µF', kind='el', pins={'+':('B12','VCC'),'-':('D12','GND')}, spec='电解，≥16 V，外径≤5 mm；负极色带脚接 D12'),
 dict(ref='C5', value='2.2 pF', kind='c', pins={'1':('J5','E'),'2':('J4','SENSE')}, spec='C0G/NP0，±0.25 pF 或更好，≥25 V；竖装本体宽≤5 mm、厚≤2 mm；弱耦合取样'),
 dict(ref='J1', value='5 V 输入', kind='port', pins={'+':('A11','VCC'),'-':('A12','GND')}, spec='红/黑软线分别焊入，另做应力固定；不用大螺丝端子'),
 dict(ref='TP1', value='取样点', kind='tp', pins={'1':('K4','SENSE')}, spec='短测试针，不接长飞线；10X 探头尖接这里'),
 dict(ref='TPG', value='探头地', kind='tp', pins={'1':('K3','GND')}, spec='短地针；探头地弹簧接这里'),
]
# Every jumper is insulated except its two endpoints. Geometric crossings do not connect.
ROUTES = {
 'VCC': [('A11','B12'),('B12','C10'),('C10','E9'),('E9','F8')],
 'B': [('E1','D6'),('D6','F7'),('F7','H7'),('F7','C7')],
 'E': [('F6','H6'),('H6','I5'),('I5','J5'),('J5','K6')],
 'GND': [('A12','D12'),('D12','F9'),('F9','I6'),('I6','K9'),('I6','D4'),('D4','B1'),('I6','K3')],
 'SENSE': [('J4','K4')],
}
COLORS = {'VCC':'#c53531','GND':'#334155','B':'#146bb0','E':'#bd6a00','SENSE':'#8a36ad'}
WIRES=[]
for net, routes in ROUTES.items():
    for a,b in routes:
        WIRES.append(dict(ref=f'W{len(WIRES)+1:02}',net=net,a=a,b=b))

def validate():
    terminals={}
    for p in PARTS:
        for pin,(hole,net) in p['pins'].items():
            assert hole not in terminals, f'Two component leads in {hole}'
            assert hole[0] in 'ABCDEFGHIJKL' and 1<=int(hole[1:])<=14
            terminals[hole]=(net,p['ref'],pin)
    parent={h:h for h in terminals}
    def find(h):
        if parent[h]!=h: parent[h]=find(parent[h])
        return parent[h]
    for w in WIRES:
        a,b=w['a'],w['b']
        assert terminals[a][0]==terminals[b][0]==w['net']
        parent[find(a)]=find(b)
    for net in COLORS:
        assert len({find(h) for h,v in terminals.items() if v[0]==net})==1, net
    assert len({find(h) for h in terminals})==5
    # Independently specify intended schematic component terminals.
    wanted={'X1':['GND','B'],'Q1':['E','B','VCC'],'R1':['B','VCC'],
            'R2':['GND','B'],'R3':['E','GND'],'C1':['E','B'],'C2':['E','GND'],
            'C3':['VCC','GND'],'C4':['VCC','GND'],'C5':['E','SENSE'],
            'J1':['VCC','GND'],'TP1':['SENSE'],'TPG':['GND']}
    for p in PARTS: assert [x[1] for x in p['pins'].values()]==wanted[p['ref']]
    return {'component_count':len(PARTS),'jumper_count':len(WIRES),'net_count':5,
            'unique_component_holes':True,'all_expected_nets_connected':True,
            'no_cross_net_wire':True,'back_view_horizontal_mirror':True,
            'physical_build_tested':False,'transistor_variant_simulated':False,
            'crystal_parameters_qualified':False}

c=canvas.Canvas(str(OUT/'C518062_万能板实验图册_R1.pdf'),pagesize=(842,595))
c.setTitle('C518062 万能板实验图册 R1 - 2N3904 版本（待实测）')

def text(x,y,s,size=10,color='#172334'):
    c.setFillColor(HexColor(color));c.setFont('CN',size);c.drawString(x,y,s)
def line(x1,y1,x2,y2,color='#172334',width=1.2):
    c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.line(x1,y1,x2,y2)
def dot(x,y,color='#172334'):
    c.setFillColor(HexColor(color));c.circle(x,y,2.5,stroke=0,fill=1)
def rect(x,y,w,h,fill='#ffffff',stroke='#172334'):
    c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(stroke));c.setLineWidth(1);c.rect(x,y,w,h,fill=1,stroke=1)
def header(n,title,sub):
    rect(0,515,842,80,'#102b43','#102b43')
    text(30,555,title,22,'#ffffff');text(30,530,sub,10,'#d9e5ee')
    text(30,22,'C518062 · 独立振荡器实验版 R1 · 2026-10-17 · 未经实物验证',9,'#64748b')
    text(755,22,f'{n} / 6',10)
def finish():c.showPage()
def paragraphs(x,y,lines,size=11,step=21):
    for s in lines:text(x,y,s,size);y-=step
    return y
def ground(x,y):
    line(x,y,x,y-7)
    for d,w in [(7,12),(11,8),(15,4)]:line(x-w/2,y-d,x+w/2,y-d)
def res(x,y1,y2,label):
    mid=(y1+y2)/2;line(x,y1,x,mid+16);line(x,mid-16,x,y2)
    rect(x-6,mid-16,12,32);text(x+11,mid+2,label,10)
def cap(x,y1,y2,label):
    mid=(y1+y2)/2;line(x,y1,x,mid+4);line(x,mid-4,x,y2)
    line(x-10,mid+4,x+10,mid+4);line(x-10,mid-4,x+10,mid-4);text(x+15,mid,label,10)

header(1,'01  原理图：先认清五个网络','5 V Colpitts 实验电路；Q1 改为直插 2N3904，不能沿用 BFR93A 的验证结论。')
# Supply and ground rails.
line(90,440,520,440,COLORS['VCC'],2);text(90,455,'VCC = +5 V / J1+',12,COLORS['VCC'])
line(90,150,670,150,COLORS['GND'],2);ground(90,150);text(110,127,'GND / J1- / TPG',11)
line(160,340,430,340,COLORS['B'],2);text(160,359,'B：基极 / 晶体节点',11,COLORS['B'])
res(280,440,340,'R1 10 kΩ');res(280,340,150,'R2 10 kΩ');dot(280,340)
# Crystal symbol.
line(160,340,160,276);line(160,242,160,150)
line(145,276,175,276);rect(149,250,22,18,'#eef3f6');line(145,242,175,242)
text(65,259,'X1 C518062',11);text(65,241,'31 MHz',10)
# NPN transistor.
line(430,318,430,362);line(430,352,470,384);line(470,384,470,440,COLORS['VCC'])
line(430,328,470,290);line(470,290,470,240,COLORS['E']);
path=c.beginPath();path.moveTo(460,300);path.lineTo(449,304);path.lineTo(455,311);path.close();c.setFillColor(HexColor('#172334'));c.drawPath(path,fill=1,stroke=0)
text(485,354,'Q1 2N3904',12);text(485,336,'C=3 / B=2 / E=1',10)
text(474,405,'3 C',9);text(399,320,'2 B',9);text(474,278,'1 E',9)
line(470,240,710,240,COLORS['E'],2);dot(470,240);text(485,255,'E：发射极节点',11,COLORS['E'])
res(470,240,150,'R3 4.7 kΩ')
# Label-connected B avoids ambiguous crossing through transistor symbol.
text(620,365,'B（与左侧 B 相连）',10,COLORS['B']);dot(620,340,COLORS['B'])
cap(620,340,240,'C1 33 pF');cap(620,240,150,'C2 33 pF');dot(620,240)
line(710,240,728,240);line(728,230,728,250);line(736,230,736,250);line(736,240,787,240,COLORS['SENSE']);dot(787,240,COLORS['SENSE'])
text(713,268,'C5 2.2 pF',10);text(722,217,'TP1 / SENSE',10,COLORS['SENSE'])
# Supply decoupling separate named rail.
line(610,440,772,440,COLORS['VCC']);text(610,455,'VCC',10,COLORS['VCC'])
cap(635,440,390,'C3');cap(750,440,390,'C4');ground(635,390);ground(750,390)
text(608,480,'C3 = 100 nF；C4 = 10 µF',10);text(765,420,'+',12)
paragraphs(38,100,[
 'C1、C2、C5：C0G/NP0。C4：正极接 VCC，负极接 GND；晶体两脚不分极性。',
 'TP1 是弱耦合观察点：可观察有无振荡、频率和包络变化，读到的 Vpp 不是 E 点或晶体的真实 Vpp。',
 '不要额外安装模型中的 C0、Cm、Lm、Rm 或 1 pF 寄生电容；它们是晶体/布线的等效描述。'],10,19)
finish()

header(2,'02  元件清单与插孔表','只适用于本册 R1；不要把旧 BOM 中的 S9013 直接按 Q1 孔位替换。')
ys=478
for title,x in [('位号',30),('规格 / 数量均为 1',77),('引脚 → 孔号',255),('备注',480)]:text(x,ys,title,11)
ys-=14;line(30,ys,810,ys,'#cbd5e1')
for p in PARTS:
    ys-=27
    text(30,ys,p['ref'],10);text(77,ys,p['value'],10)
    mapping='；'.join(f'{pin}→{h}' for pin,(h,n) in p['pins'].items())
    text(255,ys,mapping,9)
    short={'X1':'型号 49S-31.000-18-10-10/B；CL 标称 18 pF',
           'Q1':'厂商手册：1=E、2=B、3=C；按脚序插入',
           'R1':'1% / 1/4 W；脚距 7.62 mm','R2':'1% / 1/4 W；脚距 7.62 mm','R3':'1% / 1/4 W；脚距 7.62 mm',
           'C1':'C0G/NP0 / ≥25 V / 2.54 mm 脚距','C2':'C0G/NP0 / ≥25 V / 2.54 mm 脚距',
           'C3':'X7R / ≥16 V / 2.54 mm 脚距','C4':'≥16 V；外径≤5 mm；负极色带接 D12',
           'C5':'C0G/NP0；2.54 mm 脚距；仅用于取样',
           'J1':'红线 A11；黑线 A12；线材另做固定','TP1':'短针；探头尖接这里','TPG':'短地针；探头地弹簧接这里'}
    text(480,ys,short[p['ref']],9)
paragraphs(30,95,[
 '辅料：单面独立焊盘板（2.54 mm，至少 14 列×12 行）、细绝缘镀锡铜线、焊锡、助焊剂。',
 '准备万用表检查通断。电阻可用 1/8 W 小体积规格；电容若脚距不同，不要硬插或改孔位。',
 '晶体约 4.88 mm 脚距轻微调整至两格；Q1 引脚整形时扶住根部，不在塑封出口处用力折弯。'],10,19)
finish()

def xy(h,back=False):
    col=int(h[1:]);row=ord(h[0])-65
    return 66+(14-col if back else col-1)*27,452-row*27
def board(back=False):
    rect(48,136,390,335,'#edf5ef','#7a9d84')
    for col in range(1,15):
        x,y=xy('A'+str(col),back);text(x-4,483,str(col),10)
    for row in 'ABCDEFGHIJKL':
        x,y=xy(row+'1',back);text(28,y-3,row,11);text(448,y-3,row,11)
        for col in range(1,15):
            x,y=xy(row+str(col),back)
            c.setStrokeColor(HexColor('#b78b49'));c.setFillColor(white);c.setLineWidth(1)
            c.circle(x,y,4.3,fill=1,stroke=1)
    x,y=xy('A1',back);c.setStrokeColor(HexColor('#dc2626'));c.setLineWidth(2);c.circle(x,y,9,stroke=1,fill=0)
    text(x-15,y+15,'A1',9,'#dc2626')

header(3,'03  正面布局：从元件面往下看','列号从左到右 1→14；行号从上到下 A→L。孔距 2.54 mm；本图放大，不是 1:1 模板。')
board()
for p in PARTS:
    coords=[xy(h) for h,n in p['pins'].values()]
    if p['kind']=='q':
        x,y=coords[1];rect(x-24,y-18,48,38,'#273443','#273443')
        text(x-20,y+7,'Q1',9,'#ffffff')
        for (px,py),lab in zip(coords,['E','B','C']):text(px-3,py-29,lab,9)
    elif len(coords)==2 and p['kind']!='port':
        (x1,y1),(x2,y2)=coords;line(x1,y1,x2,y2,'#475569',2)
        mx,my=(x1+x2)/2,(y1+y2)/2
        if p['kind']=='crystal':rect(mx-58,my-24,116,48,'#d5dce1');text(mx-32,my+7,'X1 31 MHz',10)
        elif p['kind']=='r':
            horizontal=y1==y2
            rect(mx-(22 if horizontal else 8),my-(8 if horizontal else 22),44 if horizontal else 16,16 if horizontal else 44,'#dce9f6')
            text(mx-6,my-3,p['ref'],8)
        elif p['kind']=='el':
            c.setFillColor(HexColor('#dfe5ea'));c.setStrokeColor(HexColor('#475569'));c.circle(mx,my,24,stroke=1,fill=1)
            text(mx-8,my-3,'C4',9);text(x1+7,y1+2,'+',10);text(x2+7,y2-2,'-',10)
        else:
            c.setFillColor(HexColor('#e8c88b'));c.setStrokeColor(HexColor('#8d6a32'));c.rect(mx-23,my-6,46,12,stroke=1,fill=1)
            text(mx+25,my+3,p['ref'],9)
    else:
        for (pin,(h,n)),(x,y) in zip(p['pins'].items(),coords):
            dot(x,y,COLORS[n]);text(x-10,y-15,p['ref']+('+' if pin=='+' else '-' if pin=='-' else ''),8)
    for x,y in coords:
        c.setFillColor(HexColor('#172334'));c.circle(x,y,2.3,fill=1,stroke=0)
paragraphs(483,474,[
 '先在实物元件面标出 A1 红点。',
 'Q1 的 E/B/C 分别插入 F6/F7/F8。',
 '以厂家引脚定义为准，不凭外观猜脚序。',
 '图中 Q1 平直边朝向 G 行一侧。',
 'X1 两脚：D4、D6；外壳悬空不另接线。',
 'C4 正极 B12；负极 D12。',
 '',
 '小电容竖装，本体宽≤5 mm、厚≤2 mm。',
 '插孔以第 2 页表格为准。',
 '本板为单面焊盘：正面无需焊接。',
 '背面焊引脚，并按第 4、5 页接跳线。',
 '',
 '不要用长插座插晶体或 Q1。',
 '晶体外壳别碰到其他裸引脚。',
 'Q1 三脚展开后保留绝缘间隙。'],11,22)
paragraphs(30,104,[
 '实际孔阵列覆盖 33.02 × 27.94 mm，板边另留余量；若现有板更大，只使用这个角落。',
 '晶体约 11 × 5 mm；小电容竖装，宽≤5 mm、厚≤2 mm；Q1 与 C1 之间留一空行。',
 '先完成所有焊接和断电通断检查，再接 5 V。此图没有任何“孔与孔自动相连”的假设。'],10,19)
finish()

header(4,'04  背面连线：翻到焊接面后的实际视角','像翻书一样左右翻板，上边仍是 A 行；因此列号从左到右 14→1。不要再自行镜像。')
board(True)
for w in WIRES:
    x1,y1=xy(w['a'],True);x2,y2=xy(w['b'],True)
    # White halo distinguishes separate insulated conductors at projected crossings.
    line(x1,y1,x2,y2,'#ffffff',5)
    line(x1,y1,x2,y2,COLORS[w['net']],2.1)
for p in PARTS:
    for hole,net in p['pins'].values():
        x,y=xy(hole,True);dot(x,y,COLORS[net])
for h in ['F6','F7','F8','K3','K4','A11','A12']:
    x,y=xy(h,True);text(x+5,y+5,h,8)
paragraphs(483,474,[
 '红圈 A1 已移到右上角。',
 '每根线的起止孔见下一页。',
 '图上交叉处不代表电气连接！',
 '全部跳线用绝缘线，只剥两端。',
 '中途经过的铜环不焊、不剥皮。',
 '',
 '红色 VCC：+5 V 与集电极',
 '蓝色 B：基极与晶体端',
 '橙色 E：发射极与反馈端',
 '深灰 GND：公共地',
 '紫色 SENSE：弱耦合取样端',
 '',
 'RF 连线贴近板底；不要绕大圈。',
 '重叠处有绝缘层，轻微错开即可。',
 '同一孔多条线：焊在该引脚根部，',
 '不强塞多根线穿过一个小孔。'],11,21)
paragraphs(30,104,[
 '如需拆换元件，先断电。所有坐标沿用正面命名：背面的 F6 仍是同一个物理孔 F6。',
 '接地也按端点表短接；不同 GND 焊盘不会因涂成相同颜色而自动相通。',
 '此图只保证连接定义一致；万能板寄生、晶体实际参数及探头负载仍需实测验证。'],10,19)
finish()

header(5,'05  跳线端点表：逐根焊、逐根检查','全部 20 根跳线；只连接列出的端点。跨线保持绝缘，端点同孔才相连。')
for i,w in enumerate(WIRES):
    col=i//10;row=i%10;x=35+col*398;y=470-row*32
    text(x,y,w['ref'],12,COLORS[w['net']]);text(x+48,y,f"{w['a']}  →  {w['b']}",12)
    text(x+200,y,w['net'],11,COLORS[w['net']])
paragraphs(35,119,[
 '建议顺序：先装元件并剪脚，再接 GND、VCC，最后接 B、E 和 SENSE；每完成一组即核对。',
 '用断电电阻/通断挡检查每根线的两端接近 0 Ω。VCC 与 GND 不应持续接近 0 Ω。',
 'C4 充电会让阻值读数变化；不能仅凭短促蜂鸣判断短路。检查焊盘间是否有意外锡桥。',
 'B 与 GND 之间有 R2 和晶体：不是短路网。E 与 GND 之间有 R3：也不是短路网。'],11,21)
finish()

header(6,'06  第一次上电与测量','先查焊接，再看直流，最后观察波形；本册不是已验收的 31 MHz 标准信号源。')
paragraphs(35,476,[
 '1. 断电检查：X1、Q1 和 C4 极性/脚序；逐根对照第 5 页；确认电源没有持续短路。',
 '2. 电源先设 5.0 V、限流 5 mA，再接 J1。若进入恒流、供电明显掉压或元件发热，立即断电。',
 '   限流只是保护接错线；它不限制晶体激励功率，也不证明晶体在允许耗散内。',
 '3. 用万用表以 GND 为参考检查直流：Q1 集电极应接近 5 V；基极约 2.5 V；',
 '   发射极通常比基极低约 0.6~0.8 V。这是粗查偏置，不是实测承诺或验收限值。',
 '4. DS2102E 探头选 10X，通道倍率也选 10X；输入设 1 MΩ，不选 50 Ω。',
 '   探头尖接 K4（TP1），短地弹簧接 K3（TPG）。不要夹到晶体脚或电源正端。',
 '5. 通道 DC 耦合、关闭 20 MHz 带宽限制；先用 10 ns/div、20~50 mV/div，边沿触发。',
 '   31 MHz 一个周期约 32.3 ns。幅度未知，可逐步调垂直档与触发电平，不保证固定档能触发。',
 '6. 先记录有没有稳定周期波形、粗略频率及 5 V 供电电流；随后再做重复断电启动测试。',
 '   20 MHz 带宽限制或探头负载可能让波形变小；不要因此直接判断晶体损坏。',
 '7. TP1 经 2.2 pF 耦合，波形幅度取决于探头电容、输入电阻及寄生，不能直接当振荡器 Vpp。',
 '   测晶体激励功率还需进一步的射频测量；电源端 V×I 只是本板总功耗。',
 '',
 '验证边界：已检查元件表、孔位、跳线和原理图的网络一致性；尚未对本 2N3904 版本做',
 '电路仿真或实物验证。C518062 的 Rm/Cm/C0/工作模式及允许激励仍未闭合，可能需要调试。',
 '原 BFR93A 模型的频率、幅度、耗电数值不能用于本板；未连接发射机主工程。',
 '',
 '引脚依据：onsemi《2N3904/D》，2024-10 Rev.3，第 1 页：1=E、2=B、3=C。',
 'https://www.onsemi.com/download/data-sheet/pdf/2n3904-d.pdf',
 '示波器依据：RIGOL DS2000E 系列规格书；DS2102E 为 100 MHz 双通道示波器。'],11,20)
finish();c.save()

result=validate()
for row in 'ABCDEFGHIJKL':
    for col in range(1,15):
        a=xy(row+str(col)); b=xy(row+str(col),True)
        assert a[0]+b[0]==483 and a[1]==b[1]
result['mirror_holes_checked']=168
(HERE/'connectivity_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'assembly_data.json').write_text(json.dumps({'parts':PARTS,'jumpers':WIRES},ensure_ascii=False,indent=2),encoding='utf-8')
md=['# C518062 万能板实验版 R1','',
    '本版使用 onsemi 2N3904 TO-92，未做该版本仿真或实物验证。不可沿用旧 BFR93A 仿真结论。',
    'C518062 晶体参数尚未闭合；本资料是待调试实验电路，不是保证起振/频率/功耗的验收设计。','',
    '## 元件及孔位','', '| 位号 | 值 | 引脚、孔位、网络 | 要求 |','|---|---|---|---|']
for p in PARTS:
    pins='；'.join(f'{pin}: {h} ({net})' for pin,(h,net) in p['pins'].items())
    md.append(f"| {p['ref']} | {p['value']} | {pins} | {p['spec']} |")
md += ['', '## 焊接跳线','', '单面独立焊盘，2.54 mm，14 列×12 行。所有跳线绝缘，仅两端焊接。背面左右镜像，坐标不重新命名。','', '| 编号 | 网络 | 起点 | 终点 |','|---|---|---|---|']
for w in WIRES:md.append(f"| {w['ref']} | {w['net']} | {w['a']} | {w['b']} |")
md += ['', '## 设计说明','',
       '- Q1 换成直插器件是本版的工程选择，未把 S9013 或 BFR93A 视作等效替换。',
       '- R1/R2=10k，R3=4.7k，反馈电容33pF沿用原独立模型的起始值，仍需对新晶体管验证。',
       '- 不把 CL=18pF 当作需要额外跨接晶体的18pF电容。模型寄生1pF也不是本板实装元件。',
       '- C3/C4 是电源去耦；C5=2.2pF提供弱耦合取样，不是输出缓冲。',
       '- 示波器用10X、1MΩ、短地弹簧。TP1振幅不可当作晶体或发射极振幅；普通示波器测频也不自动具备ppm准确度。',
       '- 第一次电源5V/限流5mA；本板总功耗用实际电压×电流估算，不含后续稳压或全发射机。',
       '- 未检验真实器件的体积公差；若电容脚距或电解直径超出表内要求，需要先改版，不能硬挤。',
       '- 主工程、供应商邮件草稿均未修改。','',
       '## 来源','',
       '- https://www.onsemi.com/download/data-sheet/pdf/2n3904-d.pdf',
       '- https://beyondmeasure.rigoltech.com/acton/attachment/1579/f-0790/1/-/-/-/-/DS2000E_DataSheet_EN.pdf','',
       '生成源：build_pack.py。assembly_data.json 为孔位及跳线数据；connectivity_check.json 为网络检查结果。']
(HERE/'README_元件与接线.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(OUT)
print(json.dumps(result,ensure_ascii=False))
