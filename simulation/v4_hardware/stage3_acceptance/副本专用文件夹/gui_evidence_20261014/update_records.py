"""Back up current records, then apply the evidence-based S03-04 correction."""
from pathlib import Path
import hashlib
import json
import re
import shutil

OUT = Path(__file__).resolve().parent
KEEP, BASE = OUT.parent, OUT.parent.parent
ROOT = BASE.parents[2]
BACKUP = OUT / 'records_before'
BACKUP.mkdir(exist_ok=True)
report = '副本专用文件夹/gui_evidence_20261014/S03_04_GUI与加权复核报告.md'
records = [ROOT/'项目管理/02_当前阶段目标.md', ROOT/'项目管理/03_当前实现状态.md',
           BASE/'S03_04_冷启动排查记录.md', KEEP/'README.md', KEEP/'S03_04_试验台账.md',
           BASE/'S03_04_步骤1_控制行差集.md', KEEP/'S03_04_步骤1_控制行差集.md']
manifest = []
for i, path in enumerate(records):
    dest = BACKUP / f'{i+1:02d}_{path.name}'
    if dest.exists():
        raise RuntimeError('Backup already exists; refusing to rewrite history: '+str(dest))
    shutil.copy2(path, dest)
    manifest.append({'source': str(path), 'backup': str(dest),
                     'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()})
(BACKUP/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')


def save(path, text):
    path.write_text(text, encoding='utf-8', newline='\n')


path = records[0]
t = path.read_text(encoding='utf-8')
t = re.sub(r'阶段状态：.*?\n关联文档：',
    '阶段状态：进行中；**S03-01～03已完成，S03-03已结项。S03-04仍待验收：命令行引擎支持冷启动功能，但7 ms末五周期均值跨度15.372 mV（幅度的0.3193%），未通过原定0.1%筛查。2026-10-14 GUI直接20 μs复现失败，实际停在225.797635 ns；失败`.gra`已保存。** 2 Vpp线性与其余工况未开始。\n关联文档：',t,count=1)
new_section = '''### S03-04：启动过程验证

- [x] 声明测试条件：完整功能模型、理想供电，无真实上电斜坡；4 Vpp/50%；用户自定义 UIC，C111/C115/CBB 显式零初值。
- [x] 冷启动功能已有命令行引擎证据：5/7 ms 结果显示输出能够建立；4.218 ms 是最后一次低于 1 V 的事件时间，不能称为稳定时间。
- [x] 重算 7 ms 末尾五个完整周期：V2 robust 幅度 4.814008 Vpp、时间加权均值 4.417497 V、周期均值跨度 15.372227 mV。
- [ ] 启动后稳定性：均值跨度占幅度 0.319323%，未达到原定 0.1% 临时重复性筛查；撤回“6.5 ms 已稳定”和“S03-04 已通过”。
- [x] GUI 直接点击 20 μs 试验并归档失败 `.gra`：TSTEP=TMAX=1 ns，四条曲线各 563 点，实际终点 225.797635 ns，报瞬态不收敛。输入工程与 COM 矩阵成功副本哈希完全一致。
- [ ] GUI 成功复现：尚未达到 20 μs，不能用 COM 或命令行结果替代。
- [ ] TSTART 短窗对照与从零计算的长窗尾段记录：尚未执行；先确认本机行为，再用于控制保存量。

证据来源分开记录：短窗矩阵是 COM `RunSimulation` 驱动；5/7 ms 是 `source` + `tran` 命令行引擎；本轮 20 μs 是原生 GUI 点击 Run。控制文本一致不证明有效求解设置一致。7 ms 成功、10 ms 失败不证明 7 ms 是上限。

本轮不追查求解器内部机理。按用户次序，稳定性确认后再保持接收增益和负载不变做 2 Vpp/50%，随后补其余档位。当前原生 GUI 前置检查失败，长窗及线性测试未启动。

详见[本轮 GUI 与加权复核报告](../simulation/v4_hardware/stage3_acceptance/副本专用文件夹/gui_evidence_20261014/S03_04_GUI与加权复核报告.md)、[冷启动记录](../simulation/v4_hardware/stage3_acceptance/S03_04_冷启动排查记录.md)。先前版本已备份，历史原始数组不变。

'''
t = re.sub(r'### S03-04：启动过程验证.*?(?=### S03-05：)', lambda _:new_section,t,flags=re.S,count=1)
t = re.sub(r'\*\*S03-03已结项；当前待解决的是S03-04启动收敛.*?\n\n',
    '**S03-03已结项；S03-04冷启动功能有证据，稳定性和GUI成功证据待补。** 20 μs GUI复现失败已留档，先恢复该前置检查，再做TSTART对照及长窗稳定性；稳定性确认后做2 Vpp减半线性。暂不继续追查求解器内部机理。\n\n',t,flags=re.S,count=1)
save(path,t)

path = records[1]
t = path.read_text(encoding='utf-8')
t = re.sub(r'\*\*当前可运行基线：.*?(?=\n\n当前工程)',
    '**当前可运行基线：V4_3_REPAIRED。S03-01～03完成，预充电5 ms引擎预检与2 ms原生GUI复跑结论保留。S03-04仍待验收：冷启动功能有命令行引擎证据，但7 ms末五周期偏置跨度15.372 mV（幅度的0.3193%），未通过0.1%临时筛查。2026-10-14使用与COM矩阵逐字节相同的副本，GUI点击20 μs运行在225.797635 ns不收敛；已保存失败`.gra`、参数截图及实际零初值网表。2 Vpp线性及其余工况尚未开始。**',t,flags=re.S,count=1)
lines = t.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| 冷启动“无法收敛” |'):
        lines[i] = '| 冷启动“无法收敛” | COM短窗矩阵有通过记录，不能推广为GUI通过。本轮原生GUI在TSTEP=TMAX=1 ns时仍停于225.797635 ns；有效求解设置等同性未证明，机理暂不追查 |'
    elif line.startswith('| 冷启动“没有启动” |'):
        lines[i] = '| 冷启动“没有启动” | 2 ms不足以支持该判断；5/7 ms命令行引擎数据支持能够启动。7 ms时间加权重算未通过末五周期重复性筛查，撤回“6.5 ms已稳定”；10 ms失败不证明7 ms为上限 |'
    elif line.startswith('| “引擎用了另一套 reltol/trtol” |'):
        lines[i] = '| “引擎用了另一套 reltol/trtol” | 尚不能认定或排除。部分set不改变结果、option报错，不能证明与GUI实际设置相同；只保存已测现象，不推断完整有效配置 |'
    elif line.startswith('下一项：补齐冷启动的原生 GUI'):
        lines[i] = '下一项：GUI 20 μs成功复现仍待解决（本轮失败证据已齐）；之后做TSTART短窗对照、冷启动长窗尾段稳定性，确认后再做2 Vpp/50%线性及其余档位。暂不追查求解器内部机理。'
    elif line.startswith('| 2026-10-14 | 按 S03-04 步骤'):
        lines[i] = '| 2026-10-14 | 历史控制行与步长试验（来源标签和结论已更正） | 短窗矩阵来自COM；长窗来自命令行引擎。历史“原生GUI通过／有效选项相同”不成立；保留原数据和备份供复核 |'
    elif line.startswith('| 2026-10-14 | 冷启动窗口延长试验完成'):
        lines[i] = '| 2026-10-14 | 历史7 ms成功／10 ms失败记录 | 保留两次已测结果；撤回“6.5 ms稳定／S03-04通过”，不能认定7 ms为上限 |'
t = '\n'.join(lines)+'\n'
t += '\n2026-10-14 本轮复核：[GUI与加权复核报告](../simulation/v4_hardware/stage3_acceptance/副本专用文件夹/gui_evidence_20261014/S03_04_GUI与加权复核报告.md)。GUI失败曲线各563点，已确认页标题与工程归属；11份源文件及只读备份SHA-256全部一致。本轮只在独立工程副本运行，更新状态记录前已备份。\n'
save(path,t)

# Replace the outdated acceptance narrative; retain its full prior version in backup.
save(records[2], '''# S03-04 冷启动排查记录

更新日期：2026-10-14。**状态：冷启动功能有命令行引擎证据，稳定性与原生 GUI 成功证据待补；S03-04 未验收。** S03-03预充电标称结论保留。

本轮完整报告：[GUI与时间加权复核](副本专用文件夹/gui_evidence_20261014/S03_04_GUI与加权复核报告.md)。本文件更新前的完整历史版本保存在[记录备份](副本专用文件夹/gui_evidence_20261014/records_before/03_S03_04_冷启动排查记录.md)，其中被撤回的推断不再作为当前结论。

## 1. 证据来源与边界

| 证据 | 入口 | 可支持的结论 |
|---|---|---|
| matrix3_results.json、confirm/ | COM RunSimulation 驱动工程 | 所测COM调用的状态记录，不能标成GUI点击Run通过 |
| Z_2ms、L_5ms、L_7ms | 命令行引擎 source + tran | 这些窗口的完整模型数值结果；5/7 ms支持能启动，不能证明GUI入口通过 |
| 本轮S03_GUI_COLD_20us.gra | 原生GUI点击Run、Grapher保存 | 20 μs目标运行失败，实际终点225.797635 ns，四条曲线各563点 |

控制行的请求文本相同不证明有效设置相同。部分 `set` 不改变已测结果、`option` 报错，均不能证明 GUI 与命令行引擎生效配置等同。历史“原生GUI单变量矩阵”的标签更正为“COM矩阵”。不再宣称已定位冷启动不收敛根因。

## 2. 原生 GUI 20 μs 复现（本轮新增）

- 输入副本与 COM 成功矩阵 `V_1n_1n.ms14` 完全同哈希：`10b971880847cbfb2c9d0b3e5c780c7856ba200998aa53d8e4ca8d4e69a5ac73`。
- TSTEP=TMAX=1 ns，TSTART=0、TSTOP=20 μs、用户自定义 UIC；实际 SPICE 网表 C111=0、C115=-0、CBB=0。
- 原生GUI点击Run后，报 `Unable to converge during transient analysis`、`Simulation canceled`。
- `.gra` 实际终点 `2.257976350349652e-7 s`；一页、页标题对应本轮工程、四条曲线各563点。不能把横轴20 μs刻度当成已计算到20 μs。
- 首个正时间10 ps：V(bb_in)=14.112384 μV、V(v2)=6.136117 μV、V(bbo)=81.397 mV，未复现4.5 V预充电起点。
- [失败波形](副本专用文件夹/gui_evidence_20261014/S03_GUI_COLD_20us.gra)、[参数截图](副本专用文件夹/gui_evidence_20261014/01_20us_parameters.png)、[失败截图](副本专用文件夹/gui_evidence_20261014/04_20us_gui_failure.png)、[实际网表](副本专用文件夹/gui_evidence_20261014/S03_GUI_COLD_20us_actual.cir)、[审计JSON](副本专用文件夹/gui_evidence_20261014/gui_20us_audit.json)。

## 3. 冷启动长窗的正确判定

2 ms窗口不足以认定不能启动。5 ms输出已建立，4.218 ms是最后一次低于1 V的电平事件；不是稳定时间。7 ms完整数据有7,127,505点，沿用原S03方法重算末五完整周期：

| 指标 | 冷启动7 ms | 预充电标称5 ms |
|---|---:|---:|
| V2 robust幅度 | 4.814008 Vpp | 4.816023 Vpp |
| 时间加权均值 | 4.417497 V | 4.496041 V |
| 周期均值跨度 | 15.372227 mV | 0.350986 mV |
| 均值跨度/幅度 | 0.319323% | 0.007288% |
| 0.1%临时重复性筛查 | 未通过 | 通过 |

原 `cold7ms_analysis.py` 使用样本普通平均。“6.5 ms已稳定”“收敛到标称”“S03-04通过”均撤回。均值进入标称2%范围不能替代原0.1%重复性筛查。[加权逐周期数据](副本专用文件夹/gui_evidence_20261014/weighted_7ms_review.json)是当前测量依据，旧分析和图仅作历史材料。

7 ms引擎成功、10 ms报 `Internal simulation error` 仅限定已测结果；不认定7 ms为上限，也不认定10 ms必然受内存限制。

## 4. 本轮工作边界和下一步

本轮不追查求解器内部机理，不调整电路或接收增益。GUI短窗前置检查失败，因此TSTART短窗对照、7 ms仅保存6.5–7 ms的GUI运行、2 Vpp线性测试均未开始。

后续顺序保持：先取得GUI 20 μs通过证据；短窗验证TSTART只影响结果报告且前段仍从零计算；再记录长窗末段并按原判据检查稳定性。确认后固定接收增益和负载做2 Vpp/50%，与已验收4 Vpp比较，随后补其余档位。TSTART节约保存量不能预先保证解决内存问题。

## 5. 副本与复核纪律

所有本轮运行工程和新增证据均在 `副本专用文件夹/gui_evidence_20261014/`。源 `.ms14` / `.cir` 和既有原始波形未改；[11份源文件哈希](副本专用文件夹/gui_evidence_20261014/source_hash_verification.json)与只读引用全部一致。状态文档更新前逐份备份，见 `records_before/manifest.json`。
''')

path = records[3]
t = path.read_text(encoding='utf-8')
t = t.replace('（7,127,505 点，收敛判定依据）','（7,127,505 点；加权复核未通过重复性筛查）')
t = t.replace('**冷启动 5 ms 分析：V(v2) 于 4.218 ms 稳定输出，末段均值 4.026 V**','历史普通样本平均分析；4.218 ms为最后一次低于1 V的事件，不是稳定时间')
t = t.replace('**7 ms 冷启动收敛分析：末段 V(v2) 4.4492 V vs 标称 4.5322 V（−83 mV）**','历史普通样本平均分析；“6.5 ms稳定／通过”已撤回，以本轮时间加权结果为准')
t = t.replace('证实引擎 `set`/`option` 对求解器无效','已测选项通道现象；不证明GUI与引擎有效配置相同')
t = t.replace('步骤 1 门禁：控制行差集为空','历史请求文本差集；不等于有效设置一致')
banner = '\n> 2026-10-14更正：短窗矩阵来自COM，5/7 ms来自命令行引擎。本轮GUI点击20 μs在225.797635 ns失败；7 ms末五周期偏置跨度0.3193%，S03-04未通过。[最新报告](gui_evidence_20261014/S03_04_GUI与加权复核报告.md)。状态文档另已备份后更正，源工程与旧原始波形不变。\n'
t = t.replace('\n\n', '\n'+banner+'\n',1)
save(path,t)

path = records[4]
t = path.read_text(encoding='utf-8')
t = t.replace('说明：本轮通过 **COM 调用工程自身的瞬态分析**取得结果，该路径不产生 `.gra`（Grapher 保存是 GUI 内操作）。\n因此下表的“`.gra` 点数”一列标注为 **未产生**，并用引擎 `.raw` 点数与首非零点代替，两者时间窗与设置一致。\n原生 `.gra` 需在 GUI 内以同一副本跑一次补齐（见第 7 节）。',
    '来源更正：A/B为COM调用记录，C/D/E为命令行引擎记录；引擎数据只作独立参照，不能代替COM或GUI的采样证据，有效设置等同性未证明。2026-10-14本轮GUI直接运行失败，原生`.gra`已保存，见G节。')
t = t.replace('## A. 原生 GUI 工程（COM 驱动工程自身分析）','## A. COM 驱动工程记录（不是 GUI 点击运行）').replace('## B. 单变量矩阵（各重复 2 次，原生 GUI）','## B. 单变量矩阵（各重复 2 次，COM 驱动）')
t = t.replace('## D. 引擎通道探测（结论：`set`/`option` 对求解器无效）','## D. 引擎通道探测（仅限已测调用，不证明有效设置一致）')
t = t.replace('（疑为点数/内存上限）','（失败原因未确认，不推断7 ms为上限）')
t = t.replace('→ **收敛到标称工作点**','→ **旧普通平均描述；稳定性结论撤回，时间加权复核未通过**')
t = t.replace('5 ms 显示冷启动约 4.2 ms 建立输出；**7 ms 显示它在约 6.5 ms 收敛到预充电标称**。','5 ms支持输出能够建立；4.218 ms电平交越不是稳定时间。**7 ms加权复核偏置跨度15.372 mV（0.3193%），未达到0.1%临时重复性筛查。**')
t += '''
## G. 2026-10-14 原生 GUI 20 μs（本轮新增）

| 工程副本 | 变更项 | 失败时刻 | 错误原文 | 原生gra点数／首非零点 |
|---|---|---|---|---|
| gui_evidence_20261014/S03_GUI_COLD_20us_input.ms14 | 与COM成功矩阵输入逐字节相同，TSTEP=TMAX=1 ns | 225.797635 ns，未达到20 μs | Unable to converge during transient analysis; Simulation canceled | 1页、4曲线各563点；t=10 ps时BB_IN=14.112384 μV、V2=6.136117 μV |

[完整报告](gui_evidence_20261014/S03_04_GUI与加权复核报告.md)。GUI前置检查未通过，TSTART对照、长窗尾段GUI和2 Vpp线性尚未运行。旧版台账已备份。
'''
save(path,t)

for path in records[5:]:
    t = path.read_text(encoding='utf-8')
    banner = '\n> 2026-10-14复核更正：本记录的“差集为空”仅指当时抽取的请求文本；部分set不生效，因此不能证明GUI、COM和命令行引擎的有效求解设置相同。历史短窗矩阵是COM入口。本轮GUI在1 ns/1 ns、20 μs目标下于225.797635 ns失败，详见最新GUI与加权复核报告；旧控制文本保留供追溯，不作为已解除GUI故障的依据。\n'
    t = t.replace('\n\n', '\n'+banner+'\n',1)
    save(path,t)

after = [{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in records]
(OUT/'updated_records_manifest.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Updated {len(records)} records; backed up {len(manifest)} prior versions.')
