from pathlib import Path
import csv,json,hashlib
import fitz
ROOT=Path(__file__).resolve().parents[3]
HELPER=ROOT/'output/pdf/tx_complete_20261119/build.py'
exec(compile(HELPER.read_text(encoding='utf-8').split('# Full continuous baseband')[0],str(__file__),'exec'))
# Reuse the drawing language only; no TX generation code executes.
O=Path(__file__).resolve().parent
def coil_v(d,x,y,Y,label):
 m=(y+Y)/2;d.line(x,y,x,m-100)
 for i in range(4):
  yy=m-100+i*50;p=d.c.beginPath();p.moveTo(x,d.h-yy);p.curveTo(x+40,d.h-yy,x+40,d.h-yy-50,x,d.h-yy-50);d.c.drawPath(p)
 d.line(x,m+100,x,Y);d.text(x+42,m-8,label,22)
def diode(d,x,X,y,label):
 m=(x+X)/2;d.line(x,y,m-30,y);d.wire([(m-30,y-30),(m-30,y+30),(m+25,y),(m-30,y-30)])
 d.line(m+25,y-33,m+25,y+33);d.line(m+25,y,X,y)
 d.text(m-90,y-70,label,25);d.text(m-72,y+70,'A',23);d.text(m+35,y+70,'K / 色环',23)

d=Draw('module_select.pdf',2300,1400)
d.header('接收天线输入 + 双调谐选频','LSEL1/2采用Bourns 78FR47K-RC 470 nH；CFIX与微调并联。各回路须在实际有源级加载下调到31 MHz。')
d.text(55,210,'接收天线',25,BLUE);d.line(80,250,80,350,BLUE);d.line(80,250,45,215,BLUE);d.line(80,250,115,215,BLUE)
d.wire([(80,350),(80,500),(200,500)],BLUE);d.text(100,380,'JRF信号端 / RX_IN',22,BLUE)
d.ch(200,450,500,'CSEL 15 pF');d.line(450,500,1050,500,BLUE);d.dot(500,500);d.dot(750,500);d.dot(1000,500)
coil_v(d,500,500,1100,'LSEL1 470 nH');d.cv(750,500,1100,'CFIX1 27 pF');d.cv(1000,500,1100,'');d.arrow(960,850,1045,750)
d.text(1015,940,'CT1 2~18 pF',22);d.text(1015,980,'起调约11.09 pF',21)
d.ch(1050,1250,500,'CK 2.4 pF');d.line(1250,500,1850,500,BLUE);d.dot(1300,500);d.dot(1550,500);d.dot(1800,500)
coil_v(d,1300,500,1100,'LSEL2 470 nH');d.cv(1550,500,1100,'CFIX2 33 pF');d.cv(1800,500,1100,'');d.arrow(1760,850,1845,750)
d.text(1815,940,'CT2 2~18 pF',22);d.text(1815,980,'起调约12.38 pF',21)
d.ch(1850,2100,500,'COUT 11 pF');d.line(2100,500,2150,500,BLUE);d.dot(2150,500);d.rv(2150,500,1100,'')
d.text(1990,760,'RPORT 1 MΩ',22);d.text(2000,420,'PORT → CIN1',23,BLUE)
d.line(100,1100,2200,1100);d.ground(100,1100);d.text(130,1145,'JRF地端 / 接收机公共GND',23)
d.text(60,1210,'接收天线的型号/长度与安装尚未定型；此处完整给出馈点和地端，不把发射端90 cm地网直接当作接收天线规格。',23)
d.text(60,1255,'50 Ω仅是历史仿真的激励源内阻，不在天线输入口额外串/并焊50 Ω。CT1/2按Vishay BFC280905217候选实施。',23)
d.text(60,1300,'每回路1 pF布局预算及线圈RLOSS/CSELF是模型项，不另焊；470 nH实物有容差，固定电容可能需按实测单件选配。',23)
select=d.done()

d=Draw('module_rf.pdf',3200,1450)
d.header('两级射频放大 + 射随缓冲','三只管均为onsemi 2N3904BU：1=E、2=B、3=C。+9 V与公共地分别同网，禁止套用发射板5 V供电。')
d.line(350,250,3020,250,RED);d.text(350,220,'+9 V',26,RED)
d.text(55,465,'PORT输入',24,BLUE);d.line(80,480,80,510,BLUE);d.ch(80,400,510,'CIN1 1 nF');d.line(400,510,600,510,BLUE)
for x,name in [(450,'1'),(1250,'2'),(2250,'B')]:
 d.rv(x,250,510,'RBT'+name+(' 10 kΩ' if name=='B' else ' 22 kΩ'))
 d.rv(x,510,1100,'RBB'+name+(' 10 kΩ' if name=='B' else ' 4.7 kΩ'));d.dot(x,510)
for x,num in [(600,1),(1500,2)]:
 d.npn(x,510,'Q'+str(num));d.rv(x+75,250,420,'RC'+str(num)+' 1 kΩ');d.dot(x+75,420)
 d.rv(x+75,600,750,'REU'+str(num)+' 33 Ω')
 d.rv(x+75,750,1100,'REB'+str(num)+' 220 Ω',True);d.dot(x+75,750)
 d.line(x+75,750,x+300,750);d.cv(x+300,750,1100,'CEB'+str(num)+' 330 pF')
d.ch(675,1100,420,'CIN2 100 pF');d.wire([(1100,420),(1100,510),(1500,510)],BLUE)
d.ch(1575,2100,420,'CBUF 100 pF');d.wire([(2100,420),(2100,510),(2400,510)],BLUE)
d.npn(2400,510,'QBUF');d.line(2475,250,2475,420,RED);d.line(2475,600,2475,650);d.dot(2475,650)
d.rv(2475,650,1100,'REBUF 470 Ω');d.ch(2475,2900,650,'COBUF 1 nF');d.dot(2900,650)
d.text(2880,605,'RF → 检波',23,BLUE);d.rv(2900,650,1100,'RRF 1 kΩ')
d.line(350,1100,3050,1100);d.ground(350,1100)
d.line(500,1200,2800,1200,RED);d.text(500,1175,'+9 V 就地去耦',22,RED)
for x,label in [(600,'CDQ1 100 nF / Q1'),(1450,'CDQ2 100 nF / Q2'),(2300,'CDBUF 100 nF / QBUF')]:
 d.cv(x,1200,1340,label);d.ground(x,1340)
d.text(60,1415,'REU是未旁路33 Ω；CEB只跨下段220 Ω，不能把33 Ω也一起旁路。保持RF短线与连续、就近回地。',24)
rf=d.done()

d=Draw('module_detect.pdf',1700,1250)
d.header('BAT85包络检波 + 两级RC低通','BAT85阳极接RF输入，阴极（色环）朝DET；使用BAT85模型候选，不能把BAT85S当作同一器件。')
d.text(55,445,'RF输入',25,BLUE);d.line(80,470,80,510,BLUE);d.line(80,510,450,510,BLUE)
diode(d,450,850,510,'DDET BAT85');d.dot(850,510);d.line(850,510,1000,510);d.dot(1000,510)
d.text(860,470,'DET',24,BLUE)
d.rv(850,510,950,'RDET 4.7 kΩ',True);d.cv(1000,510,950,'CDET 100 pF')
d.rh(1000,1400,510,'RFILT 4.7 kΩ');d.line(1400,510,1530,510,BLUE);d.dot(1450,510)
d.cv(1450,510,950,'');d.text(1470,755,'CFILT',22);d.text(1470,795,'100 pF',22)
d.text(1380,455,'ENV_OUT',24,BLUE)
d.line(400,950,1590,950);d.ground(400,950)
d.text(60,1045,'RF节点到BAT85阳极用短连线；旧网表RCONNECT=0.1 Ω是连线等效，不另购0.1 Ω电阻。',23)
d.text(60,1095,'ENV_OUT（源网表名out）接下页CCOUP；这里是检波后的包络，不是最终放大输出V2。',23)
d.text(60,1145,'两只100 pF是实际检波/滤波电容，保留；不另装仿真的1 PΩ占位负载。',23)
det=d.done()

d=Draw('module_bb.pdf',2300,1450)
d.header('OPA197基带放大 + 3 V参考 + 最终输出','单电源9 V；默认RFB 430 kΩ / RG 10 kΩ，闭环增益44倍。输出含约3 V直流偏置，用Vpp测方波幅度。')
d.text(55,330,'ENV_OUT输入',24,BLUE);d.line(80,350,80,410,BLUE);d.ch(80,400,410,'CCOUP 100 nF');d.line(400,410,1300,410,BLUE);d.dot(550,410)
d.rv(550,410,950,'RBIAS 100 kΩ')
d.comp(1300,450,'U1',3,2,6);d.line(1520,450,1740,450);d.dot(1740,450)
d.line(1050,490,1300,490,BLUE);d.dot(1050,490);d.rv(1050,490,950,'RG 10 kΩ',True);d.dot(1050,670)
d.wire([(1740,450),(1740,670),(1500,670)]);d.rh(1050,1500,670,'RFB 430 kΩ')
d.rh(1740,2040,450,'ROUT 100 Ω');d.dot(2040,450);d.text(2020,415,'V2 / FINAL',26,PURPLE)
d.line(2040,450,2180,450,PURPLE);d.text(2005,530,'JOUT 1：信号',23);d.text(2005,575,'JOUT 2：GND',23)
d.wire([(1400,395),(1400,270),(1600,270)],RED);d.text(1415,250,'7脚 → +9 V',23,RED)
d.wire([(1400,505),(1400,585)]);d.ground(1400,585);d.text(1430,572,'4脚 → GND',23)
d.text(1460,845,'U1 = TI OPA197ID/IDR，SOIC-8',24)
d.text(1460,890,'1、5、8脚：NC，悬空不接。',23)
d.text(1460,935,'需SOIC-8直通转接板，逐脚通断核对。',23)
d.text(1460,980,'不能套用LM393或SOT-23-5的引脚。',23)
# Passive reference, no hidden ideal source.
d.text(80,720,'+9 V',24,RED);d.line(200,730,200,750,RED);d.rv(200,750,950,'RVT 20 kΩ');d.dot(200,950)
d.rv(200,950,1150,'RVB 10 kΩ');d.ground(200,1150)
d.line(200,950,1050,950,PURPLE);d.dot(450,950);d.dot(550,950);d.cv(450,950,1150,'CVREF 10 µF',True);d.ground(450,1150)
d.text(620,1010,'REF约3 V（RBIAS与RG的共同参考）',23,PURPLE)
d.text(620,1050,'REF不能接GND，CVREF正极朝REF。',23,PURPLE)
d.text(1450,1080,'+9 V / U1附近',23,RED);d.line(1450,1110,1960,1110,RED);d.cv(1500,1110,1250,'CDU1 100 nF');d.ground(1500,1250)
d.text(60,1325,'RFB=390 kΩ可作40倍对照；默认装430 kΩ。换件后复查削顶、窄脉冲和输入半幅比例，不能靠过冲凑4 Vpp。',23)
d.text(60,1370,'不焊仿真/仪器等效的RBBLOAD 1 MΩ和CLOAD 100 pF；实际示波器及输出线本身会加载。',23)
bb=d.done()

d=Draw('module_power.pdf',1800,1050)
d.header('接收机电源与接口','9 V稳压实验电源或实测合适的9 V电池；与发射端5 V供电区分。输入功耗与电压范围须实测。')
d.box(70,250,330,220,'#f1f6f9','#dce5ec');d.text(95,300,'JPOWER 两针输入',27)
d.text(95,365,'1：+9 V',25,RED);d.text(95,425,'2：GND',25)
d.line(400,358,1660,358,RED);d.line(400,418,500,418);d.line(500,418,500,760);d.ground(500,760)
d.text(600,300,'+9 V → Q1、Q2、QBUF、OPA197和RVT上端',25,RED)
d.cv(800,358,760,'CPWR 10 µF',True);d.ground(800,760)
d.cv(1250,358,760,'CPWRHF 100 nF');d.ground(1250,760)
d.text(70,860,'各有源器件旁仍各装100 nF：CDQ1、CDQ2、CDBUF、CDU1；入口电容不代替远端去耦。',24)
d.text(70,910,'JRF地端、JOUT地端、所有板地与电源负端共接；REF约3 V为内部参考，不接电源负端。',24)
d.text(70,960,'示波器测REF或输出时，地夹始终接公共GND；不能把地夹夹到REF节点。',24)
power=d.done()

out=fitz.open();p=out.new_page(width=7800,height=3700)
def place(doc,dst):p.show_pdf_page(fitz.Rect(dst),doc,0,keep_proportion=False)
place(select,(50,200,2350,1600));place(rf,(2600,200,5800,1650));place(det,(6100,200,7800,1450))
place(bb,(4550,2050,6850,3500));place(power,(100,2100,1900,3150))
a=Draw('overview_overlay.pdf',7800,3700)
a.text(55,70,'接收机完整原理图：天线输入 + 双调谐选频 + 两级RF放大 + 缓冲 + BAT85检波 + OPA197基带输出',48)
a.text(55,130,'RX R1 / 2026-11-19 | 当前470 nH / G44替代候选；全部模块展开；同名+9 V及GND共网；不是已验收的无线接收机。',29)
a.wire([(2200,700),(2450,700),(2450,710),(2680,710)],BLUE,4);a.dot(2200,700);a.text(2290,660,'PORT → CIN1',25,BLUE)
a.wire([(5500,850),(5940,850),(5940,710),(6180,710)],BLUE,4);a.dot(5500,850);a.text(5770,905,'RF → BAT85',25,BLUE)
a.wire([(7630,710),(7750,710),(7750,1850),(4370,1850),(4370,2460),(4630,2460)],PURPLE,4);a.dot(7630,710)
a.text(7050,1800,'ENV_OUT → CCOUP',28,PURPLE)
a.text(2200,2200,'接收链路接口',36)
a.text(2200,2280,'JRF：天线/射频测试输入及GND',30)
a.text(2200,2350,'JOUT：最终V2输出及GND',30)
a.text(2200,2420,'电源：+9 V；内部REF约3 V',30)
a.text(2200,2540,'检波色环朝DET；REF不是GND。',31,PURPLE)
a.text(2200,2650,'本图6页模块细节附后，元件标签与接线',28)
a.text(2200,2700,'端点可逐项对照，不依赖旧图的孔位。',28)
a.text(2200,2820,'接收天线尚待实际选型/安装测量；',28)
a.text(2200,2870,'不擅自加入50 Ω电阻或发射端匹配网络。',28)
a.text(100,3570,'G44 nominal仿真仅覆盖指定约9.60 mV峰值理想AM输入；实际天线、器件损耗、冷启动、6 m及端到端线性均需实测。',29)
a.text(100,3630,'OPA197必须核对SOIC-8转接板脚序；BAT85与BAT85S不能混用。电感/布局模型寄生和仪器等效负载不作为额外焊接元件。',29)
ov=a.done();p.show_pdf_page(p.rect,ov,0)
for doc in [select,rf,det,bb,power]:out.insert_pdf(doc)

d=Draw('connections.pdf',2400,1700)
d.header('接收机全链路接线、器件与验证边界','物理接线按本页核对；此图更新为470 nH + G44，不沿用旧132-17L / G22的元件值或机械孔位。')
rows=[('天线 → 选频','JRF信号端 → CSEL 15 pF；JRF地端 → GND。实物天线型号/长度尚未定。'),
('第一回路','TANK1 → LSEL1、CFIX1 27 pF、CT1微调，三者另一端均接GND。'),
('两回路耦合','TANK1 → CK 2.4 pF → TANK2。CT1/2仅是对地微调，不串到信号路上。'),
('第二回路','TANK2 → LSEL2、CFIX2 33 pF、CT2微调，各接GND；TANK2经COUT 11 pF输出PORT。'),
('选频 → RF','PORT经CIN1 1 nF接Q1基极；PORT另有RPORT 1 MΩ到地。'),
('RF级联','Q1集电极经CIN2 100 pF接Q2基极；Q2集电极经CBUF 100 pF接QBUF基极。'),
('缓冲 → 检波','QBUF发射极经COBUF 1 nF输出RF；RF保留1 kΩ到地，并短线接BAT85阳极。'),
('检波与滤波','BAT85色环阴极接DET；RDET/CDET对地；DET经RFILT到ENV_OUT，CFILT对地。'),
('检波 → 基带','ENV_OUT经CCOUP 100 nF到OPA197的3脚；该节点经RBIAS 100 kΩ到REF。'),
('运放反馈','2脚经RG 10 kΩ到REF；6脚经RFB 430 kΩ回2脚；6脚经ROUT 100 Ω输出V2。'),
('参考与电源','RVT 20 kΩ从9 V接REF；RVB 10 kΩ从REF接GND；CVREF 10 µF正极朝REF。'),
('U1 SOIC-8','3=IN+、2=IN-、7=+9 V、4=GND、6=OUT；1/5/8不连接。'),
('三极管','Q1/Q2/QBUF均按onsemi 2N3904BU：1=E、2=B、3=C；其他厂牌须查封装图。')]
for i,(s,t) in enumerate(rows):
 y=170+i*67;d.box(50,y,2300,67,'#f1f6f9' if i%2==0 else '#ffffff','#dce5ec');d.text(75,y+42,s,25);d.text(380,y+42,t,25)
d.text(60,1110,'起调：CFIX1 27 pF + CT1约11.09 pF；CFIX2 33 pF + CT2约12.38 pF。电感±10%时须按实测选配固定电容。',25)
d.text(60,1160,'470 nH：Bourns 78FR47K-RC；微调：Vishay BFC280905217；二极管：BAT85；运放：OPA197ID/IDR + 直通转接板。',25)
d.text(60,1210,'电阻均单件，不采用串并联拼值；RFB默认430 kΩ，390 kΩ仅为40倍对照档，改变后重新测量。',25)
d.text(60,1280,'测试顺序：9 V/偏置与REF → 带有源级负载的LC调谐 → 小信号RF → 检波 → 基带幅度/削顶 → 实际发射机联调。',25)
d.text(60,1330,'仪器用RP2200实体10X；示波器倍率菜单若保持1X，电压显示乘10。RF测量有探头加载，尽量在缓冲节点测。',25)
d.text(60,1380,'输入测试源的50 Ω、线圈RLOSS/CSELF、1 pF布局、OPA内部模型、1 PΩ占位、输出1 MΩ/100 pF仪器负载均不另焊。',25)
d.text(60,1450,'依据：replacement_20261118/bourns/netlists/G44_D50_source.cir；替代候选README/RESULTS；旧施工图的器件物理脚号。',24)
d.text(60,1500,'增补CPWRHF及四处100 nF为实物去耦，未声称旧仿真已覆盖布局/电源；此次只转绘接线，不新增电路仿真。',24)
d.text(60,1550,'未验收项：实际接收天线、带载调谐、BAT85实物、窄脉冲过载、冷启动、长时间稳定、无线6 m和端到端线性。',24)
d.text(60,1620,'本图不是可照抄孔位的万能板背面图；保持短线、公共地连续，先核对实际封装再落孔。',25)
out.insert_pdf(d.done())

# Reviewable physical netlist derived from the current circuit, not instrument sources/models.
src=ROOT/'simulation/v4_hardware/stage5_receiver/replacement_20261118/bourns/netlists/G44_D50_source.cir'
parts=[];inside=False
excluded={'RSOURCE','RCT1','RCT2','CTUNE1','CTUNE2','RLOSS1','RLOSS2','CSELF1','CSELF2','RCONNECT','RLOAD','RBBLOAD','CLOAD'}
for line in src.read_text(encoding='utf-8').splitlines():
 a=line.split()
 if not a:continue
 if a[0].lower()=='.subckt':inside=True;continue
 if a[0].lower()=='.ends':inside=False;continue
 if inside or a[0][0] in '*.+':continue
 k=a[0][0].upper();ref=a[0]
 if ref in excluded:continue
 if k in 'RCL':parts.append([ref,a[3],a[1],a[2]])
 elif k=='Q':parts.append([ref,a[4],*a[1:4]])
 elif ref=='XDET':parts.append(['DDET','BAT85 A,K','rf','det'])
 elif ref=='XOPA':parts.append(['U1','OPA197 SOIC8 3,2,7,4,6','bbin','neg','vcc','0','bbo'])
for i,fix,trim in [(1,'27p','11.09p'),(2,'33p','12.38p')]:
 parts.extend([[f'CFIX{i}',fix,f'tank{i}','0'],[f'CT{i}',f'2-18p init {trim}',f'tank{i}','0']])
for ref,val,nodes in [('CDQ1','100n',['vcc','0']),('CDQ2','100n',['vcc','0']),('CDBUF','100n',['vcc','0']),('CDU1','100n',['vcc','0']),('CPWR','10u',['vcc','0']),('CPWRHF','100n',['vcc','0']),('JRF','antenna/test input',['input','0']),('JPOWER','9V input',['vcc','0']),('JOUT','V2 output',['final','0'])]:parts.append([ref,val,*nodes])
for row in parts:
 if row[0].startswith('LSEL'):row[2:]=['tank'+row[0][-1],'0']
refs=[r[0] for r in parts];assert len(refs)==len(set(refs))
with (O/'physical_connections.tsv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['Reference','Value','Nodes(Q=C,B,E;D=A,K;U=3,2,7,4,6)']);w.writerows([r[0],r[1],','.join(r[2:])] for r in parts)
dest=O/'接收机全模块连接原理图_R1.pdf';out.save(dest,garbage=4,deflate=True)
check=fitz.open(dest);alltext='\n'.join(p.get_text() for p in check)
missing=[r for r in refs if r not in alltext];assert not missing,missing
for i,p in enumerate(check):
 scale=min(2400/p.rect.width,1600/p.rect.height);p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(O/f'preview_{i+1}.png')
report={'pages':len(check),'physical_parts':len(parts),'unique_refs':True,'all_refs_in_pdf':not missing,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source':'G44_D50_source.cir','gain':44,'supply':'9V','scope':'candidate wiring drawing, not hardware acceptance'}
(O/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(dest);print(json.dumps(report,ensure_ascii=False))
