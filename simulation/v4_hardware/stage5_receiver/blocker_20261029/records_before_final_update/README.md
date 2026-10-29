# 31 MHz 电路实验项目

模拟调制收发电路的设计、Multisim/ngspice 仿真、晶体振荡器实验和验证记录。

## 从这里开始

- [总计划](项目管理/01_总计划.md)
- [当前实现状态](项目管理/03_当前实现状态.md)
- [性能指标](性能指标要求_N31_M50.md)
- [S05 最新：选频、阻塞与 OPA197 基带验证](simulation/v4_hardware/stage5_receiver/S05_03_选频阻塞与基带验证.md)
- [S05 R2 接收候选与补购清单](simulation/v4_hardware/stage5_receiver/S05_04_R2接收候选与补购清单.md)
- [S05 首批独立仿真（R1 历史基准）](simulation/v4_hardware/stage5_receiver/S05_01_首批独立仿真报告.md)
- [最新独立振荡器与缓冲结果](simulation/v4_hardware/stage4_rf_oscillator/S04_12_2N3904实物版探索与缓冲推进.md)
- [当前板与整机备料清单](simulation/v4_hardware/stage4_rf_oscillator/advance_20261029/补购清单_当前板与整机备料.md)
- [万能板接线说明](simulation/v4_hardware/stage4_rf_oscillator/perfboard_20261017/README_元件与接线.md)

## 当前验证边界

截至 2026-10-29，S05 已形成 R2 独立候选：选频峰移到约 30.83 MHz、31 MHz 增益 68.44 倍；接入 BAT85/F1 与 TI OPA197 后，标称 10 mV/50 Ω、m=0.5 的预偏置方波输出约 4.78 Vpp。1.6 MHz 阻塞显著改善，但 29/33 MHz 邻近干扰、固定增益大输入过载、启动、BAT85S 型号与无线实测仍未闭合，**整机灵敏度和 6 m 距离不成立**。首批 R1 证据和冻结工程保留。S04 的独立 2N3904 振荡器标称假设模型通过末窗稳定性筛查，独立缓冲已开展带载探索；放大与隔离连接、晶体型号参数和整机电池端功耗尚未闭合。仿真结果不等于实物验收，详见各报告的条件和限制。

## 文件与复现

`simulation/` 保存工程、网表、脚本和测量摘要，`项目管理/` 保存计划与验证状态，`output/` 保存实验图册等交付物。

保留原有 Git 历史。按 `.gitignore`，大型原始波形（例如 `.raw`、`.gra`、`.npz`）、软件安装包及缓存不上传；部分证据仅保存在本机，摘要中留有路径或哈希。因此克隆本仓库不等于获得所有原始数据。运行脚本前需要安装相应软件并核对脚本中的本地路径；仓库不是开箱即用的软件包。
