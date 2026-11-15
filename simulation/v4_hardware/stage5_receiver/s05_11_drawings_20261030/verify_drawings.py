"""Independent connectivity checks against KiCad's exported XML, not SVG metadata.
No simulation, no Git modification. Must run after kicad-cli sch export netlist.
"""
from pathlib import Path
import json,xml.etree.ElementTree as ET,hashlib,sys,re,csv
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
HERE=Path(__file__).resolve().parent;STAGE=HERE.parent;ROOT=STAGE.parents[2]
OUT=ROOT/'output/pdf/S05_A_G22_施工图_20261030'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()
def nr(s):return s if re.search(r'\d$',s) else s+'1'
errors=[];checks={}
parts=read(OUT/'qa/physical_parts.json');fixture=read(OUT/'qa/fixture_parts.json')

def xml_check(name,expected):
    tree=ET.parse(OUT/'qa'/f'{name}.xml');pins={};values={}
    for c in tree.findall('./components/comp'):values[c.attrib['ref']]=c.findtext('value')
    for net in tree.findall('./nets/net'):
        n=net.attrib['name'].lstrip('/')
        if n.startswith('unconnected-'):n='NC'
        for a in net.findall('node'):
            key=(a.attrib['ref'],a.attrib['pin']);assert key not in pins
            pins[key]=n
    ep={(nr(r),pin):net for r,p in expected.items() for pin,net in p['pins'].items()}
    if pins!=ep:
        for key in sorted(set(pins)|set(ep)):
            if pins.get(key)!=ep.get(key):errors.append(f'{name} {key}: KiCad={pins.get(key)}, expected={ep.get(key)}')
    for r,p in expected.items():
        if values.get(nr(r))!=p['value']:errors.append(f'{name} {r}: value mismatch {values.get(nr(r))} != {p["value"]}')
    if set(values)!={nr(r) for r in expected}:errors.append(name+' unexpected/missing symbols')
    checks[name]={'components':len(values),'physical_pins':len(ep),'nets_including_NC':len(tree.findall('./nets/net')),'all_pins_and_values_equal':not any(e.startswith(name) for e in errors)}

xml_check('01_receiver',parts)
lcset={r:p for r,p in parts.items() if r in ['CSEL','CK','COUT','RPORT','LSEL1','LSEL2','CFIX1','CFIX2','CT1','CT2','JRF']}
lcset.update({'RMEAS':dict(value='953',pins={'1':'port','2':'0'}),'CEXT':dict(value='TBD / budget',pins={'1':'port','2':'0'})})
xml_check('02_lc_module',lcset)

# Parse raw top-level SPICE statements independently; physical transformations are explicit.
source={};inside=False
for l in (OUT/'sources/T_sq50_six_source.cir').read_text().splitlines():
    t=l.split()
    if not t:continue
    if t[0].lower()=='.subckt':inside=True;continue
    if t[0].lower()=='.ends':inside=False;continue
    if inside or t[0][0] in '.*+':continue
    source[t[0]]=t[1:]
def expect(ref,pins,val):
    if parts[ref]['pins']!=pins or parts[ref]['value']!=val:errors.append('source mapping '+ref)
retained=[]
for ref,p in parts.items():
    original=p['source']
    if original not in source or ref in ['CFIX1','CFIX2','CT1','CT2']:continue
    t=source[original]
    if ref.startswith('LSEL'):
        expect(ref,{'1':'tank'+ref[-1],'2':'0'},t[2])
        i=ref[-1]
        assert source['RLOSS'+i][:2]==['tank'+i,'ln'+i] and t[:2]==['ln'+i,'0']
        assert source['CSELF'+i][:2]==['tank'+i,'0']
    elif ref=='RCONNECT':expect(ref,{'1':t[0],'2':t[1]},'wire / model 0.1R');assert t[2]=='0.1'
    elif ref=='DDET':expect(ref,{'2':t[0],'1':t[1]},t[-1])
    elif ref=='U1':expect(ref,{'3':t[0],'2':t[1],'7':t[2],'4':t[3],'6':t[4],'1':'NC','5':'NC','8':'NC'},t[-1])
    elif ref.startswith('Q'):expect(ref,{'3':t[0],'2':t[1],'1':t[2]},t[-1])
    else:expect(ref,{'1':t[0],'2':t[1]},t[2])
    retained.append(original)
for i,fix,trim in [(1,30,10.609801788),(2,39,7.1490753446)]:
    t=source[f'CTUNE{i}'];assert t[:2]==[f'ctl{i}','0']
    assert source[f'RCT{i}'][:2]==[f'tank{i}',f'ctl{i}']
    if abs(float(t[2].removesuffix('p'))-(fix+trim+1))>1e-9:errors.append(f'CTUNE{i} decomposition')
    assert parts[f'CFIX{i}']['value']==f'{fix}p' and parts[f'CT{i}']['value']=='2-18p'
    for r in [f'CFIX{i}',f'CT{i}']:assert parts[r]['pins']=={'1':f'tank{i}','2':'0'}
assert source['VSUP']==['vcc','0','9']
assert source['RFB']==['bbo','neg','210000'] and source['RG']==['neg','ref','10k']
assert source['XOPA']==['bbin','neg','vcc','0','bbo','OPAx197']
assert source['XDET']==['an','det','BAT85']
assert source['RLOAD']==['out','0','1000000000000000.0']
checks['source_transformations']={'retained_source_elements':len(retained),'supply_9V':True,'gain_22':True,'CT_plus_board_budget_checked':True,'diode_macro_to_physical_pin_reversal_checked':True,'explicit_model_and_fixture_exclusions':['VMOD','BSIG','RSOURCE','VSUP','RLOSS1/2','RCT1/2','CSELF1/2','RLOAD','RBBLOAD','CLOAD']}

model_refs=['RSOURCE','CSEL','CK','COUT','RPORT','RLOSS1','RLOSS2','RCT1','RCT2','CSELF1','CSELF2','LSEL1','LSEL2','CTUNE1','CTUNE2','RBBLOAD','CLOAD']
model_expect={r:dict(value=source[r][2],pins={'1':source[r][0],'2':source[r][1]}) for r in model_refs}
# The source terminal is a drawing aid for the test environment, not a netlist part;
# its nets must match the ones RSOURCE already uses.
model_expect['JSRC']=dict(value='SOURCE',pins={'1':'src','2':'0'})
xml_check('09_model_and_test_boundaries',model_expect)

board=read(OUT/'qa/perfboard_graph.json');placed=[];allparts=parts|fixture
for b,d in board.items():
    padnets={};expected=defaultdict(set)
    for ref,pins in d['placements'].items():
        placed.append(ref)
        if set(pins)!=set(allparts[ref]['pins']):errors.append(b+' missing physical pin '+ref)
        for pin,pt in pins.items():
            pt=tuple(pt);n=allparts[ref]['pins'][pin]
            if n=='NC':n='NC:'+ref+'.'+pin
            if pt in padnets and padnets[pt]!=n:errors.append(b+' pad short '+str(pt))
            padnets[pt]=n
            if not n.startswith('NC:'):expected[n].add(pt)
    for label,(n,pt) in d['pads'].items():
        pt=tuple(pt)
        if pt in padnets and padnets[pt]!=n:errors.append(b+' interface pad short '+label)
        padnets[pt]=n;expected[n].add(pt)
    adj=defaultdict(set)
    for tag,n,a,c in d['links']:
        a,c=tuple(a),tuple(c)
        if padnets.get(a)!=n or padnets.get(c)!=n:errors.append(tag+' wrong endpoint net')
        adj[a].add(c);adj[c].add(a)
    for n,ps in expected.items():
        first=next(iter(ps));seen={first};todo=[first]
        while todo:
            for v in adj[todo.pop()]:
                if v not in seen:seen.add(v);todo.append(v)
        if seen!=ps:errors.append(b+' open or short '+n)
    checks['board_'+b]={'parts':len(d['placements']),'wires':len(d['links']),'pin_pad_conflicts':0,'point_to_point_graph_checked':True,'mechanical_and_RF_qualification':'NOT VERIFIED'}
assert len(placed)==len(set(placed)) and set(placed)==set(allparts)

# Check the six inter-board conductors and the resulting global net partitions.
global_adj=defaultdict(set);expected_global=defaultdict(set);global_nets={}
for b,d in board.items():
    for n,ps in d['nets'].items():
        for pt in ps:
            key=(b,tuple(pt));expected_global[n].add(key);global_nets[key]=n
    for tag,n,a,c in d['links']:
        a,c=(b,tuple(a)),(b,tuple(c));global_adj[a].add(c);global_adj[c].add(a)
with (OUT/'tables/板间连接表.csv').open(encoding='utf-8-sig') as f:inter=list(csv.DictReader(f))
def endpoint(t):
    m=re.match(r'(LC|RF|BB) ([A-Z])(\d+)',t);assert m,t
    return (m[1],(int(m[3]),ord(m[2])-64))
for row in inter[:6]:
    a,b=endpoint(row['端A']),endpoint(row['端B']);n=row['节点']
    if global_nets.get(a)!=n or global_nets.get(b)!=n:errors.append(row['线号']+' inter-board wrong net')
    global_adj[a].add(b);global_adj[b].add(a)
for n,ps in expected_global.items():
    seen={next(iter(ps))};todo=list(seen)
    while todo:
        for v in global_adj[todo.pop()]:
            if v not in seen:seen.add(v);todo.append(v)
    if seen!=ps:errors.append('global board net open/short '+n)
checks['inter_board']={'conductors_checked':6,'global_net_partitions_checked':len(expected_global)}

history=read(OUT/'qa/history_before.json');changed=[];reviewed=[]
external=read(OUT/'qa/reviewed_external_changes.json') if (OUT/'qa/reviewed_external_changes.json').exists() else {}
for name,h in history.items():
    if not (ROOT/name).exists():changed.append(name);continue
    current=sha(ROOT/name)
    if current!=h:
        record=external.get(name,{})
        if record.get('before_sha256')==h and record.get('after_sha256')==current:reviewed.append(name)
        else:changed.append(name)
if changed:errors.extend('history changed: '+n for n in changed)
checks['history']={'files':len(history),'unreviewed_changes':changed,'reviewed_external_append_only_updates':reviewed}
manifest=read(OUT/'qa/source_manifest.json')
for name,m in manifest.items():
    # Read/hash existing arrays only. This does not run ngspice or recompute waveforms.
    p=Path(m['raw_path']);ok=p.exists() and sha(p)==m['raw_sha256_recorded']
    checks[name+'_raw_hash']=ok
    if not ok:errors.append(name+' raw missing/hash mismatch')
result={'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors,'scope':'Connectivity, values, mapping, hole/wire graph, source hashes. NOT hardware validation or RF layout qualification. No simulation run.'}
(OUT/'qa/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(bool(errors))
