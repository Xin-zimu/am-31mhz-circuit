from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
import fitz

O=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('CN',r'C:\Windows\Fonts\simsun.ttc',subfontIndex=0))
W,H=1600,1120
PAD=10
c=canvas.Canvas(str(O/'measurement_appendix.pdf'),pagesize=(W,H))
style=ParagraphStyle('p',fontName='CN',fontSize=22,leading=32,wordWrap='CJK',textColor=HexColor('#172638'))
cell=ParagraphStyle('cell',parent=style,fontSize=20,leading=28)
def txt(x,y,s,size=22,color='#172638'):
 c.setFont('CN',size);c.setFillColor(HexColor(color));c.drawString(x,H-y,s)
def para(y,s):
 p=Paragraph(escape(s),style);_,h=p.wrap(1475,900);p.drawOn(c,62,H-y-h);return y+h+15
def head(n,title,sub):
 c.setFillColor(HexColor('#112e43'));c.rect(0,H-145,W,145,fill=1,stroke=0)
 txt(55,69,f'{n:02d}   '+title,36,'#ffffff');txt(55,119,sub,20,'#d7e3ed')
 txt(55,1091,'31 MHz AM 项目 · 焊接与测量实验版 · 2026-11-17 · 数值待实物填写，不把仿真当实测',17,'#65788c')
 txt(1450,1091,f'{n} / 8',18)
def table(y,headers,rows,widths):
 content=[[Paragraph(escape(str(x)),cell) for x in row] for row in [headers]+rows]
 t=Table(content,colWidths=widths)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e4edf3')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.6,HexColor('#b9c8d2')),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),PAD),('BOTTOMPADDING',(0,0),(-1,-1),PAD)]))
 _,h=t.wrap(1480,950)
 assert y+h<1050,(y,h)
 t.drawOn(c,60,H-y-h);return y+h+22

head(4,'领料与上电准备','不含正面布局、背面连线和跳线端点表；照第1～3页原理图识别实际网络。')
y=table(180,['部分','本轮实际领料','说明'],[
 ['基带芯片/调节件','LM393P×1；DIP-8座×1；100 kΩ微调×1；10 kΩ电位器×1；20 kΩ电位器×1','100 kΩ作频率变阻器，先调约15.3 kΩ；20 kΩ用于幅度。'],
 ['基带固定电阻','10 kΩ×3；20 kΩ×2；22 kΩ×1；4.7 kΩ×1；1 kΩ×4；100 Ω×4','已把30 kΩ及两个2.2 kΩ按第1页串联组合拆成现有料，不要重复领原值。'],
 ['基带电容','1 nF C0G×1；100 nF×1；10 µF×1','100 nF已有0805，可短引脚转接并固定；10 µF为直插，注意极性。'],
 ['载波新增两级','2N3904BU×2；10 kΩ×2；22 kΩ×1；4.7 kΩ×1；330 Ω×1；56 Ω×1；1 kΩ×3','1 kΩ中两只组成OUT的2 kΩ测试负载；单测BO可暂时移用，接QG时移回OUT。'],
 ['载波新增电容','1 nF C0G×2；10 nF C0G×2；100 nF去耦×2；入口10 µF×1','原振荡板元件不计在本页；两级共板时入口10 µF一只，各级就近去耦。'],
 ['仪器与辅料','限流直流电源、万用表、DS2102E、10X探头与短地弹簧、已有晶体振荡板','基带和射频分板；晶体测试夹具与有源振荡板不是同一电路。'],
 ],[230,720,530])
y=para(y,'断电逐项查：芯片方向与脚号、三极管E/B/C、电解正负极、同名网络通断、相邻焊点锡桥。电源对地不能持续接近0 Ω；电容充电导致的短促蜂鸣不能单独判定短路。')
y=para(y,'所有本册模块先用实验室5.0 V供电，不直接接9 V电池。限流起点：基带10 mA；原R1板5 mA；缓冲单级10 mA；增益单级10 mA；三段载波链20 mA。限流掉压或异常发热时先断电排查。')
c.showPage()

head(5,'基带板：第一次上电与测量','对应第1、2页；目标是得到可重复调节的20 kHz方波，并记录三档占空比、四档幅度。')
y=180
for s in [
 '1. 插芯片前检查：DIP座8脚接+5 V，4脚接GND；两路2.2 kΩ上拉均已安装。断电插LM393P；将频率变阻器预调约15.3 kΩ，占空比电位器置中间附近，幅度滑端先靠GND一侧。',
 '2. 电源设5.0 V、限流10 mA。上电测芯片8脚对4脚电压、板输入电流；若供电跌落，先检查短路、芯片反插及限流状态，不先转所有电位器。',
 '3. 示波器探头与通道倍率都选10X，输入高阻（1 MΩ），DC耦合；地夹接GND。先测1脚TP_OSC：10 µs/div、1 V/div起步，边沿触发，触发电平放在波形中部。',
 '4. 调RVRF使1脚频率接近20 kHz，周期约50 µs。再看2脚RAMP，应为重复充放电斜坡，不必是直线三角波。若1脚恒高/恒低，查RC回路、迟滞网络和脚号。',
 '5. 探头移到7脚TP_PWM，转RVD，把占空比依次调至10%、30%、50%；每档记录频率、占空比和高低电平。若1脚正常而7脚不变，查6脚是否接RAMP、5脚滑端以及7脚上拉。',
 '6. 探头移到V1（RVA滑端），先保持50%占空比，再调1、2、3、4 Vpp；随后补测10%、30%下的四个幅度点，共12组。每次调幅后复查频率和占空比；上升沿、下降沿各留一张放大截图。',
 '7. 本轮V1只接高阻示波器。接入调制级后必须重新校准，不能把本次旋钮位置当作最终带载标定。低电平不要求恰为0 V；记录实际高、低平台，不只记Vpp。',
]: y=para(y,s)
y=table(y,['观察/指标','本轮判断口径'],[
 ['频率与占空比','尽量调至20 kHz及10/30/50%；课程频率1%对应19.8～20.2 kHz，占空比误差按百分点记录，超过5个百分点需处理。'],
 ['幅度与边沿','确认V1能覆盖1～4 Vpp，记录实际误差；本册不自设幅度容差。明显削顶、缺脉冲或无法调到目标要记录，不用“有方波”代替通过。'],
 ],[300,1180])
c.showPage()

head(6,'载波缓冲QB：先直流，再接振荡器','对应第3页左侧；不需要天线，也不需要先焊调制和末级驱动。')
y=180
for s in [
 '1. 先完成已有R1板的单独测试，记录TP1频率、观察幅度及供电电流。TP1经2.2 pF弱耦合，其Vpp不能当作振荡器E节点的真实幅度；普通探头不直接跨晶体脚。',
 '2. QB先与振荡板断开。5.0 V、限流10 mA供电，用万用表对GND测QB的B、E、C直流电压，确认偏置合理后再接信号。',
 '3. 断电后，从原振荡板的E节点经CIN=1 nF接QB基极，不能从原板TP1/SENSE取信号。两板GND可靠短接；QB输出经COUTB=1 nF成为BO。',
 '4. 在BO与GND间暂接2 kΩ测试负载（1 kΩ＋1 kΩ），QG先不连接。两级合用5 V时以15 mA限流起步；若限流导致电压下降，先查接线。',
 '5. 示波器10X、高阻输入、DC耦合，关闭20 MHz带宽限制。尖端接BO，短地弹簧接附近GND；10 ns/div、200 mV/div起步，幅度未知时再调档位。31 MHz周期约32.3 ns。',
 '6. 记录BO的频率、Vpp、波形和总电流。用相同TP1测法比较原振荡板接QB前后频率及起振情况；最好顺序测量，避免两支探头同时改变RF负载。',
 '7. 做5次断电再上电检查，每次待电源充分掉电后启动。记录成功次数及波形截图。若要量启动时间，需用电源上升沿触发、单次采集并保留足够长记录；不凭手动开关感觉估计。',
]:y=para(y,s)
y=table(y,['测点','粗略参考 / 怎样使用'],[
 ['QB：C / B / E 对地','C≈5 V；B约2.3～2.5 V；E约1.6～1.9 V。这是偏置排查参考，不是保证值；同时检查B比E高约0.6～0.8 V。'],
 ['BO：频率 / 幅度','频率应随原振荡板保持在31 MHz附近；射随缓冲不是电压放大级。实物幅度不设固定通过值，记录负载和探头条件后与级联结果比较。'],
 ['异常处理','不振荡：先恢复原板独立测试；BO无波形：查CIN/COUTB和QB脚序。不得直接以“幅度小”判晶体损坏。'],
 ],[330,1150])
c.showPage()

head(7,'载波增益QG：测工作点、幅度和加载影响','对应第3页右侧；本页的2 kΩ只是测试负载，不是课程强制负载。')
y=180
for s in [
 '1. QG先不接BO，单独5.0 V、限流10 mA供电。万用表测B、E、C对地；先排除反插、错阻值和短路。REG=56 Ω不加旁路电容。',
 '2. 断电，把BO经CG=10 nF接QG基极；前级COUTB=1 nF保留。拆掉BO的临时2 kΩ负载，将2 kΩ接到OUT对地。COUTG=10 nF保留，所有板共地。',
 '3. 振荡＋缓冲＋增益三段共同供5.0 V，限流20 mA起步。示波器尖端接OUT、短地弹簧接GND；10X、高阻、DC耦合、全带宽，10 ns/div、500 mV/div起步。',
 '4. 记录OUT频率、周期、Vpp、波形是否削顶、是否有低频包络摆动，以及三段总电流。再用较慢时基观察波形幅度是否持续起伏；保留原始采样或截图。',
 '5. 接QG后重新记录QB和QG的直流工作点；在同样探头条件下比较接入前后TP1频率。BO单独带2 kΩ时的幅度不能直接当作接QG后的输入幅度。',
 '6. 如需估算增益，先说明测的是哪个输入节点及探头负载。普通探头直接测QG基极会改变31 MHz输入；明天优先记录输出和稳定性，不为算增益强探高阻节点。',
 '7. 三段链做5次重复上电并记录启动成功次数。功耗按板上实测供电电压×电流计算，只代表这三段5 V电路，不是最终9 V电池端整机功耗。',
]:y=para(y,s)
y=table(y,['项目','参考、边界与异常处理'],[
 ['QG直流偏置','B约0.75～0.9 V，E约0.1～0.25 V，C约1～3.5 V，仅为粗查范围。若C贴近地/电源或B-E关系异常，先核对脚序和偏置网络。'],
 ['频率 / 幅度','31 MHz±1%对应30.69～31.31 MHz；短时测到此范围不代表温漂通过。2 kΩ下约2 Vpp是旧仿真参考，不是实物保证或课程独立验收门槛。'],
 ['失真 / 负载','若削顶或幅度异常，先核查是否误选50 Ω输入、负载是否重复、供电是否限流。不要把网表的探头等效10 pF再焊一只到OUT上。'],
 ],[330,1150])
c.showPage()

PAD=5
cell.fontSize=18
cell.leading=24
head(8,'实测记录：每块板都留下可比较的数据','填写日期、板号、供电、负载与探头条件；留空即未测，不预填仿真值。')
y=180
y=para(y,'日期：________  基带板号：________  RF板号：________  电源实测：________ V  探头型号/倍率：________________')
y=table(y,['占空比目标','V1目标/Vpp','频率/kHz','占空比/%','实测Vpp','VH / VL（V）','板电流/mA'],
 [[str(d)+'%',str(a),'','','','',''] for d in [10,30,50] for a in [1,2,3,4]],
 [190,190,190,190,190,310,220])
y=table(y,['配置','负载/测点','频率/MHz','Vpp','总电流/mA','启动成功/次数'],[
 ['原R1单独','TP1弱耦合','','','',' /5'],
 ['原R1＋QB','BO，2 kΩ','','','',' /5'],
 ['原R1＋QB＋QG','OUT，2 kΩ','','','',' /5'],
 ],[300,300,200,180,220,280])
y=para(y,'直流记录：QB：B_____ V / E_____ V / C_____ V；QG：B_____ V / E_____ V / C_____ V。')
y=para(y,'截图文件名/异常/更改的元件值：________________________________________________________________________')
c.showPage();c.save()

out=fitz.open()
out.insert_pdf(fitz.open(O/'焊接原理图_基带与载波.pdf'))
out.insert_pdf(fitz.open(O/'measurement_appendix.pdf'))
assert len(out)==8
for i in range(3):
 p=out[i];p.draw_rect(fitz.Rect(1430,1060,1590,1110),fill=(1,1,1),color=(1,1,1))
 p.insert_text((1450,1091),f'{i+1} / 8',fontsize=18,color=(.1,.15,.2))
out.save(O/'基带与载波_焊接测量图册_R1.pdf')
for i in range(3,8):out[i].get_pixmap(matrix=fitz.Matrix(1.1,1.1),alpha=False).save(O/f'{i+1:02d}_measurement.png')
print('8 pages generated')
