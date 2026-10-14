from pathlib import Path
import hashlib, json, shutil

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
SCRATCH = Path('D:/ms_xsp/stage3_acceptance')
SCRATCH.mkdir(exist_ok=True)
sources = [HARDWARE/'AM_20k_31MHz_V4_3_REPAIRED.ms14',
           HARDWARE/'repair_20261011/final_actual.cir',
           HARDWARE/'AM_20k_31MHz_V4_3_REPAIRED.gra',
           HARDWARE.parents[1]/'设计.docx',
           HARDWARE.parents[1]/'电子线路实验评分标准-学生.docx',
           HARDWARE.parents[1]/'性能指标要求_N31_M50.md']
manifest = {'date':'2026-10-12', 'sources':[],
            'scope':'Full exported circuit; Multisim XSPICE command interface. Not a new GUI run.',
            'requirement_source_status':'User supplied N31/M50 specification and scoring DOCX; original scoring text cross-checked',
            'baseline_copy_settings':'Unmodified copy: 200 us GUI analysis; longer analysis is in .cmd only.'}
for src in sources:
    data=src.read_bytes()
    manifest['sources'].append({'path':str(src),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
baseline=HERE/'S03_BASELINE_V4_3.ms14'
if not baseline.exists(): shutil.copy2(sources[0],baseline)
assert baseline.read_bytes()==sources[0].read_bytes()
net=sources[1].read_bytes()
# Preserve the complete GUI-exported circuit; add only a SPICE end directive.
cir=net.rstrip()+b'\n.end\n'
(HERE/'nominal_full.cir').write_bytes(cir)
(SCRATCH/'nominal_full.cir').write_bytes(cir)
for stop in [1, 5]:
    label=f'nominal_{stop}ms'
    cmd=f'''source D:/ms_xsp/stage3_acceptance/nominal_full.cir
begin-scope page Transient Analysis
save $v1 $bb_in $bbo $v2
iplot $v1 $bb_in $bbo $v2
set trtol = 1
set reltol = 0.0001
set itl4 = 100
set convlimit
set rshunt = 1e+012
set dynamicdc
set inertialdelay
tran 2n {stop}m 0 2n uic
write-and-destroy-iplot "D:/ms_xsp/stage3_acceptance/{label}.raw"
end-scope
'''
    (SCRATCH/f'{label}.cmd').write_text(cmd,encoding='ascii')
    (HERE/f'{label}.cmd').write_text(cmd,encoding='ascii')
(HERE/'baseline_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
