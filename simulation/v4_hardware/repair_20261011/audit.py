from pathlib import Path
import xml.etree.ElementTree as E
import re
H=Path(__file__).resolve().parent
s=(H/'original.xml').read_text('ascii'); r=E.fromstring(s)
items={i.get('CiID'):i for i in r.iter('Item') if i.get('CiID') and len(i)}
for c in r.iter('CiComponent'):
    name=c.get('LocalName','').replace('&ASC','')
    if name not in ['A1','R4','R5','R6','R7','C1','C3','C4','V5','V6']:continue
    print('\nCOMP',name,c.attrib)
    for p in c.findall('Ports/Item'):
        po=items[p.get('CiID')].find('CiPort')
        print('PORT',po.get('LocalName'),[items[n.get('CiID')].find('CiNode').get('LocalName') if n.get('CiID') in items else n.attrib for n in po.findall('Nodes/Item')])
    for t in c.iter('CiaSpiceTmpltExprt'):print('TEMPLATE',repr(t.get('String','')[:160]))
    for t in c.iter('CiaParamList'):print('PARAMS',[(i.get('Name'),i.get('Value')) for i in t.findall('parameters/Item')][:22])
