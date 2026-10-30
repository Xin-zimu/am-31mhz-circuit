"""Recompute S05-07 presentation from retained evidence; never launch a simulator."""
from run_lc import *
import hashlib, platform, re, csv, io
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    n=LoadedNetwork(); root=STAGE.parents[2]
    rows=json.loads((HERE/'sweep_results.json').read_text(encoding='utf-8'))
    corners=json.loads((HERE/'corner_results.json').read_text(encoding='utf-8'))
    std=json.loads((HERE/'standard_values.json').read_text(encoding='utf-8'))
    ext=json.loads((HERE/'extension_results.json').read_text(encoding='utf-8'))
    srcs=[
      ('coilcraft_1008cs_model.pdf','https://www.coilcraft.com/getmedia/8b8dc5bb-0e94-4194-b919-ac2586274005/spice_1008cs.pdf','2026-04-30','Official typical frequency-dependent model; pages visually checked'),
      ('coilcraft_132.pdf','https://www.coilcraft.com/getmedia/22e0981d-b6cb-4c11-a3ec-5cac433ee01c/132.pdf','2013-10-29','132-17L is 460nH; old meter reference column 475nH must not replace it'),
      ('vishay_irf24.pdf','https://www.vishay.com/docs/34056/irf24.pdf','2014-03-04','Reference only; not selected primary sample'),
      ('vishay_bfc280905.pdf','https://www.vishay.com/docs/28529/bfc280905.pdf','2024-09-06','2-18pF 05003/05217 ordering and electrical table visually checked')]
    dump(HERE/'source_references.json',[dict(file='sources/'+name,url=url,revision=rev,retrieved='2026-10-30',sha256=sha(HERE/'sources'/name),note=note) for name,url,rev,note in srcs])
    doc=root/'电子线路实验评分标准-学生.docx'
    xml=ET.fromstring(ZipFile(doc).read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paras=[''.join(p.itertext()) for p in xml.findall('.//w:p',ns)]
    selected=[t for t in paras if any(k in t for k in ['峰峰值','通信距离','指定距离6m','通用或自制PCB'])]
    dump(HERE/'requirements_review.json',dict(source=str(doc.relative_to(root)),sha256=sha(doc),
         exact_text=selected,rf_20mv_literal_matches=[t for t in paras if re.search(r'20\s*m[Vv]|20\s*毫伏',t)],
         conclusion='No explicit 20mV receiver RF input requirement found. Course baseband/range requirements remain; this does not waive receiver dynamic-range work after actual link levels are known.'))
    # Archived S05-06 CSV called linear gain "g31_dB". Publish a separate corrected copy.
    corrected=[]
    with (PREV/'network_sensitivity.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            source=json.loads((PREV/'results'/(row['case']+'.json')).read_text())
            value=source['metrics']['g31'];row.pop('g31_dB')
            row['gain31_v_v']=f'{value:.10g}';row['gain31_db']=f'{20*np.log10(value):.10g}'
            corrected.append(row)
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=list(corrected[0]))
    writer.writeheader();writer.writerows(corrected)
    fixed(HERE/'s0506_network_units_corrected.csv',buf.getvalue().encode('utf-8'))
    # Text-only local report tables: values are calculated, units are explicit.
    entries=[('原A，历史raw',json.loads((HERE/'baseline_reuse.json').read_text())['metrics'])]
    ids=['Lminusplus_untuned','Lminusplus_CT','Lplusminus_untuned','Lplusminus_CT','CS471_CT','P460_Q50_CT','P460_Q65_CT','P460_match_rounded','P460_probe10p']
    entries += [(r['name'],r['spice']) for r in rows if r['name'] in ids]
    entries += [('P460_C15_C11_CT',std['metrics'])]
    s='| 用例 | 31 MHz 增益 V/V（dB） | 3dB 边界中心/MHz | 总带宽/MHz | 29/33 相对响应/dB | 50Ω回波损耗/dB |\n|---|---:|---:|---:|---:|---:|\n'
    for name,m in entries:
        s+=f"| {name} | {m['gain31_v_v']:.3f}（{m['gain31_db']:.3f}） | {m['center_edges_mhz']:.4f} | {m['bw_mhz']:.4f} | {m['relative29_db']:.3f} / {m['relative33_db']:.3f} | {m['return_loss50_db']:.3f} |\n"
    fixed(HERE/'comparison_table.md',s.encode('utf-8'))
    # Derive plots from raw for simulated curves; only corners/model are explicitly analytic.
    plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':10})
    fig,axs=plt.subplots(2,2,figsize=(12,8.5),constrained_layout=True)
    items=[('历史 A',PREV/'results/C_Q50.json'),('标准值调谐候选',HERE/'results/P460_C15_C11_CT.json'),
           ('匹配探索',HERE/'results/P460_match_rounded.json')]
    for label,path in items:
        r=json.loads(path.read_text());raw=d.readraw(Path(r['raw_path']));f=raw['frequency'].real
        g=abs(raw['v(rf)']);v=raw['v(input)'];z=50*v/(1-v)
        axs[0,0].plot(f/1e6,20*np.log10(g/np.interp(31e6,f,g)),label=label)
        axs[0,1].plot(f/1e6,-20*np.log10(abs((z-50)/(z+50))),label=label)
    axs[0,0].set(ylabel='相对 31 MHz 响应 / dB',ylim=(-25,2),title='加载选频响应（SPICE raw）')
    axs[0,1].set(ylabel='50 Ω 回波损耗 / dB',ylim=(0,30),title='匹配改善会改变响应，未接天线')
    curves=[]
    for r in corners:
        h,_=n.response(r['parameters']);curves.append(20*np.log10(abs(h)))
    curves=np.array(curves)
    axs[1,0].fill_between(n.f/1e6,curves.min(axis=0),curves.max(axis=0),alpha=.25,color='#145da0',label='48 组分别调谐的计算范围')
    h,_=n.response(std['parameters']);axs[1,0].plot(n.f/1e6,20*np.log10(abs(h)),label='标准值 Q50')
    axs[1,0].set(ylabel='源端到 RF 电压增益 / dB',ylim=(10,36),title='角点为节点方程计算，3 个极端点经 SPICE 核对')
    for label,name in [('无探头附加电容','P460_Q50_CT'),('tank2 额外 10 pF','P460_probe10p')]:
        r=json.loads((HERE/'results'/(name+'.json')).read_text());raw=d.readraw(Path(r['raw_path']));f=raw['frequency'].real
        axs[1,1].plot(f/1e6,20*np.log10(abs(raw['v(rf)'])),label=label)
    axs[1,1].set(ylabel='源端到 RF 电压增益 / dB',ylim=(8,36),title='探头电容扰动（SPICE raw）')
    for ax in axs.flat:
        ax.set_xlim(28,34);ax.set_xlabel('频率 / MHz');ax.grid(alpha=.2);ax.legend(fontsize=8)
        for f0 in [29,31,33]:ax.axvline(f0,color='grey',lw=.7,ls=':')
    fig.suptitle('S05-07：LC 调谐与实物敏感性\n小信号 AC，不是阻塞、方波或实物验收',fontsize=14)
    (HERE/'plots').mkdir(exist_ok=True);fig.savefig(HERE/'plots/lc_summary.png',dpi=170);plt.close(fig)
    # Audit preserves every pre-existing S05 byte and validates immutable solver results.
    snap=json.loads((HERE/'baseline_snapshot.json').read_text(encoding='utf-8'))
    errors=[]
    for rel,h in snap['historical_files'].items():
        if not (root/rel).exists() or sha(root/rel)!=h:errors.append('historical changed: '+rel)
    results=[]
    for p in sorted((HERE/'results').glob('*.json')):
        r=json.loads(p.read_text())
        if 'raw_sha256' not in r:continue
        for path,key in [(Path(r['raw_path']),'raw_sha256'),(HERE/'netlists'/(r['name']+'.cir'),'net_sha256'),(HERE/'results'/(r['name']+'.log'),'log_sha256')]:
            if sha(path)!=r[key]:errors.append('hash: '+str(path))
        raw=d.readraw(Path(r['raw_path']));f=raw['frequency'].real
        if not all(np.all(np.isfinite(v)) for v in raw.values()):errors.append('nonfinite: '+r['name'])
        if len(f)>1 and (len(f)!=2401 or abs(f[0]-20e6)>1 or abs(f[-1]-44e6)>1):errors.append('AC coverage: '+r['name'])
        # Active stage and model block are byte-identical to historical fixture (normalized newlines).
        old=(PREV/'netlists/C_Q50.cir').read_text().split('VSUP vcc')[1].split('.options')[0]
        cur=(HERE/'netlists'/(r['name']+'.cir')).read_text().split('VSUP vcc')[1].split('.options')[0]
        if old.strip()!=cur.strip():errors.append('active/model block changed: '+r['name'])
        results.append(r)
    metadata=dict(git_base=snap['git_head'],python=platform.python_version(),numpy=np.__version__,
                  ngspice_sha256=sha(d.EXE),new_ac_results=len(results),
                  historical_files_checked=len(snap['historical_files']),historical_errors=errors,
                  new_transient_runs=0,retained_old_failures_not_retried=['F22_sq10_Ac20','F22_sq50_Q40'],
                  user_hardware='No components purchased; oscilloscope available; other equipment unconfirmed',
                  measured_hardware=False,bat85s_qualified=False,passed=not errors,
                  scripts={p.name:sha(p) for p in HERE.glob('*.py')})
    # Audit is derived output; regenerating it is safe, historical evidence stays immutable.
    (HERE/'audit.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=True))
    assert not errors,errors


if __name__=='__main__':main()
