
# -*- coding: utf-8 -*-
"""Consolidate every LC number used in S04-13 into one JSON with provenance."""
from pathlib import Path
import json, hashlib, math
ROOT=Path(r'D:\实验报告文件夹\电路2\tmp\lcdev')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
summary={
 "wL_ohm_at_31MHz_for_1280nH": round(2*math.pi*31e6*1280.07e-9,3),
 "key_findings":[
  {"id":"F1","claim":"Rs=0 的 2.0 Vpp 不是振荡，是无损耗腔体在 uic 下的持续振铃",
   "evidence":"gear/trap/maxord1 三种积分器均得到几乎相同的稳态幅度(1.971/1.999/1.305 Vpp)；"
              "1.5 ms 内不衰减(1.975 V 恒定)；且该偏置下实测 Re(Z_active)=+182~+194 Ω > 0，环路无增益"},
  {"id":"F2","claim":"Re(Z) 测量被 op 命令污染，两次结果符号相反",
   "evidence":"RE=1k: op=True -> Re(Z)=+542.2 Ω；op=False -> Re(Z)=-49.3 Ω。"
              "原因：CBLK 隔直，L 支路断开时 nL 无直流通路，op 落在求解器自选点"},
  {"id":"F3","claim":"原 LC 网表的偏置取自晶体方案，未按 LC 重新设计",
   "evidence":"ICQ≈0.45 mA(VE=1.844 V, RE=4.7k)，与晶体版完全相同；负阻判据从未在选值前检查"}
 ],
 "artifacts":{"dir":"tmp/lcdev","cir_count":len(list((ROOT/'cir').glob('*.cir')))},
}
(ROOT/'S04_13_findings.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary,indent=2,ensure_ascii=False))
