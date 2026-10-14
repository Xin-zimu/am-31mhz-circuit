from pathlib import Path
import re,xml.etree.ElementTree as ET
here=Path(__file__).resolve().parent
t=(here/'stage1_import.xml').read_text()
root=ET.fromstring(t)
for comp in root.iter('CiComponent'):
    name=comp.get('LocalName')
    if name in ['&ASCQ1','&ASCQ2','&ASCQ3','&ASCQ6','&ASCQ7']:
        print(name)
        for e in comp.iter():
            for key,val in e.attrib.items():
                if any(x in val.lower() for x in ['model','q1','q2','q3','q4','q5','npn','pnp','qin','qoc']): print(e.tag,key,val[:700])
(here/'q1.xml').write_text(re.search(r'<CiComponent Class="CiComponent" LocalName="&amp;ASCQ1".*?</CiComponent>',t,re.S)[0])
nodes={}
for n in root.iter('CiNode'):
    for i in n.findall('Ports/Item'): nodes[i.get('CiID')]=n.get('LocalName')
for comp in root.iter('CiComponent'):
    if comp.get('Circuit')=='601050728':
        print('CONNECTION',comp.get('LocalName'),[(p.get('CiID'),nodes.get(p.get('CiID'))) for p in comp.findall('Ports/Item')])
for n in root.iter('CiNode'):
    if n.get('Circuit')=='601050728':print(ET.tostring(n,encoding='unicode')[:250])
