"""Reanalyse retained preflight RAW files and generate auditable artifacts."""
import csv
import json
import math
from pathlib import Path
import preflight as p

R=p.ROOT
bb=p.baseband(reuse=True)
ref=p.oscillator('osc_reference',2000,10e-12,reuse=True)
rc=p.oscillator('osc_yz_rc',37500,4e-12,reuse=True)
# Cross-check against the existing C4 reported baseline at these settings.
assert abs(ref['vpp']-1.97489)<1e-4
assert all(r['window_relative_difference']<1e-3 for r in (ref,rc))
assert .07<bb['low_v']<.08 and 4.07<bb['high_v']<4.08

rows=[]
for q in (16,25,26):
    for eff in (.8,.85,.9):
        dyn=2*5*(.5*1+.5*.6)/50/math.pi*1000
        # Dynamic AD835 consumption is a class-B estimate, NOT a device model.
        chip=10*q+dyn
        reserve=10.0
        rails=chip+rc['rail_power_mw']+bb['rail_power_mw']+reserve
        battery=rails/eff+5
        positive=5*q+dyn/2+rc['rail_power_mw']+bb['rail_power_mw']+reserve/2
        negative=5*q+dyn/2+reserve/2
        linear_battery=9*(positive/5+8)+negative/eff+5
        rows.append(dict(status='CONDITIONAL_ESTIMATE_NOT_VERIFIED',iq_ma=q,efficiency=eff,
            ad835_positive_mw=5*q+dyn/2,ad835_negative_mw=5*q+dyn/2,
            carrier_mw=rc['rail_power_mw'],baseband_mw=bb['rail_power_mw'],
            bias_buffer_reserve_mw=reserve,rail_total_mw=rails,
            conversion_loss_mw=rails/eff-rails,battery_idle_reserve_mw=5,
            battery_mw=battery,margin_to_500_mw=500-battery,
            retain_7805_plus_battery_inverter_mw=linear_battery))
with (R/'results/条件功耗预算.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

text='''# 本次接口预检与条件功耗汇总

这些结果不含AD835宏模型。原晶体模型与教育版2N3904模型沿用项目，不能等同于已采购晶体或晶体管批次实测。

## 晶振与负载

5ms自主起振，uic；只保存4.9～5.0ms；trap，reltol=1e-5，最大步长0.125ns，输出间隔0.25ns。相同网表只替换RLOADG/CLOADG并增加供电电流记录，原电路不改。

| 条件 | Vpp | 最小V | 最大V | 频率MHz | THD 2～5次 | 5V轨mW |
|---|---:|---:|---:|---:|---:|---:|
'''
for label,r in [('原负载2kΩ∥10pF',ref),('Y/Z典型RC近似37.5kΩ∥4pF',rc)]:
    text+=f"|{label}|{r['vpp']:.6f}|{r['minimum']:.6f}|{r['maximum']:.6f}|{r['f_hz']/1e6:.6f}|{100*r['thd_2_to_5']:.3f}%|{r['rail_power_mw']:.6f}|\n"
text+=f'''
原负载结果复现C4同设置的1.97489Vpp。两段末尾50µs窗口Vpp相对变化分别为{ref['window_relative_difference']:.3g}、{rc['window_relative_difference']:.3g}，仅说明此末窗重复性。新负载未做多步长/多容差收敛，不能给它最终精确幅度保证。

**RC近似已经使Y端峰值越过±1V；它还没有包含输入偏置电流和器件非线性，不能据此计算真实AD835输出。** 原负载虽约2Vpp，受谐波影响，负峰也达−1.081V，Vpp/2并不能代表两个实际峰值。

理想纯幅度缩放下，新负载要保证绝对峰值≤1V，比例最多约{1/max(abs(rc['minimum']),abs(rc['maximum'])):.4f}；留10%峰值余量时最多约{.9/max(abs(rc['minimum']),abs(rc['maximum'])):.4f}。实际无源衰减器会反过来改变源负载，不能把这个比例直接定成最终电阻比。

## 功耗情景（新负载RC近似）

实算保留模块：载波三级42.72438mW，LM393前端17.24275mW。其余是预算假设：基带缓冲10mW、转换器电池侧静态5mW、效率为表内假设。AD835动态部分用理想B类驱动估算，不是实测值。

| AD835静态mA | 假设效率 | 电池mW | 距500mW余量 | 保留7805正轨+独立反相mW |
|---:|---:|---:|---:|---:|
'''
for x in rows:text+=f"|{x['iq_ma']}|{x['efficiency']:.0%}|{x['battery_mw']:.2f}|{x['margin_to_500_mw']:.2f}|{x['retain_7805_plus_battery_inverter_mw']:.2f}|\n"
text+='''
25mA/85%情景约441mW，不是通过结论；额外RF缓冲、电池内阻损耗、器件公差、转换器真实轻载效率或动态损耗都会消耗余量。全温26mA情景单列。7805情景按其历史预算8mA静态上限、负轨从电池独立转换、缓冲预算正负各半计算；若负轨从正5V生成，不能沿用这一列。

供电方案尚未选到具体器件，输入功率没有实测闭环。RX外供，不包括在TX评分功耗内。无输出级、RF接口和电源资格验证时不得给整机验收。

## 数值分析复现

运行 `py -3 -X utf8 scripts/finalize.py` 从保留RAW重新分析，不重跑求解器。
运行 `py -3 -X utf8 scripts/preflight.py` 重跑三个独立接口测试。
不采用AM01旧非均匀采样直接数字滤波的包络结果作为本阶段幅度基准。
'''
(R/'results/接口与功耗汇总.md').write_text(text,encoding='utf8')

# Analytic zero-low reference is separate from actual source/device results.
analytic=[]
for a in (1,2,3,4):
    for duty in (.1,.3,.5):
        hi=2*(.6+.1*a);lo=1.2
        analytic.append(dict(status='ANALYTIC_ZERO_LOW_REFERENCE_ONLY',amplitude=a,duty=duty,
            high_vpp=hi,low_vpp=lo,m=(hi-lo)/(hi+lo),mean_envelope_vpp=duty*hi+(1-duty)*lo,
            p50_mw=1000*(duty*hi**2+(1-duty)*lo**2)/400))
with (R/'results/数学参考_不是器件测试.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=analytic[0]);w.writeheader();w.writerows(analytic)
plan=[dict(topology=t,amplitude_vpp=a,duty_pct=d,resistance_ohm=r,capacitance_pf=c,
    status='BLOCKED_OFFICIAL_MODEL',actual_vm_low=None,actual_vm_high=None)
    for t in ('A','B') for a in (1,2,3,4) for d in (10,30,50)
    for r,c in ((2000,10),(10000,10),(50,0),(50,2),(50,5),(50,10))]
(R/'results/器件矩阵_待执行.json').write_text(json.dumps(plan,indent=2),encoding='utf8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(2,1,figsize=(10,6),layout='constrained')
for name,label in [('osc_reference','Original: 2k || 10pF'),('osc_yz_rc','RC proxy: 37.5k || 4pF')]:
    d=p.read_raw(R/'results'/f'{name}.raw');t=d['time'];m=t>=t[-1]-200e-9
    ax[0].plot((t[m]-t[m][0])*1e9,d['v(out)'][m],label=label,lw=1.3)
ax[0].axhline(1,color='r',ls='--',lw=.8);ax[0].axhline(-1,color='r',ls='--',lw=.8)
ax[0].set(xlabel='Time in final 200 ns',ylabel='Carrier voltage (V)',title='Interface precheck only - NO AD835 model')
ax[0].legend();ax[0].grid(alpha=.2)
for q in (16,25,26):
    sub=[x for x in rows if x['iq_ma']==q]
    ax[1].plot([100*x['efficiency'] for x in sub],[x['battery_mw'] for x in sub],'-o',label=f'AD835 Iq={q}mA scenario')
ax[1].axhline(500,color='r',ls='--',label='500 mW limit')
ax[1].set(xlabel='Assumed conversion efficiency (%)',ylabel='Estimated battery power (mW)',title='Conditional budget; converter and AD835 dynamic currents NOT verified')
ax[1].legend(fontsize=8);ax[1].grid(alpha=.2)
fig.savefig(R/'results/interface_and_budget.png',dpi=160);plt.close(fig)

before=json.loads((R/'sources/protected_before.json').read_text(encoding='utf8'))
after=p.snapshot();changes=[k for k in set(before)|set(after) if before.get(k)!=after.get(k)]
(R/'results/protection_check.json').write_text(json.dumps(dict(count=len(before),changes=changes,
    scope='cir,py,md,json,lib,mod in six protected historical trees'),indent=2),encoding='utf8')
assert not changes,changes
print('Protected historical source files unchanged:',len(before))
