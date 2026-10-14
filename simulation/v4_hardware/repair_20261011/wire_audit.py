exec(open(__file__.replace('wire_audit.py','audit.py'),encoding='utf8').read().split('for c in r.iter')[0])
pm={c:p for p in r.iter() for c in p}
c=next(c for c in r.iter('CiComponent') if c.get('LocalName')=='&ASCA1')
sy=next(i.find('CIITSymbolComp') for i in r.iter('Item') if i.get('ID')==c.get('SymCompID'))
for p in sy.iter('CIITPinSymbolComp'):
 if p.get('PinName')=='&ASC7': print('OUT PIN',E.tostring(p,encoding='unicode'))
for l in r.iter('CIITLinkComp'):
 if l.get('Node')==next(i.get('CiID') for i in r.iter('Item') if i.find('CiNode') is not None and i.find('CiNode').get('LocalName')=='&ASCBBO'):
  print('ADDED WIRE',E.tostring(l,encoding='unicode'))
  for k in ['Connect1','Connect2']:
   for i in r.iter('Item'):
    if i.get('ID')==l.get(k):print(k,E.tostring(i,encoding='unicode')[:3000])
for i in r.iter('Item'):
 if i.get('ID')=='196770760' and len(i):print('OUTPUT CONNECTED PIN',E.tostring(i,encoding='unicode'))
