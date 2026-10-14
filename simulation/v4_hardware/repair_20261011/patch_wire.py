from pathlib import Path
import re,xml.etree.ElementTree as E
H=Path(__file__).resolve().parent
s=(H/'original.xml').read_bytes().decode('ascii')
# Each wire requires its own endpoint object; junction ConnectList links endpoints.
# The previous repair illegally reused the endpoint of a different wire.
pat=r'<Item ID="195746328" Class="CODPinComp">\s*<CODPinComp\b.*?</CODPinComp>\s*</Item>'
m=re.search(pat,s,re.S);assert m
endpoint=m[0].replace('ID="195746328"','ID="900100001"',1)
wirepat=r'(<Item ID="196844840" Class="CIITLinkComp">\s*<CIITLinkComp\b[^>]*Connect2=")195746328(")'
s,n=re.subn(wirepat,r'\g<1>900100001\2',s);assert n==1
s=s[:m.start()]+endpoint+'\n'+s[m.start():]
pat=r'(<Item ID="195937496" Class="CODPinComp">\s*<CODPinComp\b.*?<ConnectList>)(.*?)(</ConnectList>)'
s,n=re.subn(pat,lambda m:m[1]+m[2]+'<Item ID="900100001" Class="CODPinComp"/>\n'+m[3],s,count=1,flags=re.S);assert n==1
# The output endpoint was incorrectly inserted as a visible standalone object.
# Wire endpoints are serialized in ReferencedComponents; only junctions belong
# in Objects. Preserve its ID and connector, move the definition into that list.
pat=r'<Item ID="196770760" Class="CODPinComp">\s*<CODPinComp\b.*?</CODPinComp>\s*</Item>'
m=re.search(pat,s,re.S);assert m
outpin=m[0];s=s[:m.start()]+s[m.end():]
pat=r'(<ReferencedComponents>.*?)(<Item ID="196770760" Class="CODPinComp"\s*/>)'
s,n=re.subn(pat,lambda m:m[1]+outpin,s,count=1,flags=re.S);assert n==1
E.fromstring(s)
(H/'wire_fixed.xml').write_bytes(s.encode('ascii'))
print('patched endpoint sharing; model and simulation settings unchanged')
