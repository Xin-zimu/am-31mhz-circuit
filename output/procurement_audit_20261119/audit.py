from pathlib import Path
import csv,json,re,hashlib
from collections import defaultdict,Counter
import openpyxl
O=Path(__file__).resolve().parent;ROOT=O.parents[1]
SRC=ROOT/'项目管理/05_元器件总表_20261119.xlsx'
w=openpyxl.load_workbook(SRC,data_only=True)
inventory=[{'excel_row':i,'id':r[0],'category':r[1],'name':r[2],'model':r[3],'brand':r[4],'spec':r[5],'use':r[7],'need_old':r[8],'stock':r[9],'status':r[11],'note':r[17]} for i,r in enumerate(w['01_元器件总表'].iter_rows(values_only=True),1) if i>=4 and isinstance(r[0],int)]
cart=[{'row':i,'id':r[0],'category':r[1],'name':r[2],'spec':r[3],'shop':r[4],'packs':r[5],'use':r[8],'note':r[9]} for i,r in enumerate(w['02_购物车未付款'].iter_rows(values_only=True),1) if i>=4 and isinstance(r[0],int)]
def value(s):
 m=re.match(r'([\d.]+)\s*(meg|[kpnµu]?)',s,re.I);assert m,s
 return float(m[1])*{'':1,'k':1e3,'meg':1e6,'p':1e-12,'n':1e-9,'u':1e-6,'µ':1e-6}[m[2].lower()]
def pretty(v):
 for mult,s in [(1e6,'MΩ'),(1e3,'kΩ'),(1,'Ω')]:
  if v>=mult:return f'{v/mult:g} {s}'
def cpretty(v):
 for mult,s in [(1e-6,'µF'),(1e-9,'nF'),(1e-12,'pF')]:
  if v>=mult*.999:return f'{v/mult:g} {s}'
def numeric_key(k,v):return (k,round(v,15) if k=='C' else v)
groups={};details=[]
for side,filename in [('TX','output/pdf/tx_complete_20261119/physical_connections.tsv'),('RX','output/pdf/rx_complete_20261119/physical_connections.tsv')]:
 for row in csv.DictReader((ROOT/filename).open(encoding='utf-8-sig'),delimiter='\t'):
  ref=row['Reference'];val=row['Value'];nodes=list(row.values())[2];key=None;cat='';name=''
  if ref in ['RVRF','RVD','RVA']:
   pval={'RVRF':100000,'RVD':10000,'RVA':20000}[ref];key=('POT',pval);cat='电位器';name=pretty(pval)+' 三端微调/电位器'
  elif ref.startswith('R'):
   v=value(val);v={1250:1200,37000:36000,40000:39000}.get(v,v);key=numeric_key('R',v);cat='电阻';name=pretty(v)
  elif ref in ['CTUNE','CT1','CT2']:
   key=('TRIM','CCW12');cat='微调电容';name='CCW12 3.5–20 pF（当前采购替代）'
  elif ref.startswith('C'):
   v=value(val);key=numeric_key('C',v);cat='电容';name=cpretty(v)
  elif ref.startswith('Q'):key=('Q','2N3904');cat='三极管';name='2N3904（原图onsemi BU）'
  elif ref=='X1':key=('X','31M');cat='晶体';name='C518062 31 MHz'
  elif ref=='U1':key=('U','LM393P' if side=='TX' else 'OPA197IDR');cat='IC';name=key[1]
  elif ref=='DDET':key=('D','BAT85S-TR');cat='二极管';name='现有Vishay BAT85S-TR（检波实测候选）'
  elif ref=='LFIX':key=('L','1812CS-392');cat='电感';name='1812CS-392 3.9 µH'
  elif ref.startswith('LSEL'):key=('L','78FR47K-RC');cat='电感';name='78FR47K-RC 470 nH'
  elif ref=='ANT' or ref.startswith('J'):continue
  else:raise ValueError(row)
  g=groups.setdefault(key,{'key':str(key),'category':cat,'name':name,'tx':0,'rx':0,'refs':[],'stock':0,'cart':0,'source':[],'note':''})
  g[side.lower()]+=1;g['refs'].append(side+':'+ref);details.append([side,ref,val,name,nodes])

# Match stock rows by explicit stable inventory IDs; these counts include previously assembled parts.
stock_map={17:('R',33.),18:('R',56.),19:('R',100.),20:('R',220.),21:('R',330.),22:('R',470.),23:('R',1000.),24:('R',4700.),25:('R',10000.),26:('R',20000.),27:('R',22000.),28:('R',100000.),30:('R',1e6),46:numeric_key('C',2.2e-12),47:numeric_key('C',15e-12),49:numeric_key('C',33e-12),51:numeric_key('C',100e-12),52:numeric_key('C',330e-12),53:numeric_key('C',1e-9),55:numeric_key('C',10e-9),56:numeric_key('C',10e-9),57:numeric_key('C',100e-9),58:numeric_key('C',100e-9),59:numeric_key('C',10e-6),4:('Q','2N3904'),7:('U','LM393P'),12:('U','OPA197IDR'),14:('D','BAT85S-TR'),1:('X','31M'),75:('POT',10000),76:('POT',100000)}
for r in inventory:
 key=stock_map.get(r['id'])
 if key in groups:
  assert isinstance(r['stock'],(int,float)),r
  groups[key]['stock']+=r['stock'];groups[key]['source'].append(f"总表!行{r['excel_row']}")
# Cart quantities are pieces, not packs, and are not received stock.
for r in cart:
 name=r['name'];spec=r['spec'] or '';key=None
 if '电阻' in name:
  m=re.search(r'([\d.]+)\s*([kK]?)Ω',name)
  if m:key=('R',float(m[1])*(1000 if m[2] else 1))
 elif '电容' in name and ('pF' in name or 'µF' in name):
  m=re.search(r'([\d.]+)\s*(pF|µF)',name);key=numeric_key('C',float(m[1])*(1e-12 if m[2]=='pF' else 1e-6)) if m else None
 elif '2N3904' in name:key=('Q','2N3904')
 elif '3296W' in name:
  m=re.search(r'(10|20)k',name);key=('POT',int(m[1])*1000)
 elif 'CCW12' in name:key=('TRIM','CCW12')
 elif '1812CS-392' in name:key=('L','1812CS-392')
 elif '78FR47K' in name:key=('L','78FR47K-RC')
 if key not in groups:continue
 per=1;m=re.search(r'(\d+)\s*(?:只|个)/份',spec)
 if m:per=int(m[1])
 elif '（5个）' in spec:per=5
 elif '10只包邮' in spec:per=10
 groups[key]['cart']+=r['packs']*per;groups[key]['source'].append(f"购物车!行{r['row']}（{r['packs']}份×{per}）")

for key,g in groups.items():
 g['need']=g['tx']+g['rx'];g['status']='库存足够' if g['stock']>=g['need'] else ('购物车覆盖，未付款' if g['stock']+g['cart']>=g['need'] else '漏列，需补充')
 if key==numeric_key('C',100e-9):g.update(stock='足够（用户确认）',status='用户确认足够，不补购',note='原账11只；当前图14只。用户已确认104足够，本次不列补购。')
 if key==('D','BAT85S-TR'):g.update(status='用现有件实测，不补购',note='Vishay DO-35直插；旧记录贴片说法错误。与Nexperia BAT85模型不同，保留实测验证边界。')
 if key==('Q','2N3904'):g.update(status='数量覆盖，厂牌待核',note='需求9只、原BU库存5只；车中50只非onsemi，须核对厂牌/脚序和RF性能，不自动当同厂牌覆盖。')
 if key==('TRIM','CCW12'):g.update(note='TX匹配1只+RX调谐2只，共3只；车中1份10只覆盖。替代Vishay后Q/调谐需实测。')
 if key==numeric_key('C',2.4e-12):g.update(note='RX CK实际图值2.4 pF；2.2在手、2.7备档不能不经复测视为等效；建议一次补10只C0G。')
 if key==('R',2200.):g.update(note='实际3只：TX RPU1、RPU2、RMRF；旧表只计2只。车中100只足够。')
 if key==('R',1000.):g.update(note='实际6只：TX RCG/RMC/RTP3；RX RC1/RC2/RRF。旧表5只。')
 if key==('R',4700.):g.update(note='实际7只，含TX原振荡R3；旧表6只漏计该位号。')
 if key==('R',100000.):g.update(note='RX RBIAS 1只，原表未给用途，但在手50只足够。')
 if key==('R',10000.):g.update(note='实际12只：TX8只、RX4只（含RG），旧表9只；库存50只仍覆盖。')
 if key==numeric_key('C',100e-12):g.update(note='实际6只：TX CMRF/CMOUT各1，RX CIN2/CBUF/CDET/CFILT各1。旧表4只。')
 if key==numeric_key('C',1e-9):g.update(note='实际6只：TX CT/CIN/COUTB/CME；RX CIN1/COBUF。旧表5只。')
 if key==numeric_key('C',10e-6):g.update(note='当前图TX4只、RX2只，共6只；库存10只。CVREF用10 µF，不是100 µF。')
 if key==('POT',20000):g.update(note='RVA幅度电位器1只即可；车中2份共10只，非全为必需。频率位RVRF用已有100 kΩ。')
 if key==('POT',10000):g.update(note='占空比1只；已有5只覆盖，车中另5只为备用，可减。')
 if key==('L','1812CS-392'):g.update(note='主用1只、车中2只含备用；不与接收470 nH混用。')
 if key in [('R',1200.),('R',36000.),('R',39000.)]:g['note']+=' 图值分别1.25k/37k/40k；采购1.2k/36k/39k已按既有清单保留，替代后测偏置。'

issues=[
 ['必须补列','CK 2.4 pF C0G','需要1只，建议买10只；现有总表和37项购物车都没有。','RX CK=2.4p；2.2/2.7为调试换值，不等于原图值。'],
 ['修改数量','成品天线1根改2根','用户本轮确认准备一次买两根；当前购物车仅1根。','两根均需核对31 MHz适用性和内置加载；不直接照搬纯拉杆外置3.9 µH模型。'],
 ['库存覆盖','100 nF / 104','用户本轮确认足够，不列购买。','图需14只；原账11只；不再用原账差3只推翻用户盘点。'],
 ['纠正旧记录','BAT85S-TR','保留现有5只，不买新的BAT85。','Vishay官方85513：DO-35直插，黑环为K；原记录贴片错误。实物代入仍需检波测试。'],
 ['图纸版本差异','CCW12替代Vishay微调','RX2只+TX1只，共3只；购物车10只足够。','此前图纸写2–18pF薄膜件，当前车为3.5–20pF陶瓷件；范围覆盖起调点，损耗性能未视为相同。'],
 ['确认商品','非原厂2N3904','总数9只，原BU5只；车中50只数量够。','同名型号不保证厂牌和封装脚序相同；优先明确来源/脚序，不新增第二包重复购买。'],
 ['补列辅料','1812电感转接/焊接支撑','2.54 mm万能板上1812CS-392不能当直插件直接插孔。','若现有铜箔/小转接片可做则不买；否则补适合1812双端器件的小转接板2片。'],
 ['补列辅料','绝缘单芯线、地线、热缩管','现有清单未见明确数量，先盘点；不等于实物一定没有。','一次备足两端板间配电和短连线；地网仅在选定天线确实需要时另定，不恢复已取消自制路线。'],
 ['补列辅料','焊锡、助焊剂、清洗/绝缘耗材','清单未列，可用实验室现成。','不自动增购物车；装配必需物需要确认可用。'],
 ['待定接口','两根天线的SMA配套/底座','已有3个SMA母座，车中2根公-公RG316；数量基本覆盖。','须核对普通SMA/RP-SMA、螺纹/针孔和安装固定；不能仅看公母字样。'],
 ['未定型','接收天线与匹配','用户已定购买两根，但第二根的31 MHz接收接口未验证。','最终天线型号确定前，不能保证一次补购后再无匹配元件调整。'],
 ['未定型','TX 9 V电池转5 V稳压','当前TX总图是外部稳压5 V输入，RX为9 V。','在手有L7805CV/LM317T但数量待盘点；先定电路再列其专用输入输出电容/散热，不凭空加BOM。'],
 ['可删/转备用','51 Ω测试源电阻','不是接收机实物必焊件。','源网表RSOURCE=50Ω是发生器内阻，不需买51Ω冒充或重复终端。'],
 ['可删/转备用','953 Ω','仅独立LC测试夹具使用，不计收发机板上用量。','若保留独立调谐夹具则保留车中10只，不称整机硬缺口。'],
 ['可删/转备用','100 µF直插','当前两张完整图中需求0只；10 µF库存10只已覆盖。','车中20只100µF是备用；不能把它当CVREF10µF的相同值。'],
 ['可删/转备用','10 Ω 1%与重复SOIC板','0.1%10Ω车中10只覆盖两处10Ω需求；LHY-A5片已覆盖OPA197。','RJ15 1%与另5片带散热焊盘板可删；不因换增益电阻强制多配运放板。'],
 ['可删/转备用','332对照电感、68 pF、390 kΩ','均是对照/备用，不是392+G44主方案必需。','可保留调试余量，但不把对照件算成主机缺件。'],
 ['记录更正','10 Ω需求与误差','整机实际两只：TX RMRG和RSENSE；精密0.1%10只足够。','同一电压下由R换算P=V²/R，R误差约等比例影响功率；不拿仿真数值闭合精度当采购精度依据。']]

# Add antenna/accessory rows beside circuit demands without pretending they are electrical netlist components.
extra=[
 {'category':'天线','name':'成品天线（两端各1）','need':2,'stock':0,'cart':1,'status':'购物车数量1改2','refs':['TX天线','RX天线'],'source':['用户本轮确认；购物车!行28'],'note':'需核对31 MHz适用性/内置加载及SMA配合；未宣称既定27 MHz商品已适配。'},
 {'category':'转接板','name':'SOIC-8到DIP-8逐脚直通','need':1,'stock':0,'cart':5,'status':'购物车覆盖，未付款','refs':['RX U1'],'source':['购物车!行35'],'note':'1片用于主机，其余备用；核对针脚映射。'},
 {'category':'连接线','name':'RG316 SMA跳线0.5 m','need':2,'stock':0,'cart':2,'status':'购物车覆盖，未付款','refs':['两端天线连接'],'source':['购物车!行36'],'note':'对普通SMA/RP-SMA、针孔、安装方式另核对。'},
 {'category':'连接器','name':'SMA母座','need':2,'stock':3,'cart':0,'status':'库存足够','refs':['TX/RX天线接口'],'source':['总表!行88'],'note':'已有3只；机械兼容需确认。'},
 {'category':'辅料','name':'1812双端电感小转接板/支撑','need':1,'stock':None,'cart':0,'status':'是否已有可用辅料待核','refs':['TX LFIX'],'source':['当前图1812贴片件'],'note':'已有铜箔/转接可用则不买；若没有，建议备2片。'}]
rows=list(groups.values())+extra
rank={'漏列，需补充':0,'购物车数量1改2':1,'数量覆盖，厂牌待核':2,'是否已有可用辅料待核':3,'购物车覆盖，未付款':4}
rows.sort(key=lambda g:(rank.get(g['status'],5),g['category'],g['name']))
for g in rows:
 g['refs']='；'.join(g['refs']);g['source']='；'.join(g['source']);g.setdefault('note','');g.setdefault('tx',None);g.setdefault('rx',None)
payload={'title':'收发机一次补购核对','date':'2026-11-19','sources':['05_元器件总表_20261119.xlsx（01总表、02购物车）','发射端全模块连接原理图_R3（74个实物条目）','接收机全模块连接原理图_R1（56个实物条目）','本轮用户：104足够、两根天线','Vishay官方BAT85S：https://www.vishay.com/docs/85513/bat85s.pdf'], 'rows':rows,'details':details,'issues':issues,'cart':cart,'inventory':inventory}
(O/'audit_data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print('demand rows',len(rows),'electrical entries',len(details))
for key in [('R',10.),('R',2200.),('R',1000.),('R',4700.),('R',10000.),numeric_key('C',100e-12),numeric_key('C',1e-9),numeric_key('C',100e-9),numeric_key('C',10e-6)]:
 g=groups[key];print(g['name'],g['need'],'stock',g['stock'],'cart',g['cart'])
print('uncovered',[(g['name'],g['need'],g['cart']) for g in rows if g['status'] in ['漏列，需补充','购物车数量1改2']])

md=['# 收发机采购完整性核对','', '2026-11-19。核对一套发射机和一套接收机，按原理图逐位号归并；已焊元件包含在整套需求内，不再重复扣库存。', '', '**结论：现有总表加购物车已覆盖大部分主电路，但不能称全部列齐。明确补列CK 2.4 pF，并把天线数量1改2；104按用户确认足够、不补买。1812电感转接与装配辅料还需盘点。**','', '原文件保持不动。购物车为未付款记录，不记成已到手；本报告未改购物车、未下单。','', '## 必须补列与版本更正','']
for a,b,c,e in issues:md.extend([f'### {a}：{b}', '',c+' '+e,''])
md.extend(['## 主电路按规格合并','', '|类别|规格|整套需要|在手|购物车折算只数|结论|位号|','|---|---|---:|---|---:|---|---|'])
for g in rows:md.append('|'+ '|'.join(str(g[k]) for k in ['category','name','need','stock','cart','status','refs'])+'|')
md.extend(['','## 来源','',*['- '+s for s in payload['sources']]])
(O/'收发机一次补购核对_20261119.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
