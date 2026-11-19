# P1b｜AM-ALT.3 三项修订：覆盖率口径、v3 节点映射、旧 h_eff=h/2 脚本

日期：2026-11-16
工作区：`D:\实验报告文件夹\电路2`
性质：**三项文档与脚本修订。未运行新仿真，未改任何历史结论性数值。**
核验：`py -3 simulation\v4_hardware\stage_am_023_review_20261116\verify_p1b.py`

---

## 0. 三项修订一览

| # | 问题 | 处置 | 是否改历史文件 |
|---|---|---|---|
| 1 | 覆盖率 117.92%～166.66% 是**旧 13.824 Ω 无取样电阻模型**的数字，与"未证明覆盖"并列会被误读为全区间通过 | 索引层改为**双口径并列**，并给出正确读法 | 否（README、项目管理为活文件，但只加说明不改历史结论） |
| 2 | `v3` 节点在 `fin_nom.cir` 里仍被 `save`，但 `fin_nom.raw` 只有 6 个变量——`v(v3)` 静默消失 | 在 `final_verify.py` 加零伏别名源，恢复节点名；文档登记历史 raw 的正确读法 | 是（`final_verify.py` 是脚本，非结果；未被任何哈希清单保护） |
| 3 | `link_budget.py` 仍带已勘误的 `h_eff = h/2` | 修正并加详细弃用说明；同时修掉同一函数里的**第二个潜在缺陷**（峰值功率当平均功率） | 是（脚本，未受哈希保护） |

**为什么 `link_budget.py` 可以改、`AM02_3_报告.md` 不能改**：前者不在任何哈希清单里（逐一核对过全部 `*sha256*.json` 与 `*SHA256*.txt`），后者在 `SHA256SUMS.txt` 的 1,530 项中。改前者是修工具，改后者是毁证据。

---

## 1. 修订一：覆盖率口径

### 1.1 旧数字怎么来的

`03_AM-ALT.3_测量匹配与驱动复核.md:71`：

> 同一 RMS 口径作初步数值比较，覆盖率为 **117.92%～166.66%**，超出需求的余量为 **17.92%～66.66%**。

拆开看，这个区间的两端来自**同一个分子、两个不同的分母**：

```
分子 = 6.2499 mA  （final_verify.json 的 fin_nom.i_ant_rms_mA）
分母下限 3.749 mA  → 6.2499 / 3.749 = 166.71%
分母上限 5.302 mA  → 6.2499 / 5.302 = 117.92%
```

问题在**分子**：6.2499 mA 是 **R_ANT = 13.824 Ω、不含 10 Ω 取样电阻**的旧模型（`03_报告:73` 自己写明了这点）。而后续所有闭合工作都改用 **14.824 Ω + 10 Ω = 24.824 Ω**。两个模型的负载差 1.79 倍，电流当然不同。

### 1.2 同口径的正确覆盖率

改用含 10 Ω 的 `closure_sense10_metrics.json` / `d05_metrics.json`：

| 统计量 | 值 | 对 D=3（3.749 mA） | 对 D=1.5（5.302 mA） |
|---|---:|---:|---:|
| **载波基波 RMS** | 4.6409 mA | **123.8%** | **87.5%** |
| **全波形时间加权 RMS** | 4.8308 mA | **128.9%** | **91.1%** |
| 高平台基波 RMS | 5.9845 mA | — | **112.9%** |
| 高平台正弦等效 RMS | 6.0029 mA | — | **113.2%** |
| ~~旧 13.824 Ω 无取样~~ | ~~6.2499 mA~~ | ~~166.7%~~ | ~~117.9%~~ |

**正确读法**：

> 现驱动在**载波 RMS 口径**下覆盖 D=3 端（123.8%）但**不覆盖 D=1.5 端**（87.5%）；在全波形 RMS 口径下为 128.9% / 91.1%。**若只看高平台峰值电流，则两端都覆盖**（112.9%～113.2%）。
>
> 因此"是否覆盖需求"取决于**用哪个电流口径**，而这三个口径的物理含义不同：
> - **载波基波 RMS**：与"天线电流产生辐射"这一链路预算假设最一致（预算本身是正弦假设）。
> - **全波形 RMS**：含调制边沿的瞬态跌落，值偏大，不直接对应辐射。
> - **高平台峰值**：对应"最坏瞬时辐射能力"，但峰值不等于持续辐射。

`06_报告:70` 的原话是**正确的**：「**未证明现驱动在所扫范围内可靠覆盖需求**；功耗均低于500 mW不能替代电流/波形验收」。它没有说"覆盖率是 87.5%"，只是把结论降级了。本文补上具体数字，使这个降级有可核对的依据。

### 1.3 索引层已改（本次实际改动）

`README.md` 第 53 段与 `项目管理/03_当前实现状态.md` 现在都写明：

> 覆盖率应为 **87.5%～123.8%**（含 10 Ω 取样电阻的载波 4.6407 mA 对 3.749/5.3019），**不是** 117.92%～166.66%（后者用旧 13.824 Ω 无取样模型）。

`项目管理/03_当前实现状态.md` 第 9 行的历史条目保留原文（那是 2026-11-16 早些时候的记录），但在新增的 19:00 条目里给了修正口径。**两条并存，读者能看到演变过程，而不是被悄悄覆盖。**

### 1.4 一处需要澄清的措辞

`03_报告:71` 还写了「超出需求的余量为 **17.92%～66.66%**」并注明「"112%～167%"是算术笔误」。这句话本身没错（112% 确实与 117.92% 不自洽），但它容易让人以为"改对之后是 117.92%～166.66%"。

**实际是**：112%～167% 这个区间来自**另一套模型**（`02_勘误` §5 的"诚实区间 3.75～5.30 → 112%～167%"，用的是 6.2499 mA）。所以：

- **112%～167%**：旧模型（13.824 Ω）× 修正后需求区间 → 这是 `02_勘误` 的表格
- **117.92%～166.66%**：同上，去掉了取整
- **87.5%～123.8%**：新模型（24.824 Ω 含 10 Ω）× 修正后需求区间 → **这才是应与 `06_报告` 并列引用的数字**

三套数字对应两个模型，必须标清模型才能引用。本次已在索引层标注。

---

## 2. 修订二：v3 节点映射

### 2.1 问题

`01_AM-ALT.3_天线阻抗匹配与驱动能力报告.md:246–259` 把 v3 重新定义为：

> **v3 的正式定义改为：匹配网络之后、天线馈电点的电压。**

`stage_completion.json:121` 同样记载。但实际网表里：

- `netlists/fin_nom.cir:193` → `save v(v1) v(ef_e) v(v3) i(ltune) i(vsup) i(v5)`
- `results/fin_nom.raw` 头部实际变量只有 **6 个**：`time`、`v(ef_e)`、`i(ltune)`、`v(v1)`、`i(v5)`、`i(vsup)`

**`v(v3)` 静默消失，ngspice 未报错。** 原因：ROISO（1 kΩ 串联隔离电阻）被删除后，`tx_drv`/`v3` 这条支路整个不存在了——v3 对应的物理位置现在就是 `ef_e`。

**影响范围**：所有电流/电压指标都用 `v(ef_e)` 与 `i(ltune)` 计算，**未受数值影响**。受影响的只有"v3 这个词在当前网表里指向哪个节点"这一登记问题。

### 2.2 修订

**脚本侧**：`final_verify.py` 的网表模板加入零伏别名源：

```
QEF vcc drv_c ef_e 2N3904
REF ef_e 0 {p['ref']}
* --- v3 alias (added 2026-11-16, P1b) ---
* The stage defines v3 as the voltage at the antenna feed point AFTER the
* matching network (01 report section 8). Once ROISO was removed there is no
* longer a node literally named v3: the feed point is ef_e. A zero-volt source
* between v3 and ef_e restores the name without perturbing a single volt or
* ampere, so v(v3) == v(ef_e) exactly.
V3ALIAS v3 ef_e 0
LTUNE ef_e ant_n1 {L_TUNE_NH:.4f}n
```

**已在 ngspice-47 实测验证**该语法：

```
Node          Voltage
in                0
v3                0
v3alias#branch    0
...
meas tran a max v(v3)  ->  a = 9.99998e-01
```

零伏源正确镜像，且不改变任何电气量（`v3alias#branch = 0`）。

**为什么用零伏源而不是直接重命名 `ef_e` 为 `v3`**：
- 重命名会改变所有既有网表、所有 `save` 语句、所有下游脚本对 `v(ef_e)` 的引用（`closure_metrics.py:80`、`round2_analyse.py`、`round2_runs.py` 等 6 个脚本都在用 `v(ef_e)`）。
- 零伏源是**纯增量**：老网表照跑，新网表多一个节点名，两者都可用。
- ngspice 里零伏源是标准做法（电流探针也常这么加）。

**文档侧**：登记历史 raw 的正确读法。

> **历史 raw（2026-11-16 之前的 `fin_nom.raw`、`fin_det_*.raw` 等）没有 `v(v3)` 列。** 读这些文件时，v3 就是 `v(ef_e)`——两者在被测电路里是同一个物理点（匹配网络后的天线馈电点）。不要因为 `save` 语句里写了 `v(v3)` 就以为数据丢了；那是 ROISO 删除后遗留的无效节点名。

### 2.3 为什么这不是"改数据"

- 未重跑任何仿真。
- 未修改任何 `.raw`、`.json` 结果文件。
- 只改了 `final_verify.py` 的网表生成模板，**该改动只在下次重跑时生效**。
- 历史 raw 的 6 变量状态保持不变，其正确读法由本文登记。

---

## 3. 修订三：`link_budget.py` 的 h_eff 与第二处缺陷

### 3.1 缺陷 A（已知）：`h_eff = h/2`

修正前：

```python
h_eff   = h/2       [m]  (transmit and receive)     # docstring line 9
...
v_oc = e * (h_rx / 2)                                # line 37
```

`02_AM-ALT.3_勘误` 已用互易性判据证明这是错的：

```
D = 3  →  A_em = 3λ²/(4π) = 22.30 m²
A_em = η₀ h_eff² / (4 R_rad)  反解  →  h_eff = h
若 h_eff = h/2  →  A_em = 5.575 m²  →  反推 D = 0.749 < 1   ← 任何天线都不可能
```

取 h/2 相当于要求**两倍的场强**，故电流也翻倍。

### 3.2 缺陷 B（本次新发现）：把峰值功率当平均功率

修正前的 `field_from_current`：

```python
def field_from_current(i_peak, h=H_TX, r=6.0):
    p = i_peak ** 2 * radiation_resistance(h)      # ← 这是峰值功率
    return e_max_from_power(p, r), p
```

而 `e_max_from_power` 的注释明确写着 `P = r²E²/180` 中的 P 是**时间平均**功率（因为 `S_avg = E_peak²/(2η₀)` 已经带 1/2）。把峰值功率喂进去会让 P 大一倍，**E 高估 √2 = 1.414**。

**实测验证**（以审计报告的权威解为基准）：

| 计算方式 | P_avg | E_peak @6 m | 与审计对比 |
|---|---:|---:|---|
| 峰值功率代入（修正前） | 118.72 µW | 24.364 mV/m | **高估 √2** |
| 除以 2 后（修正后） | 59.359 µW | 17.228 mV/m | 审计 59.362 µW / 17.222 mV/m ✅ |

**这个缺陷此前没被发现，是因为它被缺陷 A 的 ×1/2（对电流需求）部分抵消了**——`link_budget.py` 是"给定电流算场强"，方向与需求反推相反，所以两个错误在数值上恰好接近抵消，脚本输出看起来"差不多对"。这正是为什么必须同时修：

- 缺陷 A 让 `V_oc` 偏小 2 倍（场强算对了但接收电压算小）
- 缺陷 B 让 `E` 偏大 √2 倍
- 净效果：`V_oc` 偏小 √2 倍——**看起来像个 3 dB 的"保守余量"，其实是两个错误叠加**

### 3.3 修正后的代码

```python
def h_eff_monopole(h):
    """Effective height of a monopole above a ground plane [m]."""
    return h

def e_max_from_power(p_avg, r):
    """Peak E at distance r from an AVERAGE radiated power p_avg [W]."""
    return np.sqrt(180.0 * p_avg) / r

def field_from_current(i_peak, h=H_TX, r=6.0):
    """Returns (E_peak, P_avg). Power must be time-averaged."""
    p_avg = i_peak ** 2 * radiation_resistance(h) / 2.0
    return e_max_from_power(p_avg, r), p_avg

def link(i_ant_peak, h_tx=H_TX, h_rx=1.00, r=6.0):
    e, p_rad = field_from_current(i_ant_peak, h_tx, r)
    v_oc = e * h_eff_monopole(h_rx)      # was: e * (h_rx / 2)
    ...
```

### 3.4 修正后的输出与审计对齐

`py -3 scripts/link_budget.py` 现在给出：

```
 I_ant/mA   P_rad/uW   E/(mV/m)  V_oc_rx/mV
      5.0     52.795      16.25       16.25
```

交叉核对：审计报告的 D=3 解是 `I_rms = 3.749 mA → I_peak = 5.302 mA → P_avg = 59.36 µW → E_peak = 17.22 mV/m`。本脚本在 5.302 mA 峰值下给出 `P = 59.36 µW`、`E = 17.23 mV/m`——**与审计一致到三位有效数字**（差异来自 `LAM` 取值的末位）。

### 3.5 为什么 `link_budget_audit.py` 不能"一起修"

`link_budget_audit.py` 的职责**就是**复现这两处错误并分别归因：

```
defect A (h/2)          → ×2.000
defect B (rms / √2 again) → ×0.707
net                      → ×1.414
```

它是**审计工具**，不是生产代码。把它"修好"就毁掉了归因证据。本次已在 `link_budget.py` 的模块 docstring 里显式写明这一点：

> Do not "fix" that file -- it is the audit.

---

## 4. 本轮改动的完整清单

| 文件 | 改动 | 类型 |
|---|---|---|
| `simulation/v4_hardware/stage_am_alt3_20261115/scripts/link_budget.py` | 修正 `h_eff`（docstring + `link()`）；修正峰值/平均功率；新增 `h_eff_monopole()` 与详细弃用说明 | 脚本 |
| `simulation/v4_hardware/stage_am_alt3_20261115/scripts/final_verify.py` | 网表模板加 `V3ALIAS v3 ef_e 0` 及注释 | 脚本 |
| `README.md` | 第 53 段补覆盖率双口径与 v3/link_budget 缺陷 | 索引 |
| `项目管理/03_当前实现状态.md` | 新增 19:00 条目，含四项缺陷登记 | 索引 |

**未改动**：所有 `.raw`、所有 `.json` 结果、所有 `.md` 历史报告、所有 `.cir` 网表、所有哈希清单。

### 4.1 两个脚本改动的授权记录

两个脚本的修改**已获用户明确批准保留，不予回退**（2026-11-16，本次会话）：

> 用户原话：「两个脚本不回退」

记录这一点是因为它们与历史报告处于**不同的证据等级**，容易被后来的读者误判：

| | 历史报告 / 网表 / 结果 JSON | `link_budget.py`、`final_verify.py` |
|---|---|---|
| 是否被 `SHA256SUMS.txt` 或 `predecessor_sha256.json` 哈希 | **是** | **否**（逐一核对过全部哈希清单，均无命中） |
| 性质 | **证据**：记录"当时算出了什么" | **工具**：记录"怎么算" |
| 改动后果 | 销毁完整性证据 | 影响下次运行，不影响任何既有数据 |
| 本阶段处置 | 只能用勘误追加，不得改写 | 就地修正，并保留旧式写法作为注释与文档 |

**保留而不回退的理由**：`link_budget.py` 的两个缺陷（`h_eff=h/2` 与峰值功率当平均功率）方向相反、数值上接近抵消，回退会让脚本继续产出偏差 √2 的场强数字，而输出看起来"差不多对"——这是最危险的失效模式（详见 §3.2）。`final_verify.py` 的 `V3ALIAS` 是**纯增量**：零伏源不改变任何电气量，老网表照跑，新网表多一个可读的节点名。

**同时保留的可追溯性**：
- `link_budget.py` 的模块 docstring 保留了缺陷 A/B 的完整说明（含 ×2.000 / ×0.707 / 净 ×1.414），并显式写下"不要'修好' `link_budget_audit.py`——那是审计"。
- `link()` 里保留了 `# was: e * (h_rx / 2)` 作为行的历史痕迹。
- `link_budget_audit.py` **一字未动**，仍能独立复现两处错误并归因。
- 历史 raw 的 6 变量状态未变，其"`v3` 即 `v(ef_e)`"的正确读法已登记在 §2.2。

---

## 5. 未做的事（边界）

| 事项 | 原因 |
|---|---|
| 重跑 `final_verify.py` 生成带 v(v3) 的新 raw | 属新仿真，且当前结论不依赖它（所有指标用 `v(ef_e)` 已够） |
| 统一 `link_budget.py` 与 `link_budget_audit.py` 的口径 | 前者是生产、后者是审计，刻意保持不同 |
| 修正 `03_报告:71` 的 117.92%～166.66% | 受 `stage_completion.json` 引用且该报告是历史文档；改为在索引层标注 |
| 重算端口电压需求表（103～232 mV → 55.58 mV @ D=3） | 该表按 5.30 mA 缩放，属"按区间重列"，需与 AM-ALT.4 一起做更合适 |
| 修改 `fin_nom.cir` 加 V3ALIAS | 它是历史网表，改动会破坏与 `fin_nom.raw` 的对应关系 |

---

## 6. 复现与核验

```powershell
cd D:\实验报告文件夹\电路2
py -3 simulation\v4_hardware\stage_am_023_review_20261116\verify_p1b.py
cd simulation\v4_hardware\stage_am_alt3_20261115\scripts
py -3 link_budget.py
```

`verify_p1b.py` 核验：覆盖率四种口径的算式、`link_budget.py` 的修正（含用审计 JSON 交叉验证）、`V3ALIAS` 的存在与语法、以及历史 raw 的 6 变量状态未被改动。

---

## 7. 相关文件

- 上级裁定：[AM-02.3 回溯修订](AM-02.3_回溯修订_50Ω口径与AM-ALT.3目标复核.md)
- 课程口径待确认：[P0 确认单](../../../项目管理/P0_课程v3验收口径确认单.md)
- AM-02.3 勘误：[P1a](P1a_AM-02.3历史结论修订与伪2kΩ标注.md)
- 原勘误报告（未改）：`02_AM-ALT.3_勘误与天线阻抗测量方案.md`
- 覆盖率依据：`results/closure_sense10_metrics.json`、`round2_20261116/results/d05_metrics.json`
- 场强审计依据：`results/link_budget_audit.json`
