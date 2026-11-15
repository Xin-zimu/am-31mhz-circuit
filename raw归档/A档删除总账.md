# A 档删除总账（零记录删除）

生成：2026-11-15 20:43。范围：无归档价值的临时/留档/重复 raw。
原则：A 档不保留指标与波形图；仅登记路径、大小、SHA256 与删除日期，供追溯。
复现说明：全部条目均有对应网表或属异常临时产物，见备注列。

| 路径 | 大小(MB) | SHA256 | 修改时间 | 状态 | 备注 |
|---|---|---|---|---|---|
| D:\实验报告文件夹\电路2\tmp\c3\lt\lt3_trap_kick.raw | 13526.6 | 50B8510FD5DEB578E9587A6F9C3784A122C120115FDFE19040C555505E2DB6CB | 2026-10-30 02:16:59 | 已删除·2026-11-15 | LTspice 异常长窗产物（tmp 目录）；同名 .cir 在 tmp\c3\lt\ 保留，可重跑，勿再跑全窗 |
| D:\实验报告文件夹\电路2\debug\xsp_kit_ascii\out_am200u.raw | 34.2 | 817672EF712C76BD350C1CA87A803386FEE215910FB26C82D05F8A8B4EC7B8D8 | 2026-09-18 00:24:23 | 已删除·2026-11-15 | debug\文件索引.md 注明"xsp_kit_ascii 仅作留档"；与 D:\ms_xsp\out_am200u.raw SHA256 相同（副本）；驱动脚本 cmd_am200u.txt 保留 |
| D:\实验报告文件夹\电路2\debug\xsp_kit_ascii\out_iplot200u.raw | 24.4 | 8E7A814BE0A31F06194ABEAA3F4FF8F32500C9F53B93D1A466EC874407EB6F81 | 2026-09-18 00:39:40 | 已删除·2026-11-15 | 同上，与 D:\ms_xsp\out_iplot200u.raw 相同；cmd_iplot200u.txt 保留 |
| D:\ms_xsp\out_am200u.raw | 34.2 | 817672EF712C76BD350C1CA87A803386FEE215910FB26C82D05F8A8B4EC7B8D8 | 2026-09-18 00:24:23 | 已删除·2026-11-15 | 2026-09-18 手工验证件；net_am.cir＋cmd_am200u.txt 保留可重跑；debug\xsp_kit_ascii 副本同步删除 |
| D:\ms_xsp\out_am30u.raw | 18.5 | 7968709BCA2F27508428BBDC85892B3A0887BB6E095DF2FF5D11BDC4D39213FA | 2026-09-18 00:23:44 | 已删除·2026-11-15 | 2026-09-18 手工验证件；net_am.cir＋cmd_am30u.txt 保留 |
| D:\ms_xsp\out_iplot200u.raw | 24.4 | 8E7A814BE0A31F06194ABEAA3F4FF8F32500C9F53B93D1A466EC874407EB6F81 | 2026-09-18 00:39:40 | 已删除·2026-11-15 | 2026-09-18 手工验证件；net_am.cir＋cmd_iplot200u.txt 保留 |
| D:\ms_xsp\out_tmax20n.raw | 1.6 | 1FB2A5A865A8A7C3EA599CD78EE22279A9C5F7C89A3112C802956CA147A1EB4C | 2026-09-18 00:45:24 | 已删除·2026-11-15 | TMAX 对照实验产物；net_am.cir＋cmd_tmax20n.txt 保留 |

合计：7 个文件，约 13,663.9 MB（13.35 GB）。

> 注：SHA256 为删除前实测登记；本账只覆盖 raw 文件本身，配套 .cir/.cmd/.log 均未删除。
