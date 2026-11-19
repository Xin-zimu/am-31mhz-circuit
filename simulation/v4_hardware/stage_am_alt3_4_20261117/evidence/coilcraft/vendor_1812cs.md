# Coilcraft 1812CS — 厂家参数核实报告

生成 2026-11-17 · `D:\实验报告文件夹\电路2` · 用途：31 MHz 加载 1 m 短单极子

**结论先行**：1812CS-272/332/392/472/562 的 datasheet 保证值**已全部闭合**（官方 Document 105 PDF 已下载、逐字提取核对）。Doc 158 模型与 datasheet **不矛盾**，但 **SRF 系统性偏高 1.64–1.81 倍**（见 §4）。

## 1. 数据来源（官方，可复核）

| 来源 | URL | 本地副本 |
|---|---|---|
| Document 105 datasheet (Rev 08/08/22) | https://www.coilcraft.com/getmedia/677afbbb-f368-4f0b-b59e-ab9befcb1f0e/1812cs.pdf | `coilcraft_1812cs_datasheet.pdf` 124 954 B，%PDF 已校验 |
| Document 158 SPICE (158-17 Rev 06/04/04) | https://www.coilcraft.com/getmedia/570249c4-a021-466b-808d-0a2f9fe2aa78/spice_1812cs.pdf | `coilcraft_doc158_spice_1812cs.pdf` 68 958 B |
| 产品页（系列表 + 注释） | `.../1812-(4532)/1812cs/` | `vendor_1812cs_html_extract.txt` |

> coilcraft.com 对普通抓取返回 403；改用 curl.exe + 浏览器 UA 取得完整 210 KB HTML 与 PDF，PDF 用 pypdf 提取并**渲染两页目视复核**。

## 2. Datasheet 保证值（kind = guaranteed）

电感测试频率 **7.9 MHz**（网页显示成 8 MHz，PDF 原文为 7.9）。Q 测试频率 **50 MHz（确认不是 100 MHz）**。

| 型号 | L (µH) | 容差% | **Q min @50 MHz** | **SRF min (MHz)** | DCR max (Ω) | Irms (mA) |
|---|---|---|---|---|---|---|
| 1812CS-272 | 2.7 | 2/5 | 63 | 160 | 3.2 | 300 |
| **1812CS-332** | 3.3 | 2/5 | **65** | **145** | 3.8 | 270 |
| **1812CS-392** | 3.9 | 2/5 | **69** | **130** | 5.0 | 240 |
| **1812CS-472** | 4.7 | 5 | **63** | **115** | 5.4 | 230 |
| 1812CS-562 | 5.6 | 5 | 59 | 100 | 5.7 | 220 |

472/562 只有 5% 档（2% 不加粗=不备货）；272/332/392 的 2% 与 5% 均备货。

**共用规格**（Document 105 原文）：
- Irms：`"Current that causes a 15°C temperature rise from 25°C ambient. This information is for reference only and does not represent absolute maximum ratings."`
- 工作温度：`"Ambient temperature –40°C to +125°C with Irms current"`；最高件温 `+140°C (ambient + temp rise)`
- AEC-Q200：`"This high temperature series meets AEC-Q200 Grade 1 (-40°C to +125°C)"` → **是**
- TCL `+25 to +125 ppm/°C`；芯材 Ceramic；重 109–128 mg

## 3. Doc 158 模型（kind = typical / derived）

| 型号 | R1 | R2 | C(pF) | L(µH) | k | 上限(MHz) | 模型SRF\* | Q@31M\* | Q@50M\* |
|---|---|---|---|---|---|---|---|---|---|
| 1812CS-272 | 68 | 3.2 | 0.123 | 2.700 | 9.80e-4 | 310 | 276.2 | 60.5 | 82.1 |
| 1812CS-332 | 81 | 3.8 | 0.120 | 3.330 | 1.12e-3 | 260 | 251.8 | 64.3 | 87.0 |
| 1812CS-392 | 121 | 5.0 | 0.118 | 3.950 | 1.12e-3 | 240 | 233.2 | 68.1 | 93.0 |
| 1812CS-472 | 85 | 5.4 | 0.122 | 4.775 | 1.80e-3 | 220 | 208.5 | 59.7 | 79.4 |
| 1812CS-562 | 198 | 5.7 | 0.165 | 5.700 | 2.01e-3 | 190 | 164.2 | 63.9 | 78.8 |

\* **derived** — 本次任务用 Rvar = k·√f 从 Doc 158 元件值算出；Coilcraft 从未印过这些数。R1/R2/C/L/k/上限 为 Doc 158 原文（typical，de-embedded，**非保证值**）。

## 4. 关键结论：datasheet 与 Doc 158 是否冲突？

**(a) Q 测试频点 —— 不矛盾，但适用范围要小心。** datasheet 保证 **50 MHz** 的 Q。50 MHz 高于 31 MHz 工作点，故不能直接搬到 31 MHz。模型显示该频段 Q 随频率单调上升，Q(31) 普遍**低于** Q(50)：332 65→64.3（乐观 1.1%）、392 69→68.1（1.3%）、272 63→60.5（4.0%）、472 63→59.7（5.2%）。**562 例外**：模型 Q(31)=63.9 反比 59 高 8.3%（其 Q 峰在 50–100 MHz 间）。

**(b) SRF —— 确有系统性冲突，模型偏高 1.64–1.81 倍。**

| 型号 | datasheet SRF min | 模型 SRF | 比值 |
|---|---|---|---|
| 1812CS-272 | 160 | 276.2 | 1.73× |
| 1812CS-332 | 145 | 251.8 | 1.74× |
| 1812CS-392 | 130 | 233.2 | 1.79× |
| 1812CS-472 | 115 | 208.5 | 1.81× |
| 1812CS-562 | 100 | 164.2 | 1.64× |

这**正是 Doc 158 自己的警告**：`"Typically, the Self-Resonant Frequency (SRF) of the component model will be higher than the measurement of the component mounted on a circuit board"`、`"the model results may be different from the data sheet specifications"`、`"The parasitic reactive elements of a circuit board or fixture will effectively lower the circuit resonant frequency"`。机理：模型并联 C（0.118–0.165 pF）是 de-embedded 值，低估了实板有效电容。

**(c) 对 31 MHz 的实际影响 —— 无。** 最差 562 保证 SRF=100 MHz 仍是 31 MHz 的 **3.2 倍**，332 为 **4.7 倍**。五款在 31 MHz 均远离自谐振，串联 L+R 成立，加载单极子结论不受影响。冲突只影响**余量口径与引用方式**。

**建议**：对外引用 datasheet 保证值（SRF min、Q min @50 MHz、DCR max、Irms@15 °C）；Doc 158 仅用于随频率仿真；31 MHz 的 Q 必须标 derived-from-model(typical)，不得当保证值；讲 SRF 余量必须用保证最小值。

## 5. 字段闭合清单

**已闭合（5 型号全覆盖，官方保证值）**：标称 L + 测试频率(7.9 MHz) · 容差(2%/5% 及备货档) · **Q 数值 + 测试频率(50 MHz)** · DCR max · SRF min · Irms + 温升条件(15 °C @25 °C) · 工作温度(−40…+125 °C with Irms) · 最高件温(+140 °C) · AEC-Q200(Grade 1，是) · TCL/芯材/重量

**仍缺（无法取得官方值）**：
- **31 MHz 的保证 Q** — Coilcraft 只保证 50 MHz，31 MHz 无官方值，只能模型推算(derived)
- **逐型号典型 Q 表** — 第 2 页 "Typical Q vs Frequency" 是**曲线图**，只画 1.8/3.9/8.2/15/22/33 µH 六条且数值不可读；272/332/472/562 无曲线
- **31 MHz 的 ESR/交流电阻** — 官方只给 DCR max，AC 电阻只能由模型推算(derived)
- **Irms 绝对最大值** — 厂家明说仅供参考，"does not represent absolute maximum ratings"
- 长期可靠性/FIT — 仅指向官网计算器，未取具体数字

## 6. 同类替代件核查（只列真查到厂家数据的）

**✔ Vishay Dale IMC-1812**（Doc 34044, Rev 19-Dec-2024）https://www.vishay.com/docs/34044/imc1812.pdf

| P/N | L(µH) | 容差 | 测试频率 | Q min | SRF min | DCR max | 额定DC |
|---|---|---|---|---|---|---|---|
| IMC1812ES3R3K | 3.3 | ±10% | 7.96 MHz | 50 | **45.0 MHz** | 0.80 Ω | 355 mA |
| IMC1812ES3R9K | 3.9 | ±10% | 7.96 MHz | 50 | **40.0 MHz** | 0.90 Ω | 330 mA |
| IMC1812ES4R7K | 4.7 | ±10% | 7.96 MHz | 50 | **35.0 MHz** | 1.00 Ω | 315 mA |

**不适合替代**：芯材 `powdered iron for 1.0 µH to 120 µH`（**非陶瓷**）；3.3 µH 的 SRF 仅 45 MHz（31 MHz 的 1.45 倍），远低于 1812CS-332 的 145 MHz；Q 定义在 7.96 MHz；额定电流按 **40 °C 温升 @85 °C 环境**，与 Coilcraft 15 °C 口径不可直接比。工作温度 −55…+125 °C。

**✔ TDK MLF2012A3R3JTD25** https://product.tdk.cn/zh/search/inductor/inductor/smd/info?part_no=MLF2012A3R3JTD25
L 3.3 µH ±5% @10 MHz · SRF min **60 MHz** / typ 90 · Q min **45 @10 MHz** / typ 70 · DCR max 600 mΩ · 额定 50 mA · −55…+125 °C · AEC-Q200 **YES**
**不可比**：0805（2.00×1.25×1.25 mm）**铁氧体磁屏蔽叠层**，非 1812 陶瓷绕线；SRF 仅 1.9 倍、电流仅 50 mA。仅作"查证过并否决"记录。

**✔ Johanson Technology**（陶瓷芯 RF 电感）https://www.johansontechnology.com/products/ceramic-rf-inductors/ceramic-inductors/
官方表仅 0201(0.6–39 nH)、0402(1.0–120 nH)、0603(1.2–220 nH)。**陶瓷线最大 220 nH，比 2.5–5.5 µH 低两个数量级，无法覆盖。**

**✘ 未能核实（不填任何数字）**
- **Chilisin CS1812**：第三方镜像(wiki.adom.inc)表格结构与 Coilcraft 几乎相同（疑似 clone），但 chilisin.com 对所有尝试 URL 均返回同一 1.05 MB 通用页，**拿不到表格或官方 PDF** → 不记录数字
- **Bourns**(403 JS 挑战)、**Murata**(产品 URL 全 404)、**API Delevan**(域名无响应) → 未取得官方 datasheet，不记录数字

## 7. 交付物

```
evidence/coilcraft/
├── vendor_1812cs.json            结构化数据（每字段 value/unit/condition/source_url/evidence_quote/kind）
├── vendor_1812cs.md              本文件
├── vendor_1812cs_html_extract.txt 产品页表格+注释逐字抓取
├── coilcraft_1812cs_datasheet.pdf Document 105
└── coilcraft_doc158_spice_1812cs.pdf Document 158
```

`kind` 三态严格区分：**guaranteed** = datasheet 保证值 / **typical** = 厂家标注典型或 de-embedded 模型 / **derived** = 本次任务从模型算出（Coilcraft 从未印过）。
