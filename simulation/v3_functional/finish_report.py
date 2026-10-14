from pathlib import Path
import json, shutil, zipfile
from measure import read_raw
HERE=Path(__file__).resolve().parent
WORK=Path('D:/ms_xsp/v3_20k')
d=read_raw(WORK/'quick_A4.raw')
assert abs(d['time'][-1]-.0002)<1e-10
assert 'Error:' not in (WORK/'quick.log').read_text(errors='replace')
assert 'Out of memory' in (WORK/'full_retry.log').read_text(errors='replace')
status={'native_projects':'opened and resaved in Multisim 14.3; parameters verified','multisim_200us':{'completed':True,'points':len(d['time']),'end_time_s':float(d['time'][-1])},'multisim_5ms':{'completed':False,'error':'Out of memory','log':'debug/v3_20k/full_retry.log'},'steady_amplitude_sweep':'LTspice, 4.8-5 ms, engineering Schottky approximation'}
(HERE/'validation_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
report=HERE/'使用说明与验证结果.md'
addition=f'''\n## Multisim 引擎复核与已知限制\n\n200 µs 快速检查已完整完成，共 {len(d['time']):,} 点，日志无错误。网表与修改工程使用同一组参数。可直接打开 `AM_20k_D50_A4V_V3_quick200us.ms14` 运行，观察 20 kHz、31 MHz AM 和检波响应；此窗口仍处于启动阶段，不能用其最高电压或全窗口峰峰值验收稳态幅度。\n\n0–5 ms 的全程运行尝试明确报 `Out of memory`，没有取得完整波形。非零 TSTART 的尝试也未完成，不列为通过。保留四档 5 ms 工程供继续调试，但不能承诺本机 GUI 可以完成长时间显示。\n\n因此本文四档稳态幅度表是 **LTspice 的同参数网表结果**，不是 Multisim 5 ms 实测结果。本轮 XSPICE 通过项为 200 µs 启动检查；原生工程通过项为打开、保存和参数回读。\n\n日志统一保存到 `../../debug/v3_20k/`：`quick.log` 为成功短仿真，`full_retry.log` 为长仿真内存不足。原始短波形：`D:/ms_xsp/v3_20k/quick_A4.raw`。\n'''
report.write_text(report.read_text(encoding='utf-8')+addition,encoding='utf-8')
debug=HERE.parents[1]/'debug/v3_20k'
debug.mkdir(exist_ok=True)
for name in ['full_retry.log','quick.log','steady.log','final.log','baseline_run.log']:
    if (WORK/name).exists():shutil.copy2(WORK/name,debug/name)
shutil.copy2(HERE/'validation_status.json',debug/'validation_status.json')
(debug/'说明.md').write_text('200 us 短仿真成功，见 quick.log。5 ms 全程仿真报 Out of memory，见 full_retry.log；没有完整的 5 ms Multisim 波形。其他空日志/失败尝试不计作通过。稳态幅度数据来自 LTspice，见 simulation/v3_functional/使用说明与验证结果.md。',encoding='utf-8')
files=list(HERE.glob('AM_*.ms14'))+[report,HERE/'amplitude_linearity.png',HERE/'duty_endpoints.png',HERE/'native_verification.json',HERE/'validation_status.json',debug/'quick.log',debug/'full_retry.log']
with zipfile.ZipFile(HERE/'AM_20k_V3_Multisim.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in files:z.write(f,f.name)
print(json.dumps(status),flush=True)
