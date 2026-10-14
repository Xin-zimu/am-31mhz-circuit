from pathlib import Path
import re,xml.etree.ElementTree as ET,hashlib,json,sys
HERE=Path(__file__).resolve().parent
lf='--lf' in sys.argv
t=(HERE/('lf_import.xml' if lf else 'v4_import.xml')).read_text(encoding='ascii')
root=ET.fromstring(t)
port_net={}
for n in root.iter('CiNode'):
    for p in n.findall('Ports/Item'):port_net[p.get('CiID')]=n.get('LocalName','').replace('&ASC','')
port_name={}
for item in root.iter('Item'):
    p=item.find('CiPort')
    if p is not None:port_name[item.get('CiID')]=p.get('LocalName','').replace('&ASC','')
for c in root.iter('CiComponent'):
    if c.get('LocalName','').startswith('&ASCA'):
        print(c.get('LocalName'),[(port_name.get(p.get('CiID')),port_net.get(p.get('CiID'))) for p in c.findall('Ports/Item')])
model=(HERE/'models/LM393_TI.lib').read_text()
# Multisim expands %tN into the actual connected net. Only the comparator
# subcircuit name is changed; the TI model body is preserved verbatim.
comparators=[]
for c in root.iter('CiComponent'):
    if not c.get('LocalName','').startswith('&ASCA'):continue
    ports={port_name.get(p.get('CiID')):port_net.get(p.get('CiID')) for p in c.findall('Ports/Item')}
    if ports.get('7') in ['OSC','PWM_RAW']:
        comparators.append((c.get('LocalName').replace('&ASC',''),'LM393_OSC_V4' if ports['7']=='OSC' else 'LM393_PWM_V4'))
assert len(comparators)==2
for local,modelname in comparators:
    pattern=rf'<CiComponent Class="CiComponent" LocalName="&amp;ASC{local}".*?</CiComponent>'
    m=re.search(pattern,t,re.S); assert m
    comp=ET.fromstring(m[0]); template=comp.find('.//CiaSpiceTmpltExprt')
    assert template is not None
    new='x%p %t1 %t2 %t3 %t8 %t7 '+modelname+'\n'+model.replace('LM393_TI',modelname)
    old=template.get('String')
    for e in comp.iter():
        for k,v in list(e.attrib.items()):
            if v.startswith('&ASCx%p ') and 'POLYSource%p' in v:e.set(k,'&ASC'+new)
    # Multisim's proprietary reader requires literal newlines in attributes.
    # Numeric XML character references are misread by that reader.
    serialized=ET.tostring(comp,encoding='unicode').replace('&#10;','\n').replace('&#13;','\r')
    t=t[:m.start()]+serialized+t[m.end():]
    # Visible source labels identify the installed device model.
    pwm=modelname=='LM393_PWM_V4'
    t=t.replace('ECOMP2_ECOMP2' if pwm else 'ECOMP1_ECOMP1',
                'LM393P_U1B' if pwm else 'LM393P_U1A')
    t=t.replace('&amp;ASCECOMP2' if pwm else '&amp;ASCECOMP1',
                '&amp;ASCU1B' if pwm else '&amp;ASCU1A')
t=t.replace('Output="&amp;ASC1*V1"','Output="&amp;ASCLM393/TI"')
# Draw custom comparator model blocks, retaining the already verified terminal
# locations and electrical port IDs. These are functional ports, not DIP numbers.
for local,_ in comparators:
    c=next(c for c in root.iter('CiComponent') if c.get('LocalName')=='&ASC'+local)
    symid=c.get('SymCompID')
    match=re.search(r'<Item ID="'+symid+r'" Class="CIITSymbolComp">\s*<CIITSymbolComp.*?</CIITSymbolComp>\s*</Item>',t,re.S)
    assert match
    item=ET.fromstring(match[0]);sym=item.find('CIITSymbolComp');objs=sym.find('Objects')
    text_templates=[]
    for obj in list(objs):
        e=list(obj)[0]
        if e.tag.startswith('COD'):
            if e.tag=='CODTextComp':text_templates.append(e.attrib.copy())
            objs.remove(obj)
        elif e.tag=='CIITSymTextCompValue':e.set('Hidden','1')
        elif e.tag=='CIITPinSymbolComp':
            pname=e.get('PinName','').replace('&ASC','')
            if pname not in ['1','2','3','7','8']:e.set('Hidden','1')
    # Reuse the removed primitive IDs; none are electrical connections.
    source=ET.fromstring(match[0]).find('CIITSymbolComp/Objects')
    free=[o.get('ID') for o in source if list(o)[0].tag.startswith('COD')]
    poly=next(list(o)[0] for o in source if list(o)[0].tag=='CODPolygonComp')
    poly.find('Points').clear()
    for x,y in [(45,45),(108,45),(108,126),(45,126),(45,45)]:ET.SubElement(poly.find('Points'),'Item',X=str(x),Y=str(y))
    obj=ET.SubElement(objs,'Item',ID=free.pop(),Class='CODPolygonComp');obj.append(poly)
    labels=[('+',50,47),('-',50,59),('V+',50,76),('OUT',79,47),('GND',78,110),('LM393',55,92)]
    for label,x,y in labels:
        attrs=text_templates[0].copy();attrs.update(Output='&ASC'+label,**{'Transformer-M20':str(x),'Transformer-M21':str(y),'Font-Height':'-9'})
        obj=ET.SubElement(objs,'Item',ID=free.pop(),Class='CODTextComp');ET.SubElement(obj,'CODTextComp',attrs)
    replacement=ET.tostring(item,encoding='unicode').replace('&#10;','\n').replace('&#13;','\r')
    t=t[:match.start()]+replacement+t[match.end():]
diode='D(Is=20n N=1.06 Rs=2 Cjo=2p M=0.33 Vj=0.35 Bv=70 Ibv=10u)'
t=t.replace('.model DIODE__DIODES_VIRTUAL__1  D"','.model DIODE__DIODES_VIRTUAL__1  '+diode+'"')
t=t.replace('.model DIODE  D"','.model DIODE  '+diode+'"')
# Set the saved transient analysis explicitly, including selected voltage traces.
def span(s, key):
    start=re.search(r'(?<![A-Za-z])'+re.escape(key)+r'\{',s).start(); p=start+len(key); depth=0
    for i in range(p,len(s)):
        if s[i]=='{':depth+=1
        elif s[i]=='}':
            depth-=1
            if depth==0:return start,i+1
    raise ValueError(key)
a,b=span(t,'TRAN:list'); tr=t[a:b]
for key,value in [('TSTOP','0.0015' if lf else '0.0002'),('TSTART','0'),('TSTEP','5e-08' if lf else '2e-09'),('TMAX','5e-08' if lf else '2e-09')]:
    tr=re.sub(key+r':(?:double|string)\{[^}]*\}',key+':double{'+value+'}',tr,count=1)
tr=tr.replace('ANALYSIS_ID:long{0}','ANALYSIS_ID:long{3}',1)
ns,ne=span(tr,'Nodes:list')
names=['v1','ramp','pwm_raw'] if lf else ['v1','ramp','pwm_raw','tp3','tp6','v2']
nodes='Nodes:list{'+''.join('NODE:list{GROUP:long{768}\nPLOTDEVICETYPE:long{0}\nTYPE:long{3}\nNAME:string{$'+n+'}\nDESCRIPTION:string{}\nINI_VALUE:double{0}\n}\n' for n in names)+'NodeList_EnableDigitalNode:long{1}\nNodeList_EnableOutputToDigitalGraph:long{0}\n}'
tr=tr[:ns]+nodes+tr[ne:]
ns,ne=span(tr,'UserNodes:list')
tr=tr[:ns]+nodes.replace('Nodes:list{','UserNodes:list{',1)+tr[ne:]
tr=tr.replace('2:list{IsEnabled:long{0}\nreltol:double{0.001}', '2:list{IsEnabled:long{1}\nreltol:double{0.0001}')
tr=tr.replace('trtol:double{7}','trtol:double{1}')
tr=tr.replace('MSM_ASYS_OPT:long{1}','MSM_ASYS_OPT:long{0}')
tr=tr.replace('IC:string{auto_ic}','IC:string{zero_ic}')
t=t[:a]+tr+t[b:]
t=t.replace('MAX_POINTS:long{128000}','MAX_POINTS:long{2000000}')
out=HERE/('lf_fixed.xml' if lf else 'v4_fixed.xml');out.write_text(t,encoding='ascii')
print(out)
