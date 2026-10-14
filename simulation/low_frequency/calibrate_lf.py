"""Calibrate the corrected discrete LF circuit in LTspice.

The imported COMP_OC and OP18 are educational finite-bandwidth models.
The 44.8 kohm V1 load represents the modulation branch's AC loading only.
"""
from pathlib import Path
import sys, json, csv
import numpy as np
from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from build_simulation import lf_net, run_spice, read_raw, metrics


def net(rfreq, duty_voltage, amp_pos):
    text = lf_net(rfreq=rfreq, duty_voltage=duty_voltage, amp_pos=amp_pos)
    text = text.replace('R11 PWM_RAW AMP_TOP 8.2k', 'R11 PWM_RAW AMP_TOP 5.6k')
    text = text.replace('RLOAD V1 0 1meg',
        '* AC-equivalent modulation load: R23 + (R21 || R22) ~ 44.8k.\n'
        '* This fixed resistance does not reproduce the Q3 nonlinear bias or C19 DC block.\n'
        'RACLOAD V1 0 44.8k\nRLOAD V1 0 1meg')
    return text


def evaluate(rfreq, duty_voltage=4.5, amp_pos=.9, filename='calibration_work.cir'):
    path = HERE / filename
    path.write_text(net(rfreq, duty_voltage, amp_pos), encoding='ascii')
    run_spice(path)
    data = read_raw(path.with_suffix('.raw'))
    return metrics(data), data


def calibrate():
    HERE.mkdir(exist_ok=True)
    rows, waveforms, freq_params = [], {}, {}
    # The amplitude section is purely resistive. Solve its two switch states
    # analytically, then verify both levels in every final transient run.
    load = 1 / (1 / 44800 + 1 / 1e6)
    def passive_vpp(position):
        top=max(1,10000*(1-position)); bot=max(1,10000*position)
        bottom=1/(1/bot+1/(1000+load))
        ratio=load/(1000+load)
        high=9*bottom/(2200+5600+top+bottom)*ratio
        low=(9*25/2225)*bottom/(2200*25/2225+5600+top+bottom)*ratio
        return high-low
    positions={a:brentq(lambda p:passive_vpp(p)-a,.05,.9998,xtol=1e-12) for a in (1,4)}
    for frequency in (21000, 22000):
        def frequency_error(resistance):
            _, data = evaluate(resistance)
            return metrics(data, node='v(sq_osc)')['frequency_hz'] - frequency
        rfreq = brentq(frequency_error, 27000, 42000, xtol=.1)
        _, initial = evaluate(rfreq)
        tri = initial['v(tri)'][initial['time'] >= .0006]
        vlo, vhi = float(np.min(tri)), float(np.max(tri))
        freq_params[str(frequency)] = {'rfreq_ohm':rfreq, 'tri_min_v':vlo, 'tri_max_v':vhi}
        for duty_percent in (10, 20, 30, 40, 50):
            target_duty = duty_percent / 100
            voltage = brentq(lambda v: evaluate(rfreq, v, .9)[0]['duty']-target_duty,
                             vlo+.1, vhi-.1, xtol=3e-5)
            for amplitude in (1, 4):
                position = positions[amplitude]
                vfinal = voltage
                name=f'{frequency//1000}kHz_D{duty_percent:02d}_A{amplitude}Vpp'
                actual, data = evaluate(rfreq, vfinal, position, name+'.cir')
                row = dict(case=name, target_frequency_hz=frequency,
                    target_duty_percent=duty_percent, target_vpp=amplitude,
                    rfreq_ohm=rfreq, r6_ohm=27000, vr1_ohm=rfreq-27000,
                    vduty_v=vfinal, amp_position=position,
                    vr3_top_ohm=max(1,10000*(1-position)),
                    vr3_bottom_ohm=max(1,10000*position),
                    frequency_hz=actual['frequency_hz'], duty_percent=actual['duty']*100,
                    vpp=actual['vpp'], low_v=actual['low_v'], high_v=actual['high_v'])
                row.update(frequency_error_percent=(row['frequency_hz']/frequency-1)*100,
                           duty_error_percentage_points=row['duty_percent']-duty_percent,
                           amplitude_error_v=row['vpp']-amplitude)
                rows.append(row); waveforms[name] = data
                print(f"{name}: f={row['frequency_hz']:.4f} Hz, D={row['duty_percent']:.5f}%, Vpp={row['vpp']:.7f}",flush=True)
    info = {'simulator':'LTspice batch, ASCII raw, actual transient simulation',
        'models':'COMP_OC and OP18 educational approximations, NOT manufacturer macromodels',
        'changes':[
            'U1A positive input: weighted TRI/SQ_OSC node; negative input: VREF.',
            'R4 SQ_OSC to HYST=30k; R5 TRI to HYST=10k.',
            'R6 nominal 27k plus VR1 nominal 20k; calibrated total RFREQ in each case.',
            'R11 reduced from 8.2k to 5.6k; LM393 output modeled as open collector with 2.2k pull-up.',
            'RACLOAD=44.8k from V1 to ground, representing the modulation branch AC-equivalent loading.',
            'VDUTY and VR3 calibrated separately per operating point.'],
        'measurement': {'window_seconds':[.0006,.0012],
            'vpp':'98th minus 2nd percentile of sampled V1',
            'frequency':'median of successive rising 50%-amplitude crossings',
            'duty':'median rising-to-next-falling width / median period'},
        'limits':[
            'COMP_OC has a 100ns input pole, 25-ohm on resistance, and no manufacturer propagation-delay model.',
            'OP18 is a limited-output single-dominant-pole model; no guaranteed slew rate, startup, or full rail behavior.',
            '4.5V reference and supply are ideal; startup and battery droop are not validated.',
            '44.8k is a linear AC-equivalent load and excludes Q3 nonlinear bias and capacitor startup.',
            'Parameter precision is numerical calibration accuracy, not physical component accuracy.',
            'No RF/wireless distance claim follows from these LF runs.'],
        'frequency_calibration':freq_params, 'cases':rows}
    (HERE/'low_frequency_results.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    with (HERE/'low_frequency_results.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    available={f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.family'] = next((n for n in ('Microsoft YaHei','SimHei','Noto Sans CJK SC') if n in available),'DejaVu Sans')
    plt.rcParams['axes.unicode_minus']=False
    for frequency in (21000,22000):
        fig,axes=plt.subplots(5,2,figsize=(14,12),sharex=True)
        fig.patch.set_facecolor('#f5f8fc')
        for row in [r for r in rows if r['target_frequency_hz']==frequency]:
            i=(row['target_duty_percent']//10)-1; j=0 if row['target_vpp']==1 else 1
            ax=axes[i,j]; data=waveforms[row['case']]
            t=data['time']; start=.0008; m=(t>=start)&(t<=start+3/frequency)
            ax.plot((t[m]-start)*1e6,data['v(v1)'][m],color='#146ab3' if j==0 else '#a84419',lw=1.3)
            ax.set_title(f"D={row['duty_percent']:.3f}%  |  V1={row['vpp']:.4f} Vpp",fontsize=10,loc='left')
            ax.set_ylim(-.15,4.6 if j else 1.3); ax.set_ylabel('V1 / V')
            ax.grid(color='#dfe5ef',alpha=.75); ax.spines[['top','right']].set_visible(False)
            if i==4: ax.set_xlabel('时间 / μs')
        fig.suptitle(f'{frequency//1000} kHz 低频模块：5 档占空比 × 1 / 4 Vpp\nLTspice 瞬态仿真 · 开集电极输出 · 44.8 kΩ 等效调制负载',fontsize=16,y=.985)
        fig.text(.5,.012,'教学近似模型；数值校准精度不代表实物精度。R11=5.6 kΩ，三角波环路已修正。',ha='center',fontsize=10,color='#465368')
        fig.tight_layout(rect=(.01,.035,.995,.935))
        fig.savefig(HERE/f'waveforms_{frequency//1000}kHz.png',dpi=170,facecolor=fig.get_facecolor())
        plt.close(fig)
    worst = {'frequency_error_percent':max(abs(r['frequency_error_percent']) for r in rows),
        'duty_error_percentage_points':max(abs(r['duty_error_percentage_points']) for r in rows),
        'amplitude_error_v':max(abs(r['amplitude_error_v']) for r in rows)}
    print('WORST',json.dumps(worst),flush=True)
    print('FREQUENCY_CALIBRATION',json.dumps(freq_params),flush=True)
    write_note(info,worst)


def write_note(info,worst):
    lines=['# 低频模块仿真与校准说明','',
        '本目录的 20 个工作点由 LTspice 实际执行瞬态仿真。参数是教学近似模型下的校准结果，不能作为实物元件容差保证。','',
        '## 必要改动','',
        '- U1A 的反相输入接 VREF；同相输入 HYST 经 R4=30k 接 SQ_OSC、经 R5=10k 接 TRI。原方案的环路方向会锁死。',
        '- R11 从 8.2k 改为 5.6k，保留开集电极的 2.2k 上拉；增加 44.8k 的线性等效调制负载。',
        '- 频率电阻采用 R6=27k 加 VR1=20k，表中 RFREQ 为两者总值。',
        '- 44.8k 近似 R23+(R21∥R22)，仅表示载波调制支路在基带频率处的交流负载，不表示完整 Q3 电路或直流偏置。','',
        '## 校准值','',
        '| 频率 | RFREQ 总电阻 | VR1 电阻 | TRI 最小/最大 |','|---|---:|---:|---|']
    for f,p in info['frequency_calibration'].items():
        lines.append(f"| {int(f)/1000:g} kHz | {p['rfreq_ohm']:.3f} Ω | {p['rfreq_ohm']-27000:.3f} Ω | {p['tri_min_v']:.4f} / {p['tri_max_v']:.4f} V |")
    lines += ['','各占空比和幅度的 VDUTY、VR3 上下段电阻请查 CSV；不得直接把 4.5V 视为校准后的 50%。','',
        '## 结果与使用','',
        f"- 20 点最大频率误差：{worst['frequency_error_percent']:.6f}%。",
        f"- 最大占空比误差：{worst['duty_error_percentage_points']:.6f} 个百分点。",
        f"- 最大幅度误差：{worst['amplitude_error_v']:.7f} V。",
        '- `21kHz_D10_A1Vpp.cir` 等 20 个命名文件可在 LTspice 打开并运行，查看 V(V1)、V(TRI)、V(PWM_RAW)。',
        '- `low_frequency_results.csv/json` 保存参数及实测指标；两张 PNG 展示全部 20 个工作点。',
        '- `calibrate_lf.py` 可重复校准，依赖父目录的 build_simulation.py、numpy/scipy/matplotlib 和已安装 LTspice。','',
        '## 模型边界','',
        '- COMP_OC 为开集电极教学模型，含 25Ω 导通电阻、100ns 输入极点；它不是 LM393B 厂家模型，也不等于厂家传播延迟。',
        '- OP18 为输出限幅、单主极点的教学运放模型，不包含完整压摆率、输出电流、启动与输入共模限制。',
        '- 电源和 4.5V 基准理想化；未据此验证电池功耗、RF 载波、天线或传输距离。',
        '- 指标使用 0.6～1.2ms 波形窗口；幅度取2%/98%分位差，频率和占空比用半幅交越时间测量。','']
    (HERE/'低频仿真说明.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    calibrate()
