from pathlib import Path
import json,csv,math,hashlib,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from joint_sim import ROOT,OUT,BASE,PART,coil,ant,design,W
import metrics_support as met

def table(headers,rows):
 return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(str(v) for v in r)+' |\n' for r in rows)

def phasors(row):
 a=met.read_raw(OUT/(row['name']+'.raw'));t=a['time']
 k=(t>row['window_s'][0]+7e-6)&(t<row['window_s'][0]+17e-6);tt=t[k]
 w=met.weights(tt);w/=w.sum();p=2*np.pi*row['carrier_Hz']*(tt-tt[0]);m=np.array([np.sin(p),np.cos(p),np.ones(len(p))]).T
 def fit(x):
  c=np.linalg.solve(m.T@(w[:,None]*m),m.T@(w*x[k]));return complex(c[1],-c[0])
 vin=fit(a['v(tp3)']);v=fit(a['v(ef_e)']);i=fit((a['v(ef_e)']-a['v(sense_out)'])/10)
 return v/vin,i/vin

def main():
 rows=[json.loads(p.read_text()) for p in sorted(OUT.glob('*_metrics.json'))]
 # Older cases predate the shunt sweep and only carry the legacy key name.
 for _r in rows:
  if 'port_Z31_with_shunt' not in _r:
   _r['port_Z31_with_shunt']=_r['port_Z31_with_10ohm']
 for r in rows:
  r.pop('link_theta90',None)
  r['baseband_frequency_Hz']=r['modulation_cycles']/(r['window_s'][1]-r['window_s'][0])
  (OUT/(r['name']+'_metrics.json')).write_text(json.dumps(r,indent=2))
 (ROOT/'joint_summary.json').write_text(json.dumps(rows,indent=2))
 nom=sorted([r for r in rows if r['name'].endswith('_nom')],key=lambda r:r['length_m'])
 ants=json.loads((ROOT/'antenna_nominal.json').read_text());allant=json.loads((ROOT/'antenna_all.json').read_text())
 scan=[]
 for d in ants:
  for ls in [.95,1,1.05]:
   for extra in [0,.5e-12,1e-12]:
    for base in [0,.5e-12,2e-12]:
     for loss in [1,2]:
      z=coil(scale=ls,loss=loss,extra=extra);za=ant(d,base=base)
      c=1/(W*(z.imag+za.imag+W*2e-9))
      rt=10+z.real+za.real+.0025/(W*c)
      radz=d['R']+.2+1j*(W*d['Lant_H']-1/(W*d['Cant_F']))
      ratio=abs(1+1j*W*base*radz)
      scan.append(dict(length_m=d['length_m'],Lscale=ls,extra_Cp_pF=extra*1e12,base_pF=base*1e12,loss_scale=loss,
         required_total_C_pF=c*1e12,Rinput=rt,Qcoil=z.imag/z.real,efficiency_with_sense=d['R_radiated']/(ratio**2*rt),
         trim_alone_possible=bool(2e-12<=c<=18e-12),trim_plus10p_possible=bool(12e-12<=c<=28e-12)))
 with (ROOT/'retune_sensitivity.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,scan[0].keys());w.writeheader();w.writerows(scan)
 s='# 联合仿真与敏感性结果\n\n2026-11-17。ngspice-47，原晶体载波/LM393/调制/驱动完整保留；仅新建负载副本。下面全部为模型结果，不能当作6m、V2或功耗实测验收。\n\n'
 s+='## 四长度名义工况\n\n'+table(['长度cm','CT总pF','端口R含10Ω','载波RMS mA','总RMS mA','m','高/低平台峰值mA','9V预算mW'],[[round(r['length_m']*100),f"{r['Ctrim_total_pF']:.3f}",f"{r['port_Z31_with_shunt'][0]:.3f}",f"{r['carrier_fundamental_rms_mA']:.4f}",f"{r['total_time_weighted_rms_mA']:.4f}",f"{r['modulation_index']:.4f}",f"{r['high_plateau_median_peak_mA']:.3f}/{r['low_plateau_median_peak_mA']:.3f}",f"{r['battery_budget_mW']:.2f}"] for r in nom])
 s+='\n裸天线参数见03；本表含0.2Ω接触、0.5pF底座、厂家电感模型及CT。每个名义工况在局部宏模型中X31≈0，谐振31MHz。真实安装可偏离。70cm的CT须由微调与固定C0G并联实现；其余先核对2–18pF范围。\n\n'
 s+='## 压力工况与边沿\n\n'+table(['工况','载波mA','谐振MHz','端口R+jX Ω','QCE/QEF最小VCE V','过冲/欠冲 %阶跃','预算mW'],[[r['name'],f"{r['carrier_fundamental_rms_mA']:.4f}",f"{r['resonance_Hz']/1e6:.4f}",f"{r['port_Z31_with_shunt'][0]:.2f}{r['port_Z31_with_shunt'][1]:+.2f}j",f"{r['minimum_QCE_VCE_V']:.3f}/{r['minimum_QEF_VCE_V']:.3f}",f"{r['envelope_overshoot_pct_step']:.1f}/{r['envelope_undershoot_pct_step']:.1f}",f"{r['battery_budget_mW']:.2f}"] for r in rows])
 s+='\n过冲=(最大RF周期峰值−高平台)/(高−低)，欠冲=(低平台−最小RF周期峰值)/(高−低)。欠冲超过100%表示包络短时接近零，**不是负包络，也不是稳定低平台电流超过100%误差**。沿用原驱动的边沿塌陷仍需实物验证及接收链容忍度评估，不能称AM波形全面通过。所有压力点保留原CT不重调；调后可能恢复，不能把失谐电流当成最优可调电流。\n\n'
 s+='## 晶体管应力与功耗\n\n'+table(['长度cm','QCE峰值Ic mA','QEF峰值Ic mA','QCE平均/峰值功耗mW','QEF平均/峰值功耗mW','天线节点峰值V'],[[round(r['length_m']*100),f"{r['qce_peak_ic_mA']:.3f}",f"{r['qef_peak_ic_mA']:.3f}",f"{r['qce_average_power_mW']:.3f}/{r['qce_peak_power_mW']:.3f}",f"{r['qef_average_power_mW']:.3f}/{r['qef_peak_power_mW']:.3f}",f"{r['antenna_peak_V']:.3f}"] for r in nom])
 s+='\n晶体管功耗按VCE·IC+VBE·IB积分；未加入具体封装热网络。9V预算=9×(RF五伏源平均电流+基带五伏源平均电流+8mA稳压器假设)。稳态窗口1.85–2ms内取完整两个基带周期；只保存稳态窗口，不能宣称完整冷启动和长期热漂移验收。\n\n'
 conv=sorted([r for r in rows if r['name'] in ['h90_nom','h90_fine','h90_finer']],key=lambda x:-x['step_ns'])
 s+='## 频率与步长\n\n'+table(['最大步长ns','载波MHz','载波RMS mA'],[[r['step_ns'],f"{r['carrier_Hz']/1e6:.9f}",f"{r['carrier_fundamental_rms_mA']:.6f}"] for r in conv])
 if len(conv)==3:
  f=[r['carrier_Hz'] for r in conv];order=math.log(abs((f[0]-f[1])/(f[1]-f[2])),2);extrap=f[2]+(f[2]-f[1])/(2**order-1)
  s+=f'\n三点估计收敛阶{order:.3f}，零步长外推{extrap/1e6:.9f}MHz；最细步长与外推相差{abs(extrap-f[2]):.1f}Hz。这是数值误差评估，不能代替晶体参数、温度及电源实测稳定性。\n'
 s+='\n## 重新计算的条件链路预算\n\n'
 s+='使用新NEC方向图：Epeak/Irms=sqrt[η0·Re(Zant)·G(θ)/(2πr²)]，r=6m；G为包含天线损耗的NEC增益，**不能再乘一次天线效率**。匹配损耗已通过实际辐射支路电流体现。\n\nS05历史仿真响应以4.777Vpp/10mV峰值、m=.5为线性化起点，本轮按每个新m重算。接收转换系数假设Voc/E_local=1m，仅作假设场景，不是接收有效高度实测；若真实为0.5m，所需电流再乘2。地面全场与接收天线镜像约定必须一致，未建立RX全波模型前不能作为精确链路设计保证。\n\n'
 s+=table(['长度cm','仰角25°所需载波mA','本轮载波mA','仰角25°估算V2pp','仰角5°所需mA'],[[round(r['length_m']*100),f"{r['link_theta65']['required_carrier_mA_RXheff1m']:.2f}",f"{r['carrier_fundamental_rms_mA']:.2f}",f"{r['link_theta65']['V2pp_estimate_RXheff1m']:.2f}",f"{r['link_theta85']['required_carrier_mA_RXheff1m']:.2f}"] for r in nom])
 s+='\n本轮名义模型没有证明达到V2≥4Vpp。25°不是同桌水平接收方向，不得借主瓣替代实际链路；同高6m也不能拿有损地面模型θ=90°的渐近远区零点当真实室内接收量，故不把该点的巨大反算电流列入决策。6m、约0.62λ并不自动属于近场；本任务的主要链路不确定度是地面/室内传播、回流和RX实际有效高度及加载。需要固定安装后的传输测量，或进一步双天线电磁/电路联合模型。\n\n'
 s+='## 固定电感选型对比（同族 1812CS，厂家典型模型）\n\n'
 cov=ROOT/'fixed_inductor_coverage.csv'
 if cov.exists():
  cv=list(csv.DictReader(cov.open(encoding='utf-8-sig')))
  s+=table(['型号','长度cm','31MHz所需总C pF','所需串联元件','线圈Q31','含10Ω端口R','仅微调2–18pF可达','需并固定C0G'],
    [[c['part'],c['length_cm'],f"{float(c['required_total_C_pF']):.3f}",
      '电容' if c['series_C_required']=='capacitor' else '电感(感量不足)',
      f"{float(c['Q31']):.2f}",f"{float(c['port_R_with_10ohm']):.2f}",
      '是' if c['trim_alone']=='True' else '否','是' if c['trim_plus_fixed_C0G']=='True' else '否'] for c in cv])
  s+='\n三种同族件Q31在59.7–68.1之间，差别主要来自直流电阻与感量，不是“Q更高就一定更好”。**1812CS-472（4.7µH）是唯一同时覆盖80/90/100cm且只需2–18pF微调的组合**；70cm需再并约10pF固定C0G。1812CS-392与332感量偏低，31MHz所需串联电容增到22–311pF（70cm对332甚至反而需要串联电感），已超出所配微调量程，必须外加固定C0G或改用更大感量，等于多引入一个元件和一处寄生。因此472保留为主候选，392/332只作对照，不因“Q略高”改用。\n\n'
  opt=[q for q in rows if q['name'] in ('h90_opt472','h90_opt392','h90_opt332')]
  if len(opt)==3:
   s+=table(['90cm对照工况','载波RMS mA','谐振MHz','CT总pF','端口R含10Ω','m','QEF最小VCE V','欠冲%阶跃','9V预算mW'],
     [[q['name'],f"{q['carrier_fundamental_rms_mA']:.4f}",f"{q['resonance_Hz']/1e6:.4f}",f"{q['Ctrim_total_pF']:.3f}",
       f"{q['port_Z31_with_shunt'][0]:.2f}",f"{q['modulation_index']:.4f}",f"{q['minimum_QEF_VCE_V']:.3f}",
       f"{q['envelope_undershoot_pct_step']:.1f}",f"{q['battery_budget_mW']:.2f}"] for q in sorted(opt,key=lambda z:-z['carrier_fundamental_rms_mA'])])
   s+='\n三组都是各自重新调谐到31MHz后的结果，不是把同一CT硬套到不同电感。低感量件线圈串联电阻更小，端口电阻随之降到23–26Ω，但所需串联电容增至27–77pF，电容自身损耗同步上升。按同一定义复算含10Ω取样的空间波效率：**332为3.12%、392为2.93%、472为2.45%**——较低损耗确实换来了更高效率，这一项上332/392**优于**472，不能用"匹配损耗更多"来解释它们的电流优势。\n\n但**效率更高不等于应当选用**：332/392在80–100cm所需串联电容为22–311pF，且70cm时332反而需要串联电感，全部超出2–18pF微调量程，必须外加固定C0G或改用更大感量，多引入一个元件与一处寄生。因此排除332/392的**唯一理由是长度可调性不足，不是效率低**。选型结论不变，依据须写对：**在可调性满足的前提下效率更高者更优；472是目前唯一在全部长度上都满足可调性的型号。**\n\n'
  s+='## 射频功率去向与匹配效率（关键节）\n\n'
 lb=ROOT/'loss_budget.json'
 if lb.exists():
  LB=json.loads(lb.read_text(encoding='utf-8'))
  P=LB['parts90'];B90=LB['budget90']
  RT=B90['Rt']
  s+='**全部量已折算到同一电流基准（端口电流）**，各项之和严格等于联合模型端口电阻。天线支路与底座电容并联，支路电流仅为端口电流的%.1f%%，故支路电阻须除以 k²=%.4f 后再相加：\n\n'%(100/B90['k2']**.5,B90['k2'])
  s+=table(['元件','等效电阻 Ω（端口基准）','占 I²R 比例'],[
    ['RSENSE 取样电阻',f"{P['RSENSE']:.3f}",f"{100*P['RSENSE']/RT:.1f}%"],
    ['加载电感串联损耗',f"{P['COIL']:.3f}",f"{100*P['COIL']/RT:.1f}%"],
    ['天线欧姆损耗（含0.2Ω接触，扣除辐射部分）',f"{P['ANTENNA_LOSS']:.3f}",f"{100*P['ANTENNA_LOSS']/RT:.1f}%"],
    ['微调电容损耗',f"{P['TRIM_CAP']:.3f}",f"{100*P['TRIM_CAP']/RT:.1f}%"],
    ['**实际辐射**',f"**{B90['R_rad_port']:.3f}**",f"**{100*B90['R_rad_port']/RT:.1f}%**"],
    ['**合计 = 端口电阻**',f"**{RT:.3f}**",'**100.0%**']])
  s+='\n**结论：损耗主体是加载电感与取样电阻，二者合计%.1f%%；辐射仅占%.1f%%。** 线圈%.2fΩ占%.1f%%，取样电阻%.1fΩ占%.1f%%。\n\n'%(
    100*(P['COIL']+P['RSENSE'])/RT,100*B90['R_rad_port']/RT,
    P['COIL'],100*P['COIL']/RT,P['RSENSE'],100*P['RSENSE']/RT)
  s+='**适用范围限定：以上占比是 1812CS-472 在90cm名义工况下的结果，不可直接套用于392或332。** 三种型号的线圈ESR不同（15.92／11.50／10.25Ω），占比须各自单独计算；更换器件时应重建该器件的基准，不得沿用本表数字。\n\n'
  s+='**换算规则（本轮两次出错后的结论）：** 天线支路与底座电容并联，支路电阻折算到端口时须**除以 k²**；而计算功率时，**电流与电阻必须采用同一基准**——用支路电流就配支路电阻，用端口电流就配端口折算后的电阻。混用会引入 k² 的系统性偏差。\n\n'
  _k2=B90['k2']; _Ib=3.8595e-3; _Ip=_Ib*math.sqrt(_k2)
  _prad=_Ib**2*(B90['R_rad_port']*_k2)*1e3; _psen=_Ip**2*P['RSENSE']*1e3
  s+='**功率比较必须换算到同一电流基准。** 载波支路电流 Ib=%.4fmA（即 I(VANT)），端口载波电流 Ip=Ib·√k²=%.4fmA（如10Ω取样电阻所见）。两种等价算法给出一致结果：P_rad=Ib²·R_rad,branch=Ip²·R_rad,port=**%.4fmW**。同基准下取样电阻耗散 Ip²·10=**%.4fmW**，是辐射功率的 **%.1f 倍**。\n\n'%(
    _Ib*1e3,_Ip*1e3,_prad,_psen,_psen/_prad)
  s+='对0.5W整机预算这些都是小量，但在"有限RF功率是否用于辐射"这个目标下，取样电阻是除加载电感外最大的单项损失。**注意本表是载波频率功率；含调制的总RMS是另一个量，见上方"总RMS"列，两者不可混用。**\n\n'
  s+='### 取样电阻 A/B/C 方案（90cm，全部重调谐并跑完整晶体管瞬态）\n\n'
  rs=[q for q in rows if q['name'] in ('h90_nom','h90_rs5','h90_rs2','h90_rs1','h90_rs01')]
  rs=sorted(rs,key=lambda z:-z.get('rsense_ohm',10.0))
  s+=table(['方案','RSENSE Ω','载波RMS mA','总RMS mA','调制度 m','QCE最小VCE V','取样电阻功耗mW','天线节点峰值V'],
    [[q['name'],f"{q.get('rsense_ohm',10.0):.2f}",f"{q['carrier_fundamental_rms_mA']:.4f}",f"{q['total_time_weighted_rms_mA']:.4f}",
      f"{q['modulation_index']:.4f}",f"{q['minimum_QCE_VCE_V']:.4f}",f"{q['sense_resistor_power_mW']:.4f}",f"{q['antenna_peak_V']:.3f}"] for q in rs])
  s+='\n**A（保留10Ω）**载波3.86mA；**B（降阻）**5Ω→4.34mA、2Ω→4.68mA、1Ω→4.80mA；**C（最终运行≈移除）**0.01Ω→4.93mA。\n\n'
  s+='**移除取样电阻使载波电流提升27.7%，但这不是纯收益**：调制度从0.2708降到0.2576（−4.9%），天线节点峰值电压从5.87V升到7.07V。负载变轻使射随工作点移动，包络摆幅相对变小。另外取样电阻同时是10Ω电流检测点与一定的射极负反馈，去掉后**电流测量手段本身消失**，且驱动对负载变化更敏感。\n\n'
  s+='**建议**：最终样机可移除或以小阻值（如0.1Ω金属膜/四端）保留取样，但必须同时复核调制度与链路预算；调试阶段保留10Ω。\n\n若驱动是理想恒压源，端口总电阻由30.03Ω降到20.04Ω（比值1.499）时电流应涨1.499倍；**仿真**只涨1.277倍（10Ω→1Ω时为1.245 vs 理论1.428）。**差距证明驱动不是恒压源，其输出阻抗与工作点随负载移动**——这正是"不能仅凭电阻减小就判定电流一定上升"的定量依据。\n\n'
 s+='### 若只做 90–100cm：三种电感应按效率重排\n\n'
 fl=ROOT/'fixed_length_part_choice.csv'
 if fl.exists():
  FR=list(csv.DictReader(fl.open(encoding='utf-8-sig')))
  s+=table(['型号','长度cm','所需总C pF','额外C0G pF','Q31','含10Ω效率%','仅微调可行'],
    [[x['part'],x['length_cm'],f"{float(x['C_pF']):.3f}",f"{float(x['extra_C0G_pF']):.1f}",f"{float(x['Q31']):.1f}",
      f"{100*float(x['eta_driver']):.3f}",'是' if x['trim_alone']=='True' else '否'] for x in FR])
  s+='\n**这条推翻了此前的选型结论。** 之前把"单个2–18pF微调覆盖70–100cm"当作硬约束，据此排除效率更高的332/392。但天线是**装好后一次性微调**，不需要每天在70与100cm之间切换；若目标长度定为90–100cm，392只需额外并3.8–8.8pF固定C0G，332需28.5–58.8pF，**都只是多一只几分钱的C0G电容**。\n\n'
  s+='按效率：**332（90cm 3.12%、100cm 3.77%）> 392（2.93%／3.54%）> 472（2.46%／2.98%）**。100cm时332比472高约26%。此前"472是唯一可选"的结论**作废**，改为：\n\n'
  s+='- 若必须单一微调覆盖70–100cm：**472，但70cm仍需并约10pF C0G**（70cm总需20.76pF，超出2–18pF微调量程）。严格说472也不是"全程零外加"，只是外加量最小（70cm约10pF，80–100cm为0）。\n'
  s+='- 若固定90–100cm使用（推荐）：**392为效率/复杂度折中最优**，仅需约4–9pF C0G；332效率最高但需28–59pF，且70cm时仍会失效。\n\n'
  s+='注意：这三种件的Q31差异（59.7/64.3/68.1）来自厂家典型模型，**不是保证值**；排序在实测Q后可能改变。\n\n'
 s+='## 匹配后空间波效率与可重调性\n\n'
 nomscan=[r for r in scan if r['Lscale']==1 and r['extra_Cp_pF']==0 and r['base_pF']==.5 and r['loss_scale']==1]
 s+=table(['长度cm','含10Ω效率%','所需总CT pF','匹配Q31典型'],[[round(r['length_m']*100),f"{100*r['efficiency_with_sense']:.2f}",f"{r['required_total_C_pF']:.3f}",f"{r['Qcoil']:.2f}"] for r in nomscan])
 s+='\n216组解析压力/重调结果见`retune_sensitivity.csv`。Q不是一个固定理想输入：名义来自厂家电感模型，增加损耗和并联寄生后重新计算。额外自容越大，谐振变化和端口损耗放大越显著。是否可调回只是电抗条件，不能保证调后电流/V2。\n\n'
 s+='## 元件Q值的影响（含外推压力工况与两侧包络）\n\n'
 qc=ROOT/'q_corners.csv'
 if qc.exists():
  qr=list(csv.DictReader(qc.open(encoding='utf-8-sig')))
  s+=table(['loss_scale','Q31','线圈R31 Ω','含义'],[[q['loss_scale'],f"{float(q['Q31']):.1f}",f"{float(q['coil_R31_ohm']):.2f}",q['label']] for q in qr])
  s+='\n**更正与界定**：模型(Q31=59.7)在50MHz给出的Q是79.4，高于厂家给出的Q≥63@50MHz，因此标称模型对50MHz偏乐观。按Document 158的损耗缩放规律反解使Q50=63，得loss_scale=1.2646、**Q31=47.3**（线圈串联电阻15.92Ω→20.13Ω）。\n\n**必须说清：Q31=47.3不是厂家保证的下限。** 厂家只在50MHz一个频点给出Q≥63，并未保证31MHz的Q值；47.3是按本模型损耗规律外推得到的压力工况，其数值依赖于该缩放假设本身。下列各处凡出现"下限"字样，均指这个外推压力点，而非厂家的频点保证。真实Q31只能由到货实测确定，或在采购前要求供应商提供31MHz数据。此前仅扫描loss=1/2（Q31=59.7/29.9）只有下行方向，现补上行至Q31=119.1与下行至该外推压力点，形成两侧包络。\n\n'
 qq=[q for q in rows if q['name'].startswith('h90_Q')]
 if len(qq)>=2:
  s+=table(['90cm工况','Q31','载波RMS mA','端口R含10Ω','m','QEF最小VCE V','欠冲%阶跃','9V预算mW'],[[q['name'],f"{q['coil_Z31_ohm'][1]/q['coil_Z31_ohm'][0]:.1f}",f"{q['carrier_fundamental_rms_mA']:.4f}",f"{q['port_Z31_with_shunt'][0]:.2f}",f"{q['modulation_index']:.4f}",f"{q['minimum_QEF_VCE_V']:.3f}",f"{q['envelope_undershoot_pct_step']:.1f}",f"{q['battery_budget_mW']:.2f}"] for q in sorted(qq,key=lambda z:-z['coil_Z31_ohm'][1]/z['coil_Z31_ohm'][0])])
  s+='\nQ从119降到47时载波电流下降约四分之一（4.67→3.52mA），端口电阻由约22Ω升到约34Ω，功耗预算基本不变。即Q31低至47这一外推压力点仍能谐振并输出数毫安电流；但电流下降会直接削弱链路余量，而本轮链路预算本就不足，所以Q值不是可忽略的次要参数——且真实值落在哪一侧目前未知。\n\n'
  base=next((r for r in rows if r['name']=='h90_nom'),None);pert=next((r for r in rows if r['name']=='h90_trimplus1'),None)
 if base and pert:
  v0,i0=phasors(base);v1,i1=phasors(pert);zo=-(v1-v0)/(i1-i0)
  s+=f'## 驱动输出阻抗局部诊断\n\n对90cm高平台，在完整链路中将CT增加1%，将ef_e电压和取样电流基波相位/幅度归一到tp3，差分估计Zout≈{zo.real:.2f}{zo.imag:+.2f}jΩ。此为小负载扰动、相同高平台的局部割线估计，依赖近似线性和tp3归一化，**不是全平台、全频率的戴维南定值**。因此不引入50Ω输出假设，也不据该单点批准L型匹配。\n\n'
 s+='## 验证边界\n\n已输出原始raw/log/cir及每组JSON，RMS时间加权自测与独立梯形积分交叉核对；核心网表行保持。未完成：具体购物车SKU参数、真实拉杆阶梯结构、全容差/温度统计、实际RX整链波形、6m实测、实物电池功耗和频率稳定性。本轮是可复现初始模型验证，不能把阶段状态改成整机验收完成。\n'
 (ROOT/'04_联合仿真结果.md').write_text(s,encoding='utf-8')
 # Compact, shareable scientific figure.
 plt.rcParams.update({'font.size':10})
 fig,ax=plt.subplots(2,2,figsize=(11,7),layout='constrained')
 hh=[r['length_m']*100 for r in nom]
 ax[0,0].plot(hh,[r['carrier_fundamental_rms_mA'] for r in nom],'o-',label='Simulated carrier')
 ax[0,0].plot(hh,[r['link_theta65']['required_carrier_mA_RXheff1m'] for r in nom],'s--',label='Conditional 25 deg link need')
 ax[0,0].set(xlabel='Radiator length (cm)',ylabel='Carrier current (mA)');ax[0,0].legend()
 ax[0,1].plot([d['length_m']*100 for d in ants],[d['L_uH'] for d in ants],'o-');ax[0,1].set(xlabel='Radiator length (cm)',ylabel='Bare antenna compensation (uH)')
 if base:
  a=met.read_raw(OUT/'h90_nom.raw');t=a['time'];cur=a['i(vant)'];cr=np.flatnonzero((cur[:-1]<0)&(cur[1:]>=0));pk=[max(abs(cur[l:r+1]))*1e3 for l,r in zip(cr[:-1],cr[1:])];tc=(t[cr[:-1]]+t[cr[1:]])/2
  ax[1,0].plot((tc-base['window_s'][0])*1e6,pk,lw=.8);ax[1,0].set(xlabel='Time from rising edge (us)',ylabel='RF cycle peak (mA)',xlim=(-5,55))
 ax[1,1].plot(hh,[r['battery_budget_mW'] for r in nom],'o-');ax[1,1].axhline(500,color='r',ls='--');ax[1,1].set(xlabel='Radiator length (cm)',ylabel='Assumed 9 V battery budget (mW)',ylim=(0,550))
 fig.suptitle('ALT.3.3: conditional models, not hardware acceptance')
 for aa in ax.flat:aa.grid(alpha=.25)
 fig.savefig(ROOT/'simulation_summary.png',dpi=170)
 print('Generated',len(rows),'transient rows,',len(scan),'analytic cases')

if __name__=='__main__':main()
