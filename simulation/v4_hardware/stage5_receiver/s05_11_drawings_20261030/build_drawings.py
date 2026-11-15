"""Deterministic S05 drawings. No circuit solver is invoked.

Native KiCad symbols/wires and SVG are generated from the same drawing scene;
verify_drawings.py independently checks the KiCad-exported connectivity.
"""
from pathlib import Path
import csv, json, hashlib, uuid, math, html, shutil, sys, re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
HERE=Path(__file__).resolve().parent
STAGE=HERE.parent
ROOT=STAGE.parents[2]
OUT=ROOT/'output/pdf/S05_A_G22_施工图_20261030'
for sub in ['svg','pdf','kicad','tables','sources','qa']:
    (OUT/sub).mkdir(parents=True,exist_ok=True)
SCALE=.254
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'S05-11/'+s))
def q(s):return json.dumps(str(s),ensure_ascii=False)
def nref(s):return s if re.search(r'\d$',s) else s+'1'
def mm(v):return f'{v*SCALE:.6f}'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def table(name,rows):
    with (OUT/'tables'/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

SOURCE=STAGE/'lc_parts_20261030/netlists/T_sq50_six_source.cir'
def parse_source(p):
    out=[];inside=False
    for num,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        a=line.split()
        if not a:continue
        if a[0].lower()=='.subckt':inside=True
        if a[0].lower()=='.ends':inside=False;continue
        if inside or a[0][0] in '*.+':continue
        k=a[0][0].upper()
        if k in 'RCL':out.append(dict(ref=a[0],kind=k,nodes=a[1:3],value=a[3],line=num))
        elif k=='Q':out.append(dict(ref=a[0],kind=k,nodes=a[1:4],value=a[4],line=num))
        elif k=='X':out.append(dict(ref=a[0],kind=k,nodes=a[1:-1],value=a[-1],line=num))
        elif k in 'VB':out.append(dict(ref=a[0],kind=k,nodes=a[1:3],value=' '.join(a[3:]),line=num))
    return out
raw=parse_source(SOURCE);src={r['ref']:r for r in raw}
baseline=OUT/'qa/history_before.json'
if not baseline.exists():
    dump(baseline,{str(p.relative_to(ROOT)):sha(p) for p in STAGE.rglob('*') if p.is_file() and HERE not in p.parents and p.suffix.lower() in ['.md','.cir','.py','.json','.csv','.lib']})
for name in ['T_sq50_six_source.cir','T_sq10_six_source.cir','T_sq50_six.cir','T_sq10_six.cir']:
    shutil.copy2(STAGE/'lc_parts_20261030/netlists'/name,OUT/'sources'/name)
for name in ['coilcraft_132.pdf','vishay_bfc280905.pdf']:
    shutil.copy2(STAGE/'lc_parts_20261030/sources'/name,OUT/'sources'/name)
manifest={}
for case in ['T_sq50_six','T_sq10_six']:
    rec=json.loads((STAGE/f'lc_parts_20261030/results/{case}.json').read_text(encoding='utf-8'))
    p=STAGE/f'lc_parts_20261030/netlists/{case}_source.cir'
    assert sha(p)==rec['dependencies']['source_sha256']
    assert sha(STAGE/f'lc_parts_20261030/netlists/{case}.cir')==rec['net_sha256']
    assert sha(STAGE/f'lc_parts_20261030/results/{case}.log')==rec['log_sha256']
    model_path=Path(re.search(r'\.include\s+"([^"]+)"',p.read_text()).group(1))
    assert sha(model_path)==rec['dependencies']['model_sha256']
    assert sha(STAGE/'lc_parts_20261030/filters/NOM_132.cir')==rec['dependencies']['filter_sha256']
    manifest[case]={'source_sha256':sha(p),'wrapper_sha256':rec['net_sha256'],'log_sha256':rec['log_sha256'],'raw_sha256_recorded':rec['raw_sha256'],'raw_path':rec['raw_path'],'model_sha256':rec['dependencies']['model_sha256'],'model_path':str(model_path),'filter_sha256':rec['dependencies']['filter_sha256']}
assert [(r['ref'],r['nodes'],r['value']) for r in raw if r['kind'] not in 'VB']==[(r['ref'],r['nodes'],r['value']) for r in parse_source(STAGE/'lc_parts_20261030/netlists/T_sq10_six_source.cir') if r['kind'] not in 'VB']
dump(OUT/'qa/source_manifest.json',manifest)

# Pin numbers here are physical numbers, not SPICE argument positions.
parts={}
excluded={'VMOD','BSIG','RSOURCE','VSUP','RCT1','RCT2','RLOSS1','RLOSS2','CSELF1','CSELF2','CTUNE1','CTUNE2','RLOAD','RBBLOAD','CLOAD'}
for r in raw:
    if r['ref'] in excluded:continue
    ref=r['ref'];kind=r['kind'];ns=r['nodes'];value=r['value'];note='原整链网表';pkg='轴向/径向尺寸待实购核实'
    if kind in 'RCL':pins={'1':ns[0],'2':ns[1]}
    if kind=='Q':
        pins={'3':ns[0],'2':ns[1],'1':ns[2]};pkg='onsemi 2N3904 TO-92 条件映射；实购厂牌待核实';kind='Q'
    if ref=='XDET':
        ref='DDET';kind='D';pins={'2':ns[0],'1':ns[1]};pkg='Nexperia BAT85 SOD68/DO-34；采购待确认';note='XDET参数1=A/物理2；参数2=K/物理1；色环接det'
    if ref=='XOPA':
        ref='U1';kind='U';pins={'3':ns[0],'2':ns[1],'7':ns[2],'4':ns[3],'6':ns[4],'1':'NC','5':'NC','8':'NC'};pkg='TI OPA197ID/IDR SOIC-8 + 逐脚直通转接板';note='不得套用SOT-23-5引脚；转接板映射待通断核实'
    if ref=='RCONNECT':
        kind='W';value='wire / model 0.1R';note='0.1Ω是连接等效；用短连线实现，不作为独立电阻采购'
    if ref.startswith('LSEL'):
        pins={'1':'tank'+ref[-1],'2':'0'}
        # The landing span in this drawing (9.16 mm) is wider than the datasheet lead
        # spacing (3.96 mm). That is a known open item, registered in
        # qa/mechanical_open_items.json; the holes are NOT decided here.
        pkg='Coilcraft 132-17L；落点9.16mm与手册3.96mm相差5.20mm，落孔方案待实物确认'
        note='RLOSS/CSELF并入实物线圈；端子编号为图纸自定义；安装方式未定'
    parts[ref]=dict(ref=ref,kind=kind,value=value,pins=pins,source=r['ref'],note=note,package=pkg,group='RX')
for i,fix,tr in [(1,'30p','10.609801788p'),(2,'39p','7.1490753446p')]:
    for ref,kind,val,pins,desc in [(f'CFIX{i}','C',fix,{'1':f'tank{i}','2':'0'},'C0G/NP0 ≥50V ±2%'),(f'CT{i}','T','2-18p',{'1':f'tank{i}','2':'0'},'Vishay BFC280905217；图纸1=S定片/2=R动片；孔距5.08mm；孔径待实物（手册矛盾）')]:
        parts[ref]=dict(ref=ref,kind=kind,value=val,pins=pins,source=f'CTUNE{i}',note=f'固定段+微调；微调模型起点 {tr}；另含1pF布局寄生，实物按加载调谐',package=desc,group='RX')
for ref,val in [('CDQ1','100n'),('CDQ2','100n'),('CDBUF','100n'),('CDU1','100n'),('CPWR','10u')]:
    parts[ref]=dict(ref=ref,kind='P' if ref=='CPWR' else 'C',value=val,pins={'1':'vcc','2':'0'},source='S05-10 实物配套',note='新增电源去耦；不在原整链模型内，未声称仿真覆盖',package='≥16V；CPWR正极接vcc；100n紧靠有源器件',group='DECOUPLING')
parts['CVREF']['kind']='P';parts['CVREF']['note']='10u ≥16V；正极ref，负极GND；ref不是GND'
parts['CCOUP']['note']='100n无极性；连接out与bbin，不能短接'
parts['RFB']['note']='210k 1%；可采购210k单件，未擅自改为其他增益'
for ref,ns in [('JRF',['input','0']),('JPOWER',['vcc','0']),('JOUT',['final','0'])]:
    parts[ref]=dict(ref=ref,kind='J',value={'JRF':'RF IN','JPOWER':'9 V','JOUT':'BASEBAND'}[ref],pins={'1':ns[0],'2':ns[1]},source='接口',note='焊盘/短接线接口，RF口用短同轴与相邻地',package='具体接头待核实，图纸编号1=信号/正，2=地',group='INTERFACE')

class Scene:
    def __init__(self,name,w,h,title,subtitle):
        self.name=name;self.w=w;self.h=h;self.svg=[];self.lines=[];self.comps=[];self.labels=[];self.texts=[];self.ncs=[];self.root=uid(name)
        self.rect(10,10,w-20,h-20,'#fff','#a9b8c0')
        self.text(40,55,title,28,'#123444');self.text(40,86,subtitle,15,'#475d69')
        self.text(40,h-26,'S05-11 | 2026-10-31 | 同名节点电气相连；实心点为连接；跨线无点不连接。',14,'#475d69')
    def text(self,x,y,t,size=16,color='#172f3b',anchor='start',native=True):
        self.svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(t)}</text>')
        if native:self.texts.append((x,y,t,size))
    def rect(self,x,y,w,h,fill='none',stroke='#b6c4cc',dash=''):
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
    def path(self,pts,color='#182e38',width=2.2,dash=''):
        self.svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
    def circle(self,x,y,r=4,fill='#11725c'):
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>')
    def wire(self,net,*pts,label=False):
        color='#b13c38' if net=='vcc' else '#12745e'
        self.path(pts,color)
        for a,b in zip(pts,pts[1:]):
            if a!=b:self.lines.append((net,a,b))
        if label:
            p=max(pts,key=lambda p:p[1]) if net=='0' else min(pts,key=lambda p:(p[1],p[0])) if net=='vcc' else min(pts,key=lambda p:p[0])
            self.label(net,*p)
    def label(self,n,x,y,display=None):
        self.labels.append((n,x,y));self.text(x+4,y-7,display or ('GND / 0' if n=='0' else '+9 V / vcc' if n=='vcc' else n),14,'#12614f',native=False)
    def comp(self,ref,x,y,orient='h',custom=None):
        p=dict(custom or parts[ref]);p.update(x=x,y=y,orient=orient)
        k=p['kind'];geo,pindef=symbol_geometry(k,orient)
        p['geometry']=geo;p['pindef']=pindef
        self.comps.append(p)
        for poly in geo:self.path([(x+a,y+b) for a,b in poly])
        if k in ('R','C','P','T','L','W','D'):
            tx=x+24 if orient=='v' else x;ty=y-7 if orient=='v' else y-75 if k=='W' else y-39;anchor='start' if orient=='v' else 'middle'
            self.text(tx,ty,nref(ref),15,anchor=anchor,native=False);self.text(tx,ty+19,p['value'],14,anchor=anchor,native=False)
        else:
            self.text(x,y-(145 if k=='U' else 63),nref(ref)+'  '+p['value'],16,anchor='middle',native=False)
        for num,(dx,dy,nm,ang) in pindef.items():
            if k in ('Q','U','D','J','T'):
                self.text(x+dx+3,y+dy-4,f'{num}:{nm}',10,'#64717b',native=False)
            if p['pins'].get(num)=='NC':
                # Only draw the cross where the library pin is a normal type. When the
                # symbol already declares the pin as no_connect (U1 pins 1/5/8), KiCad
                # treats an extra flag as redundant and reports both "flag dangling"
                # and "NC pin connected". Skipping it removes 6 warnings and changes
                # nothing electrical: the pin is still unconnected.
                if nm != 'NC':
                    self.path([(x+dx-4,y+dy-4),(x+dx+4,y+dy+4)],'#b34845');self.path([(x+dx-4,y+dy+4),(x+dx+4,y+dy-4)],'#b34845');self.ncs.append((x+dx,y+dy))
        return {n:(x+d[0],y+d[1]) for n,d in pindef.items()}
    def save(self,native=True):
        # Automatically split same-net branches; crossing other nets never makes a junction.
        self.svg.append('')
        (OUT/'svg'/(self.name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}"><g font-family="Microsoft YaHei">'+''.join(self.svg)+'</g></svg>',encoding='utf-8')
        dump(OUT/'qa'/(self.name+'_scene.json'),dict(components=self.comps,wires=self.lines,labels=self.labels))
        if native:write_kicad(self)

def symbol_geometry(k,orient):
    # Local SVG coordinates; pins end on the component boundary. KiCad y is inverted locally.
    if k in ('R','C','P','T','L','W','D'):
        pins={'1':(-30,0,'',0),'2':(30,0,'',180)}
        if k=='R':g=[[(-30,0),(-20,0)],[(-20,-7),(20,-7),(20,7),(-20,7),(-20,-7)],[(20,0),(30,0)]]
        elif k in ('C','P','T'):
            g=[[(-30,0),(-5,0)],[(-5,-15),(-5,15)],[(5,-15),(5,15)],[(5,0),(30,0)]]
            if k=='P':g += [[(-17,-20),(-17,-10)],[(-22,-15),(-12,-15)]]
            if k=='T':
                g += [[(-17,22),(17,-22)],[(7,-19),(17,-22),(17,-12)]];pins['1']=(-30,0,'S',0);pins['2']=(30,0,'R',180)
        elif k=='L':
            g=[[(-30,0),(-23,0)]]
            coil=[]
            for i in range(4):
                coil += [(-23+i*11.5+j*11.5/12,-9*math.sin(math.pi*j/12)) for j in range(13)]
            g += [coil,[(23,0),(30,0)]]
        elif k=='W':g=[[(-30,0),(30,0)]]
        else:
            # Left anode physical pin 2, right cathode physical pin 1.
            pins={'2':(-30,0,'A',0),'1':(30,0,'K',180)}
            g=[[(-30,0),(-12,0)],[(-12,-14),(-12,14),(10,0),(-12,-14)],[(10,-14),(10,14)],[(10,0),(30,0)]]
        if orient=='v':
            g=[[(-b,a) for a,b in poly] for poly in g];pins={n:(-b,a,nm,(ang-90)%360) for n,(a,b,nm,ang) in pins.items()}
        elif orient=='hflip':
            g=[[(-a,b) for a,b in poly] for poly in g];pins={n:(-a,b,nm,(180-ang)%360) for n,(a,b,nm,ang) in pins.items()}
        return g,pins
    if k=='Q':
        return [[(-40,0),(-10,0)],[(-10,-22),(-10,22)],[(-10,-12),(20,-30),(20,-40)],[(-10,12),(20,30),(20,40)],[(20,30),(8,28),(13,19),(20,30)]],{'2':(-40,0,'B',0),'3':(20,-40,'C',270),'1':(20,40,'E',90)}
    if k=='U':
        return [[(-40,-45),(-40,45),(60,0),(-40,-45)],[(-60,-20),(-40,-20)],[(-60,20),(-40,20)],[(60,0),(80,0)],[(0,-70),(0,-27)],[(0,70),(0,27)],[(-33,-20),(-23,-20)],[(-28,-25),(-28,-15)],[(-33,20),(-23,20)]],{'3':(-60,-20,'+',0),'2':(-60,20,'-',0),'7':(0,-70,'V+',270),'4':(0,70,'V-',90),'6':(80,0,'OUT',180),'1':(35,-60,'NC',270),'5':(55,-60,'NC',270),'8':(75,-60,'NC',270)}
    if k=='J':
        return [[(-8,-8),(12,-8),(12,28),(-8,28),(-8,-8)],[(-30,0),(0,0)],[(-30,20),(0,20)]],{'1':(-30,0,'SIG/+',0),'2':(-30,20,'GND',0)}
    raise ValueError(k)

def write_kicad(sc):
    lib={};instances=[];allpins=[]
    for c in sc.comps:
        key='S05:'+c['kind']+'_'+c['orient'];short=key.split(':')[1]
        if key not in lib:
            shapes=[]
            for poly in c['geometry']:
                shapes.append('(polyline (pts '+' '.join(f'(xy {mm(x)} {mm(-y)})' for x,y in poly)+') (stroke (width 0.254) (type default)) (fill (type none)))')
            pins=[]
            for n,(x,y,nm,ang) in c['pindef'].items():
                typ='no_connect' if nm=='NC' else 'passive'
                # Geometry includes the lead, so zero-length pins match visible wire ends exactly.
                pins.append(f'(pin {typ} line (at {mm(x)} {mm(-y)} {ang}) (length 0) (name {q(nm)} (effects (font (size 1.27 1.27)))) (number {q(n)} (effects (font (size 1.27 1.27)))))')
            lib[key]=f'(symbol {q(key)} (pin_names (offset 0) hide) (pin_numbers hide) (in_bom yes) (on_board yes) (property "Reference" "X" (at 0 0 0) (effects (font (size 1.27 1.27)))) (property "Value" {q(short)} (at 0 0 0) (effects (font (size 1.27 1.27)))) (symbol {q(short+"_0_1")} '+''.join(shapes)+f') (symbol {q(short+"_1_1")} '+''.join(pins)+'))'
        x,y=c['x'],c['y'];ref=nref(c['ref']);rid=uid(sc.name+'/'+ref)
        tx=x+24 if c['orient']=='v' and c['kind'] in 'RCPTLW' else x
        ty=y-7 if c['orient']=='v' and c['kind'] in 'RCPTLW' else y-75 if c['kind']=='W' else y-39 if c['kind'] in 'RCPTLWD' else y-145 if c['kind']=='U' else y-63
        props=f'(property "Reference" {q(ref)} (at {mm(tx)} {mm(ty)} 0) (effects (font (size 2.54 2.54)))) (property "Value" {q(c["value"])} (at {mm(tx)} {mm(ty+19)} 0) (effects (font (size 2.54 2.54))))'
        instances.append(f'(symbol (lib_id {q(key)}) (at {mm(x)} {mm(y)} 0) (unit 1) (in_bom yes) (on_board yes) (uuid {rid}) {props} '+''.join(f'(pin {q(n)} (uuid {uid(rid+n)}))' for n in c['pindef'])+f' (instances (project {q(sc.name)} (path "/{sc.root}" (reference {q(ref)}) (unit 1)))))')
        allpins += [(c['pins'][n],(x+d[0],y+d[1])) for n,d in c['pindef'].items() if c['pins'][n]!='NC']
    points=defaultdict(set)
    for n,a,b in sc.lines:points[n].update([a,b])
    for n,p in allpins:points[n].add(p)
    for n,a,b in sc.lines:
        for n2,c,d in sc.lines:
            if n!=n2:continue
            if a[1]==b[1] and c[0]==d[0] and min(a[0],b[0])<=c[0]<=max(a[0],b[0]) and min(c[1],d[1])<=a[1]<=max(c[1],d[1]):
                points[n].add((c[0],a[1]))
    def on(p,a,b):
        return abs((p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]))<1e-6 and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])
    wires=[];edges=set();degrees=defaultdict(int)
    for n,a,b in sc.lines:
        ps=sorted([p for p in points[n] if on(p,a,b)],key=lambda p:(p[0]-a[0])**2+(p[1]-a[1])**2)
        for u,v in zip(ps,ps[1:]):
            e=(n,*sorted([u,v]))
            if e in edges:continue
            edges.add(e);degrees[(n,u)]+=1;degrees[(n,v)]+=1
            wires.append(f'(wire (pts (xy {mm(u[0])} {mm(u[1])}) (xy {mm(v[0])} {mm(v[1])})) (stroke (width 0) (type default)) (uuid {uid(sc.name+str(e))}))')
    jun=[]
    for (n,(x,y)),deg in degrees.items():
        if deg>=3:
            jun.append(f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) (uuid {uid(sc.name+"junction"+str((n,x,y)))}))')
            sc.circle(x,y)
    labels=[f'(label {q(n)} (at {mm(x)} {mm(y)} 0) (effects (font (size 2.54 2.54)) (justify left bottom)) (uuid {uid(sc.name+"label"+str((n,x,y)))}))' for n,x,y in dict.fromkeys(sc.labels)]
    texts=[f'(text {q(t)} (at {mm(x)} {mm(y)} 0) (effects (font (size {mm(s*.65)} {mm(s*.65)})) (justify left bottom)) (uuid {uid(sc.name+"text"+str(i))}))' for i,(x,y,t,s) in enumerate(sc.texts)]
    ncs=[f'(no_connect (at {mm(x)} {mm(y)}) (uuid {uid(sc.name+"nc"+str((x,y)))}))' for x,y in sc.ncs]
    content=f'(kicad_sch (version 20230121) (generator s05_netlist_drawings) (uuid {sc.root}) (paper "User" {mm(sc.w)} {mm(sc.h)}) (lib_symbols '+''.join(lib.values())+')'+''.join(jun+wires+labels+texts+instances+ncs)+' (sheet_instances (path "/" (page "1"))))'
    (OUT/'kicad'/(sc.name+'.kicad_sch')).write_text(content,encoding='utf-8')
    # Re-save SVG with the computed electrical junctions.
    (OUT/'svg'/(sc.name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{sc.w}" height="{sc.h}" viewBox="0 0 {sc.w} {sc.h}"><g font-family="Microsoft YaHei">'+''.join(sc.svg)+'</g></svg>',encoding='utf-8')

def lc(sc,y=250,terminal=False):
    # `terminal=False` for the full receiver sheet, which draws its own JRF at the
    # right edge (see full()). The standalone LC sheet sets terminal=True so its
    # 'input' net ends on a symbol instead of a bare label with a single pin.
    if terminal:
        sc.comp('JRF',60,y)
        sc.wire('input',(30,y),(120,y),label=True)
        sc.wire('0',(30,y+20),(30,y+60),label=True)
    else:
        sc.wire('input',(80,y),(120,y),label=True)
    sc.comp('CSEL',150,y)
    sc.comp('CK',550,y);sc.comp('COUT',950,y)
    for i,xs in [(1,[260,360,460]),(2,[660,760,860])]:
        n='tank'+str(i)
        sc.wire(n,((180 if i==1 else 580),y),((520 if i==1 else 920),y),label=True)
        for ref,x in zip([f'LSEL{i}',f'CFIX{i}',f'CT{i}'],xs):
            sc.comp(ref,x,y+130,'v');sc.wire(n,(x,y),(x,y+100));sc.wire('0',(x,y+160),(x,y+230))
        sc.wire('0',(xs[0],y+230),(xs[-1],y+230),label=True)
    sc.wire('port',(980,y),(1040,y),(1040,y+100),label=True);sc.comp('RPORT',1040,y+130,'v');sc.wire('0',(1040,y+160),(1040,y+230),label=True)
    sc.text(80,y+275,'CT1：30 pF + 2–18 pF；CT2：39 pF + 2–18 pF。',16)
    sc.text(80,y+303,'微调起点约 10.61 / 7.15 pF；需按受控加载调谐，不能由旋角定电容。',15)
    sc.text(80,y+331,'tank1 / tank2 不设长测试柱：禁止直接挂普通 10 pF 探头验收。',16,'#a43c36')

def rf_stage(sc,i,x,y):
    for ref,xx,yy in [(f'RBT{i}',x-110,y-100),(f'RBB{i}',x-110,y+100),(f'RC{i}',x+20,y-130),(f'REU{i}',x+20,y+100),(f'REB{i}',x+20,y+190),(f'CEB{i}',x+130,y+190)]:sc.comp(ref,xx,yy,'v')
    sc.comp('Q'+str(i),x,y);sc.comp('CIN'+str(i),x-210,y)
    sc.wire('vcc',(x-110,y-180),(x+20,y-180),(x+20,y-160),label=True);sc.wire('vcc',(x-110,y-180),(x-110,y-130))
    sc.wire('b'+str(i),(x-180,y),(x-110,y),(x-40,y),label=True);sc.wire('b'+str(i),(x-110,y-70),(x-110,y+70))
    sc.wire('c'+str(i),(x+20,y-100),(x+20,y-40),label=True)
    sc.wire('e'+str(i),(x+20,y+40),(x+20,y+70),label=True)
    sc.wire('eb'+str(i),(x+20,y+130),(x+20,y+160),(x+130,y+160),label=True)
    sc.wire('0',(x-110,y+130),(x-110,y+240),(x+130,y+240),(x+130,y+220),label=True);sc.wire('0',(x+20,y+220),(x+20,y+240))

def full():
    s=Scene('01_receiver',2200,1550,'S05 A + G22 完整接收端原理图','连接依据：S05-08 T_sq50_six_source.cir / T_sq10_six_source.cir；9 V；31 MHz；约 2 MHz 双调谐。')
    s.text(70,145,'A  双调谐 LC：460 nH / 15 pF / 2.4 pF / 11 pF',21)
    lc(s)
    s.text(1120,145,'B  原 Q1 / Q2 射频共射级',21)
    rf_stage(s,1,1370,350);rf_stage(s,2,1830,350)
    s.wire('port',(1130,350),(1090,350),label=True)
    s.wire('c1',(1390,310),(1510,310),(1510,350),(1590,350))
    s.wire('c2',(1850,310),(2020,310),label=True)
    s.text(1500,290,'TP_C1',14);s.text(1970,290,'TP_C2',14)
    s.text(1130,635,'Q1/Q2/QBUF：物理 1=E、2=B、3=C（onsemi 2N3904 条件映射）。',15)
    s.text(1130,660,'各级供电共用 vcc；CDQ1/CDQ2 分别就近旁路。',15)
    s.text(70,710,'C  QBUF 射随缓冲 + BAT85 包络检波',21)
    s.comp('CBUF',100,900);s.wire('c2',(70,900),(40,900),label=True)
    s.comp('QBUF',300,900);s.comp('RBTB',190,800,'v');s.comp('RBBB',190,1000,'v')
    s.wire('bb',(130,900),(260,900),label=True);s.wire('bb',(190,830),(190,970))
    s.wire('vcc',(190,770),(190,750),label=True);s.wire('vcc',(320,860),(320,800),label=True)
    s.comp('REBUF',320,1030,'v');s.wire('ee',(320,940),(320,1000),label=True)
    s.comp('COBUF',450,940);s.wire('ee',(320,940),(420,940));s.comp('RRF',550,1030,'v')
    s.wire('rf',(480,940),(620,940),label=True);s.wire('rf',(550,940),(550,1000))
    s.comp('RCONNECT',650,940);s.comp('DDET',760,940);s.wire('an',(680,940),(730,940),label=True)
    s.comp('RDET',860,1030,'v');s.comp('CDET',960,1030,'v');s.comp('RFILT',1060,940);s.comp('CFILT',1160,1030,'v')
    s.wire('det',(790,940),(1030,940),label=True);s.wire('det',(860,940),(860,1000));s.wire('det',(960,940),(960,1000))
    s.wire('out',(1090,940),(1200,940),label=True);s.wire('out',(1160,940),(1160,1000))
    s.text(540,910,'TP_RF',13);s.text(860,910,'TP_DET',13);s.text(1150,910,'TP_ENV',13)
    for x,y in [(190,1030),(320,1060),(550,1060),(860,1060),(960,1060),(1160,1060)]:s.wire('0',(x,y),(x,1110))
    s.wire('0',(190,1110),(1160,1110),label=True)
    s.text(70,1150,'DDET 阴极色环朝 det；RCONNECT 为短连线的 0.1 Ω 模型，实物不另买电阻。',15)
    s.text(70,1176,'BAT85S 尚未资格化；不可因外形相似就认定与原 Nexperia BAT85 模型等效。',15,'#a43c36')
    s.text(1290,740,'D  OPA197：G = 1 + 210k / 10k = 22',21)
    s.comp('CCOUP',1320,940);s.wire('out',(1290,940),(1250,940),label=True)
    s.comp('U1',1600,960);s.wire('bbin',(1350,940),(1540,940),label=True);s.comp('RBIAS',1420,1040,'v');s.wire('bbin',(1420,940),(1420,1010))
    s.text(1430,920,'TP_BBIN',13)
    s.wire('ref',(1420,1070),(1420,1100),label=True)
    s.wire('vcc',(1600,890),(1600,840),label=True);s.wire('0',(1600,1030),(1600,1060),label=True)
    s.comp('ROUT',1800,960);s.wire('bbo',(1680,960),(1770,960),label=True);s.wire('final',(1830,960),(2040,960),label=True)
    s.comp('RFB',1720,1180,'hflip');s.wire('bbo',(1710,960),(1710,1120),(1820,1120),(1820,1180),(1750,1180))
    s.wire('neg',(1540,980),(1510,980),(1510,1180),(1690,1180),label=True)
    s.comp('RG',1510,1260,'v');s.wire('neg',(1510,1180),(1510,1230));s.wire('ref',(1510,1290),(1510,1320),label=True)
    s.text(1840,1020,'TP_FINAL：20 kHz 基带',15)
    s.text(1840,1046,'反馈取 bbo，位于100 Ω之前。',14,'#a43c36')
    s.text(1840,1072,'输出含直流偏置；非逻辑门输出。',14)
    s.text(70,1250,'E  9 V 电源 / 3 V 参考 / 实物去耦',21)
    s.comp('RVT',170,1340,'v');s.comp('RVB',170,1440,'v');s.comp('CVREF',310,1440,'v')
    s.wire('vcc',(170,1310),(170,1280),label=True);s.wire('ref',(170,1370),(170,1390),(310,1390),(310,1410),label=True);s.wire('ref',(170,1390),(170,1410))
    s.wire('0',(170,1470),(170,1490),(310,1490),(310,1470),label=True)
    for ref,x in [('CPWR',520),('CDQ1',680),('CDQ2',840),('CDBUF',1000),('CDU1',1160)]:
        s.comp(ref,x,1400,'v');s.wire('vcc',(x,1370),(x,1320),label=True);s.wire('0',(x,1430),(x,1480),label=True)
    s.text(460,1278,'新增去耦仅属 S05-10 实物配套；原模型没有这些器件。',14,'#945a18')
    s.text(460,1301,'CDU1紧靠U1的7/4脚；CPWR正极接9 V，CVREF正极接ref。',14)
    for ref,x,y in [('JRF',2050,1240),('JPOWER',2050,1360),('JOUT',2050,1480)]:
        s.comp(ref,x,y)
        for num,(dx,dy,_,_) in symbol_geometry('J','h')[1].items():
            n=parts[ref]['pins'][num];s.wire(n,(x+dx,y+dy),(x+dx-70,y+dy),label=True)
    s.text(1560,1410,'NC：U1 1/5/8 悬空；4脚接GND。',15)
    s.text(1560,1436,'输出1 MΩ∥100 pF为外部测试总负载，',14)
    s.text(1560,1462,'不可与示波器负载不加核算地重复并联。',14)
    s.save();return s

def lc_sheet():
    s=Scene('02_lc_module',1740,1060,'S05 首块实物：独立 LC 模块接线图','无源 LC 板不接 9 V。先核实信号源与探头；可拆夹具只接在 COUT 后的 port。')
    lc(s,230,terminal=True)
    s.rect(1120,150,550,425,'#fff9ed','#bc8638','8,5')
    s.text(1150,186,'可拆测量负载（不属于接收机）',20,'#855b24')
    r=dict(ref='RMEAS',kind='R',value='953',pins={'1':'port','2':'0'},source='S05-10',group='FIXTURE',note='整链接入时拆除',package='1%')
    c=dict(ref='CEXT',kind='C',value='TBD / budget',pins={'1':'port','2':'0'},source='S05-10',group='FIXTURE',note='CEXT+Cprobe+Cconnection≈14pF',package='C0G')
    s.comp('RMEAS',1200,360,'v',r);s.comp('CEXT',1410,360,'v',c)
    s.wire('port',(1040,230),(1550,230),label=True)
    for x in [1200,1410]:s.wire('port',(x,230),(x,330));s.wire('0',(x,390),(x,460))
    s.wire('0',(1200,460),(1550,460),label=True)
    s.text(1490,285,'TP_PORT',18);s.text(1490,311,'短接探头尖端',14)
    s.text(1150,510,'探头Rin计入并联电导；CEXT不能照抄固定值。',15)
    s.text(1150,537,'原校核：953 Ω∥RPORT 1 MΩ∥接口1 MΩ；总14 pF。',13)
    lines=[
        '1  信号源内部约50 Ω → 同轴芯线 → input；屏蔽层 → GND。源阻抗不是入口并联50 Ω。',
        '2  所有 tank 接点保持短小；不装长测试针、不接普通10 pF探头，也不直连示波器50 Ω。',
        '3  CEXT = 14 pF − 实际探头尖端电容 − 连接寄生；探头未知时，CEXT待定，暂不验收。',
        '4  普通10×探头仅在port负载预算与31 MHz传递校准满足条件后使用；DS2102E按探头手册选1 MΩ。',
        '5  接真实Q1时，拆除953 Ω、CEXT及测量探头/缓冲；保留RPORT，port接CIN1再到Q1基极。',
        '6  两线圈轴向初始近似正交；几何间距不是互感合格证；固定工具/地铜位置后做加载扫频。',
        '7  独立port参考：中心31.030 MHz、BW1.885 MHz；工程带宽目标1.85–1.95 MHz，均非实测。',
        '8  CT1物理1=S→tank1、2=R→GND；CT2同理。S/R依厂家孔位图和实物确认，不按任意视角猜。',
        '9  原模型总CTUNE1=41.609801788 pF，CTUNE2=47.1490753446 pF；包含各1 pF布局寄生。',
        '10 不安装RLOSS、RCT、CSELF或CBOARD离散件；不能把寄生预算再焊成一个1 pF电容。'
    ]
    for i,t in enumerate(lines):s.text(60,650+34*i,t,16,'#a43c36' if i in (1,2) else '#172f3b')
    s.save();return s

def model_sheet():
    s=Scene('09_model_and_test_boundaries',1900,1150,'网表模型与实物边界：禁止把等效模型全部焊上板','本页保留原网表元件数值及内部节点；RLOSS/RCT/CSELF为模型；RSOURCE/RBBLOAD/CLOAD是测试环境。')
    def model(ref,x,y,orient='h'):
        r=src[ref]
        p=dict(ref=ref,kind=r['kind'],value=r['value'],pins={'1':r['nodes'][0],'2':r['nodes'][1]},source=ref,group='MODEL',package='网表等效模型/外部测试环境',note='不能自动视为采购元件')
        s.comp(ref,x,y,orient,p)
    model('RSOURCE',120,230)
    # The 'src' net held a single pin (RSOURCE.1 at 90,230). This sheet documents the
    # test environment, so the source terminal belongs on it: an explicit symbol makes
    # the net meaningful and closes the ERC error, without inventing a board part
    # (group='MODEL' keeps it out of the purchase list).
    # Vertical J symbol by this generator's rotation rule puts pin 1 at (x-30, y)
    # and pin 2 at (x-30, y+20). Placing it at y=230 lets pin 1 meet RSOURCE.1
    # (at 90,230) with one straight wire.
    src_term=dict(ref='JSRC',kind='J',value='SOURCE',pins={'1':'src','2':'0'},
                  source='测试环境',group='MODEL',
                  package='外部激励接入点，不焊在接收板上',
                  note='模型图专用：表示RSOURCE外接的信号源，非板上元件')
    s.comp('JSRC',40,230,'v',src_term)
    s.wire('src',(10,230),(90,230),label=True)
    s.wire('0',(10,250),(10,270),(120,270),label=True)
    model('CSEL',250,230);s.wire('input',(150,230),(220,230),label=True)
    model('CK',850,230);model('COUT',1530,230)
    for i,xs in [(1,[340,510,680]),(2,[1040,1210,1380])]:
        n='tank'+str(i);start,end=(280,820) if i==1 else (880,1500)
        s.wire(n,(start,230),(end,230),label=True)
        x1,x2,x3=xs
        for r,x in [(f'RLOSS{i}',x1),(f'RCT{i}',x3)]:model(r,x,340,'v');s.wire(n,(x,230),(x,310))
        for r,x in [(f'LSEL{i}',x1),(f'CSELF{i}',x2),(f'CTUNE{i}',x3)]:model(r,x,470,'v');s.wire('0',(x,500),(x,550))
        s.wire(f'ln{i}',(x1,370),(x1,440),label=True);s.wire(n,(x2,230),(x2,440));s.wire(f'ctl{i}',(x3,370),(x3,440),label=True)
        s.wire('0',(x1,550),(x3,550),label=True)
    model('RPORT',1700,470,'v');s.wire('port',(1560,230),(1700,230),(1700,440),label=True);s.wire('0',(1700,500),(1700,550),label=True)
    s.text(60,610,'实物映射：RLOSS+LSEL+CSELF → 一只132-17L；RCT+CTUNE → 固定电容+微调及其真实损耗/布局寄生。',17)
    s.text(60,645,'41.609801788 = 30 + 10.609801788 + 1 pF；47.1490753446 = 39 + 7.1490753446 + 1 pF。',18)
    s.text(60,679,'1 pF是模型布局预算，不是另装的电容。物理网络是该模型的实现目标，不宣称与理想网表逐值完全等效。',16,'#a43c36')
    s.rect(70,725,760,300,'#fff9ed','#bc8638','8,5');s.text(95,760,'基带外部总测试负载（不永久叠加）',20)
    model('RBBLOAD',350,880,'v');model('CLOAD',620,880,'v')
    s.wire('final',(150,810),(620,810),(620,850),label=True);s.wire('final',(350,810),(350,850));s.wire('0',(350,910),(350,970),(620,970),(620,910),label=True)
    s.text(900,770,'外部激励与供电',21)
    for i,t in enumerate([
        'VMOD/BSIG：31 MHz AM数值激励，非接收机元件。',
        'RSOURCE=50 Ω：发生器等效源阻抗；不额外串/并50 Ω凑数。',
        'VSUP vcc 0 9：外部9 V正电源，负端接公共地。',
        'RLOAD=1e15 Ω：检波开路数值残留，不采购、不焊接。',
        'RCONNECT=0.1 Ω：连接等效；实物短线见主图。',
        '.ic/.nodeset：暖机初值，只影响求解，不能画成真实电压源。',
        'BAT85内R1/D1与OPA197宏模型内部器件不作为外部BOM。',
        '完整原值、源行号：tables/原始网表全部元件.csv。']):s.text(900,810+30*i,t,15)
    s.save();return s

if __name__=='__main__':
    sc1=full();sc2=lc_sheet();sc3=model_sheet()
    dump(OUT/'qa/physical_parts.json',parts)
    table('BOM_逐器件.csv',[{'图纸位号':nref(p['ref']),'原用名':p['ref'],'数值':p['value'],'数量':1,'类型':p['group'],'原网表位号':p['source'],'引脚与节点':'; '.join(n+'='+v for n,v in p['pins'].items()),'封装与资格':p['package'],'说明':p['note']} for p in parts.values()])
    table('原始网表全部元件.csv',[{'位号':r['ref'],'数值':r['value'],'节点顺序':' '.join(r['nodes']),'源文件行':r['line'],'处理':'模型/激励/测试边界，见转换说明' if r['ref'] in excluded else '保留连接；见BOM物理引脚映射'} for r in raw])
    nodes=defaultdict(list)
    for p in parts.values():
        for n,v in p['pins'].items():
            if v!='NC':nodes[v].append(nref(p['ref'])+'.'+n)
    table('逐节点接线表.csv',[{'节点':n,'全部物理端点':' ; '.join(sorted(ps)),'注意':'公共地；不等于ref' if n=='0' else '仅9V正电源' if n=='vcc' else '禁止普通探头直接加载' if n.startswith('tank') else '3V分压参考，禁止接地' if n=='ref' else ''} for n,ps in sorted(nodes.items())])
    print(OUT)
    print('Parts:',len(parts),'source elements:',len(raw))
