import pythoncom
from pathlib import Path
lib=pythoncom.LoadTypeLib(r'D:\multimism\Circuit Design Suite 14.3\MSInterface.dll')
lines=[]
for i in range(lib.GetTypeInfoCount()):
    ti=lib.GetTypeInfo(i); attr=ti.GetTypeAttr(); name=lib.GetDocumentation(i)
    lines.append(repr(name))
    for j in range(attr.cFuncs):
        fd=ti.GetFuncDesc(j)
        lines.append('FUNC '+repr(ti.GetNames(fd.memid))+' '+repr(ti.GetDocumentation(fd.memid))+' '+repr(fd))
    for j in range(attr.cVars):
        vd=ti.GetVarDesc(j)
        lines.append('VAR '+repr(ti.GetNames(vd.memid))+' '+repr(vd))
Path('api_probe/typeinfo.txt').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(lines))
