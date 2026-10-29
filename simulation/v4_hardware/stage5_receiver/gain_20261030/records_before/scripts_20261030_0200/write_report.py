"""Render S05-06 from checked simulation records; never rewrite S05-05."""
from run_gain import *
from analyze_results import main as analyze

def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)

def main():
    analyze()
    data=json.loads((HERE/'summary.json').read_text());lookup={r['name']:r for r in data['integrated']}
    def get(n):return lookup[n]
    def existing(n):
        for s in ['', '_gear', '_h025_short']:
            if n+s in lookup:return lookup[n+s]
        return None
    nominal=[get('F22_sq10_sixcycles'),get('F22_sq50_sixcycles')]
    nominaltable=table(['输入占空比','原A/G11.2 Vpp¹','G22原始/稳健Vpp','输出范围/V','占空比/%','频率/Hz','20k峰值/V'],[
        [f"{r['input_duty']:.0f}%",'2.433' if r['input_duty']==10 else '2.423',f"{r['vpp']:.4f} / {r['robust_vpp']:.4f}",f"{r['low']:.3f}～{r['high']:.3f}",f"{r['duty_pct']:.4f}",f"{r['frequency_hz']:.3f}",f"{r['peak20']:.5f}"] for r in nominal])
    br=[]
    for f,aa in [(29,[10,50,60]),(33,[10,40,50])]:
        for a in aa:
            r=get(f'F22_sine_{f}_{a}_gear')
            br.append([f'{f} MHz / {a} mV',f"{r['peak20']:.5f}",f"{r['delta20_db']:.3f}",f"{r['vpp']:.3f}",f"{r['low']:.3f}～{r['high']:.3f}",f"{r['bb_gain20']:.3f}"])
    bt=table(['CW','最终20k峰值/V','ΔBB/dB','原始Vpp/V','输出范围/V','20k基带级增益'],br)
    sr=[]
    for duty in [10,50]:
        for suffix,label in [('29_10','29M / 10mV'),('33_10','33M / 10mV'),('dual10','双CW各10mV'),('33_40','33M / 40mV')]:
            r=existing(f'F22_sq{duty}_{suffix}')
            if not r:sr.append([f'{duty}%',label,'无有效数组','—','—','—','—']);continue
            sr.append([f'{duty}%',label,f"{r['vpp']:.3f} / {r['robust_vpp']:.3f}",f"{r['delta20_db']:.3f}",f"{r['duty_pct']:.3f}" if r['duty_pct'] is not None else '无',f"{r['frequency_hz']/1000:.4f}" if r['frequency_hz'] else '无',f"{r['rising_crossings']}/{r['falling_crossings']}，{r['cycle_count']}周期"])
    st=table(['输入占空比','干扰','原始/稳健Vpp','Δ20k/dB','恢复占空比/%','频率/kHz','上升/下降交越数'],sr)
    dr=[];hr=[]
    for duty in [10,50]:
        for gain,prefix in [(22,'F22'),(11.2,'F11p2')]:
            r=existing(f'{prefix}_sq{duty}_Ac20')
            if not r:dr.append([f'{duty}%',str(gain),'无有效数组','—','—','—']);continue
            dr.append([f'{duty}%',str(gain),f"{r['vpp']:.3f} / {r['robust_vpp']:.3f}",f"{r['low']:.3f}～{r['high']:.3f}",f"{r['duty_pct']:.3f}" if r['duty_pct'] else '无',f"{100*r['rail_fraction']:.2f}%"])
        r=existing(f'F22_sq{duty}_m025');base=get(f'F22_sq{duty}_sixcycles')
        if r:
            ratio=r['robust_vpp']/base['robust_vpp'];error=100*(ratio/.5-1)
            hr.append([f'{duty}%',f"{r['vpp']:.4f} / {r['robust_vpp']:.4f}",f'{ratio:.5f}',f'{error:+.2f}%',f"{r['duty_pct']:.3f}"])
    dt=table(['占空比','固定增益','20mV时原始/稳健Vpp','输出范围/V','恢复占空比/%','距0/9V轨小于0.1V占比'],dr)
    ht=table(['占空比','m=0.25原始/稳健Vpp','稳健Vpp比值','相对理想0.5误差','恢复占空比/%'],hr)
    cc={r['name']:r for r in data['components']}
    ct=table(['单项变化','31M增益','插值3dB带宽/MHz','29/33M相对抑制/dB'],[[n,f"{cc['C_'+n]['g31']:.2f}",f"{cc['C_'+n]['bw_interpolated_hz']/1e6:.3f}",f"{cc['C_'+n]['db29']:.2f} / {cc['C_'+n]['db33']:.2f}"] for n in ['Q20','Q30','Q40','Q50','Q80','Lboth0p95','Lboth1p05','retuneL0p95','retuneL1p05','CK2p185','CK2p785','RS200','rounded_C']])
    physical=[]
    for n in ['Q40','RS200']:
        r=existing('F22_sq50_'+n)
        if r:physical.append(f"{n} 的完整 G22/50% 方波为 {r['vpp']:.3f} Vpp（稳健 {r['robust_vpp']:.3f} Vpp），范围 {r['low']:.3f}～{r['high']:.3f} V。")
    failures=sorted(p.stem for p in (HERE/'failures').glob('*.json'))
    brief=json.loads((HERE/'boundary_recheck.json').read_text())
    audited=table(['RF+检波独立复核，0.25ns/六周期','Δ20k/dB'],[[x['name'].replace('Audit_',''),f"{x['delta_db']:.4f}"] for x in brief])
    text=f'''# S05-06：A 方案基带增益补偿与阻塞复验

执行日期：2026-10-30（Asia/Shanghai）。起点 Git `94ca0492db917b7956776512086dabecc0781bbc`。承接 [S05-05](S05_05_R2邻近阻塞诊断与AB决策.md)，新证据位于 [gain_20261030](gain_20261030/)。原 R2、S05-05 及其全部证据保留；未推送 Git。

## 1. 决策与验证边界

**保留约 2 MHz 双调谐 A 前端和原 Q1/Q2，将检波后 OPA197 固定增益从 11.2 调至 22，作为 10 mV / 50 Ω 标称接收候选。** 只改 RFB=102 kΩ→210 kΩ；RG=10 kΩ、3 V 参考、9 V 供电、100 Ω 输出隔离及 1 MΩ∥100 pF 负载保持不变。210 kΩ 可由 200 kΩ+10 kΩ 串联实现。候选连接见 [S05_A2_G22_candidate.cir](S05_A2_G22_candidate.cir)。此文件不含测试夹具的预充电开关或初始化元件。

名义模型下，10%/50% 方波已恢复至约 4.78/4.76 Vpp，保持 20 kHz 和可辨识脉冲；单邻近 CW 的 1 dB 工程边界仍为 29 MHz 约50～60 mV、33 MHz约40～50 mV。**该结论限于规定的有用信号、调制、源阻抗、模型与负载。固定 G22 的20 mV 输入过载不能关闭；不把标称幅度通过写成全动态范围通过。** 本轮不优化 B、不改 Q1/Q2、不引入 AGC、不做真实 TX 联调。

## 2. S05-05 定义与数据审计

阻塞仍定义为 `ΔBB=20log10(|C20k,blocked|/|C20k,clean|)`，即有用20 kHz傅里叶分量相对同一方案无干扰值的变化。1 dB 是工程比较标记，不是课程硬指标，不是RF P1dB，也不是原始Vpp下降1 dB。原边界使用**正弦AM**，不能直接当作所有占空比方波的边界。

有用载波源 Ac=10 mV开路峰值，31 MHz，m=0.5，20 kHz；所有CW幅度也指开路峰值，各源相加后共用50 Ω。单CW初相位0，双CW均0、幅度为每个干扰的幅度。温度27°C、理想9 V电源；教育用2N3904、Nexperia BAT85及原TI OPAx197 v1.3模型保持原文件。`bat85s_qualified=false`。

独立读取14组旧原始数组重新作时间加权傅里叶积分，网表/日志/raw哈希全部一致；幅度相对误差小于0.001%。重新确认原R2的29/33 MHz边界均3～4 mV。另用0.25 ns、100～400 µs六周期复跑A边界，结果如下：

{audited}

因此40～60 mV改善不是由总Vpp、错误归一化或两周期取样造成的假象。29M/50mV是临界附近的点，只报离散区间；这些条件下的改善不代表无线天线抗干扰规格。源至RF的2 MHz是带负载整段AC响应，名义插值带宽约1.96 MHz；相对原R2的4.82 dB损失是电压增益比，不是独立50 Ω两端口S21。

## 3. 所需增益、工作点与标称输出

[正式指标](../../../性能指标要求_N31_M50.md)要求标称输出至少4 Vpp；设计目标约4.8 Vpp、频率19.80～20.20 kHz、50%占空比误差不超过5个百分点。旧A/G11.2输出约2.43 Vpp，按比例估算最低G约18.5、恢复4.8 Vpp需约22.1。此处比例只用来选测试点，最终判定使用实际OPA联合结果。

{nominaltable}

¹旧A/G11.2来自S05-05，保留其两周期与测量口径；新G22原始/稳健Vpp均由2 ns均匀插值波形测得，稳健Vpp=98%−2%分位，不对自适应采样点直接求分位。

独立无强制初值DC求解得到 ref≈3.000013 V、bbin≈3.000013 V、bbo≈3.000439 V，供电电流约1.303 mA（含基带参考分压）。联合标称参考约3.000006/3.000015 V；10%最低/最高约2.480/7.257 V，50%最低约0.585 V，均有轨余量。标称最大输出斜率约4.75 V/µs，RF+检波+基带9 V端功耗约147.3 mW；不等于整机电池功耗。

两个标称用例各保存六个完整调制周期、含五个完整交越周期；每周期平均值、稳健Vpp跨度均小于平均稳健Vpp的0.1%，周期跨度小于0.1%，无额外交越或丢脉冲。0.25 ns同窗短测与0.5 ns相比，最终Vpp变化约−0.075%、20k分量约−0.064%，不改变结论。此为正常工作预偏置窗口的重复性，不是冷启动或全局长期稳态证明。

![标称与动态范围](gain_20261030/plots/output_waveforms.png)

## 4. 补偿后阻塞与方波

完整链路的正弦阻塞采用相同Gear积分器、0.5 ns、100～200 µs窗口归一化；trap原始尝试在135.896 µs报步长过小，部分数组已排除。名义和阻塞对照都使用实际BAT85和OPA197，未使用理想运放输出替代。

{bt}

20k基带级增益约22，阻塞发生前后的变化很小；增强基带增益没有把检波损失消除，也没有因轨限幅制造更好的阻塞读数。0.25 ns配对正弦复核另见JSON摘要。强CW下正弦原波形可能出现额外半幅交越，JSON通用的交越“频率/占空比”不用于正弦验收；20k投影与原始Vpp分别报告。

方波使用各自10%/50%无干扰基准，不混用正弦归一化；下表短窗两周期仅证明已测周期的恢复，不能独自声称满足五周期稳定性条件。33M/40mV的六周期尝试未取得完整有效结果，改以Gear短窗及同积分器无干扰配对诊断，不把小数位差别当作精确阈值。

{st}

阻塞下总Vpp与有用基波可不同方向变化，表中不以Vpp变大作为成功判据。单10mV及双各10mV只代表指定相位；上一轮已发现双干扰相位敏感，未外推所有相位。强干扰下方波的20k损失可能先于正弦达到1 dB，见对应数值；因此仍不把正弦40～60mV边界写成方波通用保证。

![基波阻塞比较](gain_20261030/plots/blocking.png)

## 5. 10/20 mV动态范围与幅度比例

下表的Ac20 mV是接收端有用载波源加倍，和发射基带幅度减半不是同一测试。主候选在所有工况始终使用G22；G11.2为单独、明确切换的手动低增益对照，不参与G22通过率，也不是AGC。

{dt}

G22/20mV/50%有效数组显示低端约31 mV，近下轨占比约48%，实际20k基带级增益下降，属于削底；Vpp变为8.37 V不能解释成性能提高。9 V供电、3 V平均偏置下，理想50%方波向下最多约3 V余量，10%方波的高电平约为平均值以上0.9倍Vpp；因此在接收输入加倍时，仅提高固定基带增益不能同时保证所有占空比的摆幅。G11.2低增益对照约5.57 Vpp，但50%低端仅约0.18 V，仍缺器差余量及六周期/阻塞联合验证，不直接升级为已验收自动或手动增益系统。距电源轨0.1 V的占比是筛查指标，最终削顶同时看波形及基带实际增益，不把所有近轨点机械认定为饱和。

另在Ac=10 mV不变时把m从0.5减为0.25，作为“发射调制幅度减半”的**局部理想AM代理**：

{ht}

比例误差按 `(Vpp_half/Vpp_full)/0.5−1`，同用稳健Vpp。该代理未经过真实TX、天线或传播链路，不能关闭正式无线接口的幅度比例验收。新结果也不改变S04 TP2 2.04 Vpp与S05源端10 mV口径不同的登记事项。

## 6. OPA197带宽、摆幅与稳定性

同一9 V、G22、100 Ω隔离、1 MΩ∥100 pF局部真实宏模型：20 kHz小信号增益21.991；相对20 kHz的上端−3 dB点约671 kHz。反相输入串联交流注入、保留直流反馈的返回比交越约387 kHz，相位裕量约83.7°。负载电容增至1 nF的独立压力点约301 kHz、59.7°，阶跃振铃增加；不把该压力点当作新负载规格。

局部阶跃夹具的耦合电容平均值仍在调整，因此其短窗均值筛查不通过，保留为边沿/振铃诊断；实际标称联合六周期已另行通过。这里的稳定性是名义宏模型、规定负载下的结果，未覆盖布局、温度、器差或外接长线。

[TI官方电气表](https://www.ti.com/document-viewer/OPA197/datasheet/electrical-characteristics-vs-4-v-to-18-v-vs-8-v-to-36-v-sbos5111222)给出4.5～36 V供电范围、10 MHz GBW、20 V/µs典型转换率及随负载变化的摆幅条件；“轨到轨”不等于能无误差到达0/9 V。转换率的官方测试条件与本夹具不同，不把典型值作9 V最坏保证。[稳定性章节](https://www.ti.com/document-viewer/OPA197/datasheet/capacitive-load-and-stability-sbos6205243)强调布局、增益和负载的作用，输出隔离电阻也带来负载分压。本轮保留现有100 Ω，不另加复杂补偿级。

## 7. A网络的实际可实现性

主候选完全沿用S05-05 A2：L1/L2各470 nH，CSEL14.529 pF、CK2.485 pF、COUT10.81 pF、CTUNE1/2为39.59/45.83 pF、port直流回路1 MΩ；电感以Q50@31 MHz串联ESR1.831 Ω及并联Cp1 pF建模。以下均为**实际LC拓扑SPICE单因素灵敏度**，不是理想滤波器，也不是器件型号资格。

{ct}

{''.join(physical)}

- **Q/损耗：** Q20～80是敏感性范围，不是已测分布。Q40的RF电压增益约35.19，低于名义39.28；更低Q会使检波幅度下降，单纯以“带宽接近2 MHz”判合格不够。
- **SRF与寄生：** Cp1 pF、470 nH对应理想自谐振约232 MHz；SRF200 MHz对应约1.347 pF的等效并联电容。Cp0.5～2 pF、CK±0.3 pF的独立扫描已经保存。CK仅约2.5 pF，焊盘/走线/器件互容不可忽略，需短连接和实测调谐。
- **现有器件线索：** [Vishay IRF-24规格表](https://www.vishay.com/docs/34056/irf24.pdf)的0.47 µH一行是±20%、Q≥40@25.2 MHz、SRF≥200 MHz、DCR≤0.17 Ω。不能据此宣称Q≥50@31 MHz；DCR也不能替代本模型的RF等效串联损耗。未确认实际手头线圈料号、Q曲线或实测S参数。
- **调谐必要性：** 两只L同向±5%且不调电容时，一侧29/33 MHz抑制可恶化至约3～4 dB。只调CTUNE两只电容，按 `ΔC=(1/Lnew−1/Lnom)/(2π31M)^2` 计算起点后重新跑真实AC模型，±5%恢复到约1.87～2.05 MHz、两侧抑制约11～13 dB。±20%时所需CTUNE1约30.24～53.61 pF、CTUNE2约36.48～59.85 pF；即使中心恢复，带宽仍约1.59～2.34 MHz，不能省掉加载带宽复测。建议固定C0G加合适范围微调，或分档选配；小数值不是直接采购BOM。
- **输入匹配：** 名义31 MHz看入约119.78+j22.57 Ω，对50 Ω参考回波损耗约7.37 dB、VSWR约2.50，不能称50 Ω匹配已通过。源阻抗50→200 Ω时RF增益39.28→20.99，基带幅度随之下降；真实天线阻抗必须在下一阶段测量后再决定匹配。没有用本轮模型关闭S04→S05无线接口。
- **标准值近似：** 14.5/10.8/2.4/39.6/45.8 pF组合的AC结果接近名义，但仍需要C0G/NP0介质、适当容差与实际布局；未进行实物验收。

![元件敏感性](gain_20261030/plots/component_response.png)

## 8. 求解方法、失败记录与复现

所有完整链路均先测相同激励下RF+检波开路均值，再把它用于耦合电容预偏置。成功方法：先对独立OPA电路做无强制节点初值的正常DC求解，把内部节点电压仅作为`.nodeset`求解初始猜测；只对detector out、bbin和ref保留正常工作预偏置。模型文件未改、增益未随单个测试调节。

早期完整内部状态UIC、预充电开关夹具及其Gear变体、90秒预算下的长窗、PWL拆分回放均有未完成记录，不能因没得到数组就判定电路失效。100 µs有效联合测试耗时24.5秒，六周期400 µs最终耗时约84～98秒，因此代表性检查才按已测计算量给150～180秒预算；其余主要是200 µs局部测试。ngspice独立文件允许少量并行，每个进程固定一个求解线程；没有启动Multisim。

正弦trap用例在135.896 µs出现步长过小，虽ngspice返回0并写出部分raw，完整窗口断言将其拒绝。其他失败/截断也登记，不以退出码或存在raw作为有效性充分条件。失败索引共{len(failures)}项：`{'`, `'.join(failures)}`。其中早期拆分回放仅作失败诊断，**未用于本报告输出幅度或阻塞验收**。

完成的结果、配置、原始文件路径、模型/网表/数组/日志SHA-256在[summary.json](gain_20261030/summary.json)、[audit.json](gain_20261030/audit.json)、[evidence_manifest.json](gain_20261030/evidence_manifest.json)。原始raw保存在`D:/ms_xsp/s05_gain_20261030/`，不入Git。旧文件完整快照见[baseline_snapshot.json](gain_20261030/baseline_snapshot.json)，旧边界独立审计见[previous_audit.json](gain_20261030/previous_audit.json)。原R2和S05-05证据未覆盖。

复现使用Python3.13、NumPy/SciPy及现有ngspice-47；网表文件为ASCII路径副本。执行已有用例先核验哈希并复用缓存；失败用例不自动重试，新条件另起名字。

```powershell
py -3.13 simulation/v4_hardware/stage5_receiver/gain_20261030/run_cases.py
py -3.13 simulation/v4_hardware/stage5_receiver/gain_20261030/components.py
py -3.13 simulation/v4_hardware/stage5_receiver/gain_20261030/bb_checks.py
py -3.13 simulation/v4_hardware/stage5_receiver/gain_20261030/analyze_results.py
py -3.13 simulation/v4_hardware/stage5_receiver/gain_20261030/audit_new.py
```

## 9. 下一阶段边界

按A+原Q1/Q2+G22推进标称10 mV候选，优先做线圈Q/SRF、输入阻抗与双调谐实物调校。需要覆盖更大接收幅度时，先明确手动增益档及输出动态范围要求，再作同一增益档的阻塞、方波和比例验证；本轮不引入AGC，也不因基带过载回头盲调RF偏置。

冷启动、实际BAT85S资格、所有输入/负载/温度、天线匹配、真实TX与6 m距离、整机电池端功耗仍未验证。名义仿真支持“恢复所需输出幅度并保留邻近阻塞改善”，不支持“固定G22覆盖10～20 mV全部工况”或“实物接收机已验收”。
'''
    (STAGE/'S05_06_A方案基带增益补偿与阻塞复验.md').write_text(text,encoding='utf-8')
    print('report written')

if __name__=='__main__':main()
