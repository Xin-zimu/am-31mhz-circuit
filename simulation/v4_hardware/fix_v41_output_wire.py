from pathlib import Path
import re,copy,uuid,xml.etree.ElementTree as E
h=Path('simulation/v4_hardware');p=h/'v4_1_fixed.xml';s=p.read_text();r=E.fromstring(s);pm={c:p for p in r.iter() for c in p}
def ser(e):return E.tostring(e,encoding='unicode').replace('&#10;','\n').replace('&#13;','\r')
def repl_item(kind,id,e):
 global s
 key='CiID' if kind.startswith('Ci') and not kind.startswith('CIIT') else 'ID'
 pat=rf'<Item {key}="{id}" Class="{kind}">\s*<{kind}\b.*?</{kind}>\s*</Item>'
 s,n=re.subn(pat,lambda _:ser(e),s,count=1,flags=re.S);assert n==1,(kind,id)
n=next(e for e in r.iter('CiNode') if e.get('LocalName')=='&ASCBBO');ni=pm[n];nid=ni.get('CiID')
comp=next(e for e in r.iter('CiComponent') if e.get('LocalName')=='&ASCA1')
sym=next(i.find('CIITSymbolComp') for i in r.iter('Item') if i.get('ID')==comp.get('SymCompID'))
pin=next(e for e in sym.iter('CIITPinSymbolComp') if e.get('PinName')=='&ASC7');portid=pin.get('PortID');con=pin.find('.//CIITPinConnectorComp');conid=pm[con].get('ID')
portitem=next(i for i in r.iter('Item') if i.get('CiID')==portid and i.find('CiPort') is not None)
portitem.find('CiPort/Nodes').clear();E.SubElement(portitem.find('CiPort/Nodes'),'Item',CiID=nid);repl_item('CiPort',portid,portitem)
E.SubElement(n.find('Ports'),'Item',CiID=portid);repl_item('CiNode',nid,ni)
newpinid='900000001';newlinkid='900000002';assert f'ID="{newpinid}"' not in s
E.SubElement(con.find('ConnectList'),'Item',ID=newpinid,Class='CODPinComp');repl_item('CIITSymbolComp',comp.get('SymCompID'),pm[sym])
wire=next(e for e in r.iter('CIITLinkComp') if e.get('Node')==nid);oldpin=next(e for e in r.iter('CODPinComp') if pm[e].get('ID')==wire.get('Connect1'));np=copy.deepcopy(pm[oldpin]);np.set('ID',newpinid);np[0].set('CenterX','1152');np[0].set('CenterY','1143');np[0].find('ConnectList').clear();E.SubElement(np[0].find('ConnectList'),'Item',ID=conid,Class='CIITPinConnectorComp')
nw=copy.deepcopy(pm[wire]);nw.set('ID',newlinkid);nw[0].set('Connect1',newpinid);nw[0].set('Connect2',wire.get('Connect2'));nw[0].find('Points').clear()
for x,y in [(1152,1143),(1206,1143),(1206,1296),(747,1296),(747,1143)]:E.SubElement(nw[0].find('Points'),'Item',X=str(x),Y=str(y))
mod=nw[0].find('ElectricalObject/ModifierInfo');mod.clear();el=E.SubElement(mod,'Element',NetModifier='&ASCNI_EWB_NET_AUTONAMED');E.SubElement(el,'Item',Value='',Guid='{'+str(uuid.uuid4()).upper()+'}')
anchor='<Item ID="'+pm[wire].get('ID')+'" Class="CIITLinkComp">';assert anchor in s;s=s.replace(anchor,ser(np)+'\n'+ser(nw)+'\n'+anchor,1)
p.write_text(s,encoding='ascii');print('Added electrical and graphical OPA197 output feedback wire',portid,nid)
