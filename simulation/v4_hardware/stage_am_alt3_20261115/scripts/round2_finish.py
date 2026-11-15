"""Build the evidence-backed A-E report only after all runs finish."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from round2_analyse import process
from closure_metrics import read_raw

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'round2_20261116'

def main():
    cases=json.loads((OUT/'cases.json').read_text())
    results={}
    for name in cases:
        log=(OUT/'results'/f'{name}.log').read_text(errors='replace')
        assert 'ngspice-47 done' in log,name
        results[name]=process(name)
        print('analysed',name,flush=True)
    old=[json.loads((ROOT/'results'/p).read_text()) for p in ['closure_sense10_metrics.json','closure_sense10_fine_metrics.json']]
    new=[results[k]['metrics'] for k in ['d125','d0625','d05']]
    freq=[m['carrier_Hz'] for m in old+new]
    diff=np.diff(freq)
    order=math.log(abs(diff[1]/diff[2]),2)
    limit=freq[3]+diff[2]/(2**order-1)
    predicted=limit+(freq[3]-limit)*(.05/.0625)**order
    conv=dict(step_ns=[.5,.25,.125,.0625,.05],frequency_Hz=freq,successive_difference_Hz=diff.tolist(),observed_order=order,predicted_0p05_Hz=predicted,prediction_error_Hz=abs(freq[-1]-predicted),extrapolated_zero_step_Hz=limit,estimated_finest_residual_Hz=abs(limit-freq[-1]),criterion='Engineering numerical target: estimated frequency residual <1 kHz, last difference <1 kHz, observed order approximately 2. Not a course frequency tolerance.',passed=bool(abs(limit-freq[-1])<1000 and abs(diff[-1])<1000 and 1.7<order<2.3 and abs(freq[-1]-predicted)<100))
    (OUT/'results/d_convergence.json').write_text(json.dumps(conv,indent=2)+'\n')
    nom=results['d05']; m=nom['metrics']; dg=nom['diagnostics']; tr=dg['transition_diagnostics']
    table=[]
    for name,r in results.items():
        x=r['metrics']; table.append(f"| {name} | {x['carrier_fundamental_rms_mA']:.4f} | {x['total_time_weighted_rms_mA']:.4f} | {x['minimum_QCE_VCE_V']:.4f} | {x['battery_budget_mW']:.2f} |")
    sat_table=[]
    for label,rows in dg['plateaus'].items():
        r=rows[0]; sat_table.append(f"| {label} | {r['QCE_min_VCE_V']:.4f} | {r['QCE_bc_max_V']:.4f} | {r['ce_fundamental_gain']:.4f} | {r['spectra']['v(drv_c)']['thd_2_to_5_pct']:.3f}% | {r['spectra']['i(ltune)']['thd_2_to_5_pct']:.3f}% |")
    a=json.loads((OUT/'results/a_summary.json').read_text())
    atable='\n'.join(f"| {r['Cp_pF']:.2f} | {r['minimum_current_ratio']:.4f} | {r['maximum_required_mV']:.2f} |" for r in a)
    ftable='\n'.join(f'| {h} | {f:.3f} |' for h,f in zip(conv['step_ns'],freq))
    edgetable='\n'.join(f"| {r['edge']} | {r['minimum_complete_cycle_peak_mA']:.4f} | {r['maximum_complete_cycle_peak_mA']:.4f} | {r['last_outside_2pct_us']:.3f} |" for r in tr['edge_metrics'])
    # Plots are scientific outputs; use explicit English units to avoid font dependence.
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    ax[0,0].plot([r['Cp_pF'] for r in a],[r['minimum_current_ratio'] for r in a],'o-')
    ax[0,0].set(xlabel='Uncorrected coil Cp (pF)',ylabel='Worst current / tuned current',title='A: fixed-voltage sensitivity')
    ax[0,1].plot(np.array(conv['step_ns'])**2,(np.array(freq)-31e6)/1e3,'o-')
    ax[0,1].set(xlabel='Maximum time step squared (ns^2)',ylabel='Frequency - 31 MHz (kHz)',title='D: numerical convergence')
    names=[k for k in results if not k.startswith('d')]
    ax[1,0].barh(names,[results[k]['metrics']['carrier_fundamental_rms_mA'] for k in names])
    ax[1,0].axvline(3.75,color='orange',ls='--'); ax[1,0].axvline(5.30,color='red',ls='--')
    ax[1,0].set(xlabel='Carrier fundamental RMS (mA)',title='C/E: sampled full-chain cases')
    d=read_raw(OUT/'results/d05.raw'); t=d['time']; vce=d['v(drv_c)']-d['v(drv_e)']; k=np.argmin(vce)
    use=abs(t-t[k])<1e-6
    ax[1,1].plot((t[use]-t[k])*1e6,vce[use],label='VCE')
    ax[1,1].plot((t[use]-t[k])*1e6,(d['v(drv_b)']-d['v(drv_c)'])[use],label='VBC',alpha=.8)
    ax[1,1].set(xlabel='Time from minimum VCE (us)',ylabel='Voltage (V)',title='B: edge transient'); ax[1,1].legend()
    fig.savefig(OUT/'results/round2_summary.png',dpi=160); plt.close(fig)
    report=f'''# AM-ALT.3 冻结驱动后的 A～E 仿真复核

2026-11-16。阶段状态：**已执行、勘误完成、待技术闭合**。

本轮完成2700点解析扩展和12组完整链路瞬态工况。现有两只2N3904驱动拓扑、RDC=1250 Ω、RDB1/RDB2=40k/10k Ω、RDE=150 Ω、REF=200 Ω及10 Ω取样保持不变。扫描只改独立仿真夹具中的负载、驱动器件模型参数或供电；没有改硬件设计，没有增加晶体管，没有采购、焊接。用户已确认天线与匹配未测，扫描结果不替代实测。

![A-E仿真汇总](round2_20261116/results/round2_summary.png)

## A. 扩展天线/匹配敏感性

原九组谐振解析结果直接引用 `results/closure_review.json`，不重新作为新证据计数。新增C=6～12 pF共25点，Q=30/60/100，C误差−3/0/+3%，L误差−1/0/+1%，线圈并联寄生Cp=0/0.25/0.5/1 pF，共2700点。

这是**不重新调峰时、恒定驱动电压**的相对敏感性，不是驱动电流预测。寄生模型为串联R+L被Cp并联；天线及地损耗5.224 Ω，再串10 Ω。加寄生后应重新拟合并调谐，表中恶化不能解释成可调网络也必然无法工作。

| 未校正Cp / pF | 网格最小相对电流 | 5.30 mA所需端口电压最大值 / mV RMS |
|---|---:|---:|
{atable}

75个无误差、无寄生的谐振点均恢复相对电流1，解析自检通过。该结果支持保留连续可调方案；±3%测量目标不能替代安装状态调峰。

## B. 低VCE是否意味着实际压缩

名义细步长运行：QCE最低VCE={m['minimum_QCE_VCE_V']:.6f} V，发生在距最近调制边沿{tr['minimum_VCE_offset_from_nearest_edge_us']:.3f} µs处。VBC最大{tr['maximum_VBC_V']:.4f} V；VBE与VBC同时为正的时间占比约{tr['saturation_time_fraction']*100:.3f}%，最长连续区间约{tr['longest_contiguous_saturation_ns']:.1f} ns。这里是瞬态结正向偏置证据，不只依据0.2 V阈值猜测。该时刻TP3={tr["at_minimum_VCE"]["v(tp3)"]:.5f} V、共射集电极={tr["at_minimum_VCE"]["v(drv_c)"]:.5f} V、射随输出={tr["at_minimum_VCE"]["v(ef_e)"]:.5f} V，QEF集电极电流仅{tr["at_minimum_VCE"]["i(@qef[ic])"]*1e6:.4f} µA。共射级集电极被拉低时，后级射随几乎截止，提供了边沿传输塌陷的直接节点/电流证据。

剔除边沿前后4 µs后分别分析连续平台，以下为各状态第一个完整片段；完整片段数据见JSON：

| 平台 | QCE最低VCE / V | 最大VBC / V | 共射基波增益 | 集电极THD(2～5次) | 天线电流THD(2～5次) |
|---|---:|---:|---:|---:|---:|
{chr(10).join(sat_table)}

高/低平台共射基波增益之比为{dg['ce_gain_high_vs_low_dB']:.4f} dB。稳定平台内VBC为负、基波增益变化很小，未见持续平台饱和；下降沿处则确实出现瞬态结正向偏置及包络凹陷。结论应分开记录，不能将最低VCE直接等同于整个平台严重压缩。两平台对照不是标准P1dB输入功率扫描；不能把差值直接称为P1dB。需同时看平台结偏置、增益及失真，区分边沿饱和与持续RF压缩。

边沿后的完整载波周期峰值（已剔除明显异常周期长度）：

| 边沿 | 最小周期峰值 / mA | 最大周期峰值 / mA | 最后超出目标平台±2%的时间 / µs |
|---|---:|---:|---:|
{edgetable}

观察窗为边沿后8 µs，±2%仅是恢复诊断带，非课程验收条款。表中电流幅值暂降或恢复过渡属于实际模型结果，不能用“平台增益变化小”将其删去。未做关闭饱和机制的反事实模型，因此不将全部包络过渡损失唯一归因于饱和。

## C. 负载、器件与供电扫描

完整工况定义在 `round2_20261116/cases.json`。负载两端为C=6 pF/Q30及C=12 pF/Q100，并各自调谐到31 MHz；另有固定L、C±3%。驱动器件模型仅QCE/QEF变化：BF=100、Tf×1.3、Cjc/Cje×1.2，或BF=600、Tf×0.8、Cjc/Cje×0.8；其余级的晶体管模型不变。供电扫描4.75/5.25 V同时施加于RF和基带电源。

**这些是独立参数扰动和联合压力工况，不是厂家统计分布或保证角点。** 模型BF不等于工作点实测hFE。器件手册的VCE(sat)有指定Ic/Ib测试条件，不能用来对本RF波形作单阈值判决：[onsemi 2N3904资料](https://www.onsemi.com/pub/Collateral/2N3903-D.PDF)。

表中 d125/d0625/d05 三行是同一名义负载在不同最大步长下的数值基线，供第 D 节收敛判断；其余各行为参数扫描。`c_det_minus3`/`c_det_plus3` 为固定 L、天线电容 ±3%；`c_lowC_loss`/`c_highC_lowLoss` 为负载两端并各自重新调谐到 31 MHz。

| 工况 | 载波RMS / mA | 总RMS / mA | QCE最低VCE / V | 电池预算 / mW |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

载波电流在联合压力工况约1.696 mA，器件慢模型约3.308 mA，低供电工况约3.492 mA，均低于3.75 mA预算下端；固定L且C+3%约3.931 mA，低损耗端约5.318 mA。因而**未证明现驱动在所扫范围内可靠覆盖需求**；功耗均低于500 mW不能替代电流/波形验收。该表界定的是**已采样仿真工况**。未覆盖全部参数组合、器件相关性、安装寄生、温度及冷启动，不能据此认证连续的可靠工作范围。对3.75/5.30 mA的比较仍是当前预算口径，实际调制度及接收链条件须统一后才能做最终判断。任何单点达到5.30 mA都不等于全范围通过。

## D. 31 MHz频率数值收敛

保留之前0.5/0.25 ns证据，新增0.125/0.0625 ns，并因末两点仍差1.147 kHz补做0.05 ns，不改晶体/电路参数。0.125 ns与0.0625 ns单帧运行分别约311 s与532 s，0.05 ns约629 s，raw约156/311/389 MB；这是本机该网表的实际成本，不是误差判据的一部分。各运行同为trap二阶、reltol=1e-5、同样2 ms终点及相同整数调制周期提取方法。细步长增加保存节点不改变电气网表。

| 最大步长 / ns | 提取载波频率 / Hz |
|---|---:|
{ftable}

最后相邻差{abs(diff[-1]):.3f} Hz，0.25/0.125/0.0625 ns三点实测收敛阶约{order:.3f}，零步长外推{limit:.3f} Hz，最细步长估计残差{abs(limit-freq[-1]):.3f} Hz。0.05 ns独立对照与前三点外推预测相差{abs(freq[-1]-predicted):.3f} Hz。本轮工程数值判据（相邻差<1 kHz、估计残差<1 kHz、阶数接近2，并补查预测差<100 Hz）结果：**{'通过' if conv['passed'] else '未通过'}**。这是步长收敛证据，不是实物频率校准，也不是严格误差上界；实际晶体容差、温漂和模型误差未纳入。

采用自适应积分的原始时间戳进行时间加权，载波用时间加权基波拟合。数值方法参考：[ngspice官方文档入口](https://ngspice.sourceforge.io/docs.html)。频率即使数值收敛，也不可将其改写为精确31 MHz。

## E. 完整发射链路受限仿真基线

名义基线采用 `round2_20261116/netlists/d05.cir` 与对应raw/log/指标；包括原振荡器、基带LM393、调制器、冻结驱动及含10 Ω的名义天线负载。联合压力工况 `e_adverse` 合并6 pF/Q30、低供电和慢/低BF驱动模型。基线含完整发射链路，不含无线传播与接收机，因此不能代替6 m及v2验收。

名义载波RMS={m['carrier_fundamental_rms_mA']:.4f} mA，总RMS={m['total_time_weighted_rms_mA']:.4f} mA，电池预算={m['battery_budget_mW']:.2f} mW。电池预算继续采用9 V、线性稳压、8 mA额外静态电流假设，非实测。全链路稳态窗口证据不能替代冷启动/长期漂移测试。

本轮得出的是可复现、带限制的仿真基线。**拓扑与电阻继续冻结；等待天线L/C、31 MHz安装调峰及损耗实测，再回填基线决定是否调整驱动。** 三个实物闭合任务尚未完成，阶段状态不升级。

## 复现与完整性

运行：`py -3 scripts/round2_runs.py`（独立文件、最多三个ngspice进程，已完成工况不会重复运行）；解析扩展：`py -3 scripts/round2_analyse.py`；汇总：`py -3 scripts/round2_finish.py`。

每个工况检查日志完成、raw尺寸/变量数/时间单调性；非均匀采样基波及10%已知THD自检通过。冻结前驱文件哈希见 `round2_20261116/frozen_sha256.json`，本轮证据清单见 `round2_20261116/results/evidence_sha256.json`。既有九组解析和两次步长结果保留原文件。
'''
    (ROOT/'06_AM-ALT.3_冻结驱动后ABCDE仿真复核.md').write_text(report,encoding='utf-8')
    frozen=json.loads((OUT/'frozen_sha256.json').read_text())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    files=[p for p in list((OUT/'netlists').glob('*.cir'))+list((OUT/'results').glob('*.raw'))+list((OUT/'results').glob('*.log'))+list((OUT/'results').glob('*.json'))+[OUT/'cases.json'] if p.name!='evidence_sha256.json']
    manifest={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (OUT/'results/evidence_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    summary={'completed_simulation_cases':len(results),'frozen_files_unchanged':True,'convergence':conv,'hardware_changed':False,'antenna_measured':False,'stage_status':'已执行、勘误完成、待技术闭合'}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__': main()
