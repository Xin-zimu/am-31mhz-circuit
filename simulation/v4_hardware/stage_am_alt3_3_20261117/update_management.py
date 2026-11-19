"""Add the new route without rewriting historical records; retain before snapshots."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
MARK='AM-ALT.3.3 新路线（2026-11-17）'
files=[PROJECT/'README.md']+list((PROJECT/'项目管理').glob('0[123]_*.md'))
rows=[]
for p in files:
 old=p.read_bytes()
 if MARK in old.decode('utf-8-sig'):continue
 dest=ROOT/'evidence/management_before'/p.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old)
 link=('' if p.parent==PROJECT else '../')+'simulation/v4_hardware/stage_am_alt3_3_20261117/README.md'
 notice=f'''## {MARK}

**当前执行路线：普通成品伸缩拉杆＋外购高频可调匹配元件。** 不再制作铜杆或绕加载线圈；保留现有调制、晶体载波、两级2N3904驱动和必要地网。新交付与采购前门槛见[AM-ALT.3.3独立审查及初始验证]({link})。

结论为**条件性可行**：已有70/80/90/100cm独立NEC模型与含实际损耗的匹配候选；名义载波约3.81–3.94mA、9V整机预算约303.76mW。具体商品SKU、Q31/SRF、接触/安装阻抗及链路余量仍待核，未采购、未实测6m/V2/电池功耗，不将AM-ALT.3或整机标为验收完成。50Ω与2.0/1.2Vpp不作为课程指标；旧3.75–5.30mA需求不套用新天线。

以下保留历史记录。与本条冲突的“自制线圈制作”“仅CB苗子可选”“唯一执行入口”等表述按原日期和旧模型理解；当前路线以上述AM-ALT.3.3为准。

---

'''
 p.write_bytes(notice.encode('utf-8')+old)
 rows.append(dict(path=str(p.relative_to(PROJECT)),before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(ROOT/'management_update.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('Updated',len(rows),'management entry points')
