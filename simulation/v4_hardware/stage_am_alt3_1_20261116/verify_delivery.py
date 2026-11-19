"""Numerical provenance and frozen-circuit checks, not physical acceptance."""
from run_nec import *
import hashlib,sys

rows=json.loads((ROOT/'driver_tabletop_summary.json').read_text())
lines=['# 冻结驱动回填结果｜AM-ALT.3.1\n',
'2026-11-16。新建独立负载夹具；冻结电路未修改。天线为桌面8×0.50 m水平径向线，31 MHz有损地面示例阻抗4.0876−j679.77 Ω。\n',
'| Q | 最大步长/ns | 载波基波RMS/mA | 全波形RMS/mA | 高平台基波RMS/mA | 载波/MHz | 电池预算/mW |\n|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:
 lines.append(f"| {r['Q']} | {r['step_ns']} | {r['carrier_fundamental_rms_mA']:.6f} | {r['total_time_weighted_rms_mA']:.6f} | {r['high_plateau_fundamental_rms_mA']:.6f} | {r['carrier_Hz']/1e6:.9f} | {r['battery_budget_mW']:.3f} |")
a,b=[r for r in rows if r['Q']==60]
err=abs(a['carrier_fundamental_rms_mA']/b['carrier_fundamental_rms_mA']-1)
lines += [f'\nQ60 的0.25→0.125 ns载波电流相对变化为{err*100:.5f}%，满足本轮电流细化判据<0.1%；载波频率仍变化{abs(a["carrier_Hz"]-b["carrier_Hz"]):.1f} Hz，因此**不声称本轮已经重新完成频率零步长收敛**。旧阶段更细步长证据不能冒充本负载的新运行。',
'\n统计窗取约1.89～1.99 ms的两个完整20 kHz周期，用非均匀时间权重和基波拟合；并非实测，也不是冷启动验收。电池预算沿用9 V线性稳压、额外8 mA稳压器地电流假设。',
'\n单频等效负载用L=3.48995986 µH、C=7.55259929 pF、R=4.0876+679.77/Q Ω，再保留原10 Ω。Q是31 MHz有效串联Q；没有把寄生再重复加在已定义的有效L上。完整NEC频率点见selected_environment.json，当前R-C近似只用于局部载波与邻近边带，不是全频带宏模型。',
'\n**电流增加不等于6 m链路已通过。** 上半空间辐射、水平传播、接收天线有效高度、实际调制度、教室环境与接收灵敏度需统一回算。原3.75～5.30 mA区间不再直接作为新结构合格线。',
'\n用户补充“桌面安装”之前启动的下倾负载试跑已停止，残留在driver/，不作为本交付证据。正式结果只取driver_tabletop/。']
(ROOT/'驱动回填结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

checks={}
frozen=json.loads((ROOT/'frozen_driver_sha256.json').read_text())
for filename,digest in frozen.items():assert hashlib.sha256(Path(filename).read_bytes()).hexdigest()==digest
checks['frozen_original_unchanged']=True
base=Path(next(iter(frozen))).read_text(encoding='utf-8')
def normalize(text):
 return '\n'.join(x for x in text.splitlines() if not re.match(r'^(LTUNE |RANT |CANT |tran |write )',x))
for r in rows:
 p=ROOT/'driver_tabletop'/f"q{r['Q']}_s{r['step_ns']}.cir"
 assert normalize(p.read_text(encoding='utf-8'))==normalize(base)
checks['only_load_step_output_changed']=True
bench=json.loads((ROOT/'benchmarks.json').read_text());assert bench[0]['pass']
checks['official_example_error_ohm']=abs(complex(bench[0]['R']-82.6979,bench[0]['X']-46.306))
assert bench[-1]['image_relative_error']<.03
checks['image_test_relative_error']=bench[-1]['image_relative_error']
table=json.loads((ROOT/'tabletop.json').read_text())
free=next(x for x in table if x['name']=='desk_r8_l0.5_n120_free')
res=abs(free['radiated_fraction']+free['loss_fraction']-1)
assert res<.05;checks['free_space_power_balance_residual']=res
m=[next(x for x in table if x['name']==f'desk_r8_l0.5_n{n}_soil') for n in [80,120]]
for k in ['R','X']:assert abs(m[0][k]/m[1][k]-1)<.01
checks['impedance_mesh_change_R_pct']=abs(m[0]['R']/m[1]['R']-1)*100
checks['impedance_mesh_change_X_pct']=abs(m[0]['X']/m[1]['X']-1)*100
loaded=json.loads((ROOT/'loaded_crosscheck.json').read_text())
assert all(abs(x['R_error'])<.01 and abs(x['X'])<.02 for x in loaded)
checks['NEC_loaded_circuit_crosscheck']=True
assert err<.001;checks['driver_current_step_change_pct']=err*100
checks['physical_antenna_measured']=False;checks['coil_Q_verified']=False;checks['wireless_6m_pass']=False
save('verification',checks)
# Include official reference files, source, executable, models, raw and reports.
# Exclude intentionally cancelled pre-steering driver trial outputs.
manifest={}
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or p.name=='evidence_sha256.json' or '__pycache__' in p.parts or 'driver' in p.relative_to(ROOT).parts:continue
 manifest[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
save('evidence_sha256',manifest)
print(json.dumps(checks,indent=2))
print('Evidence files:',len(manifest))
