from pathlib import Path
import re,xml.etree.ElementTree as E
H=Path(__file__).resolve().parent
s=(H/'wire_fixed.xml').read_bytes().decode('ascii')
for name,value in [('C3','-4.1'),('C4','0.43'),('C1','4.5')]:
 pat=r'<CiComponent Class="CiComponent" LocalName="&amp;ASC'+name+r'".*?</CiComponent>'
 m=re.search(pat,s,re.S);assert m
 block=m[0];start=block.index('<parameters>');end=block.index('</parameters>',start)
 values=list(re.finditer(r'<Item Value="([^"]*)"\s*/>',block[start:end]));assert len(values)>5
 for idx,new in [(5,value),(4,'1')]:
  v=values[idx];a=start+v.start(1);b=start+v.end(1)
  block=block[:a]+'&amp;ASC'+new+block[b:]
 s=s[:m.start()]+block+s[m.end():]
start=s.index('TRAN:list{');end=s.index('IC:string{',start)
icend=s.index('}',end)
s=s[:end]+'IC:string{user_ic'+s[icend:]
E.fromstring(s)
(H/'final.xml').write_bytes(s.encode('ascii'))
print('final setup: user-defined IC, 200 us, max step 2 ns; original OPAx197 model')
