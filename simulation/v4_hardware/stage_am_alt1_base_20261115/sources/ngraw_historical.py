# -*- coding: utf-8 -*-
"""ngspice ASCII raw reader: real and complex (AC) data."""
import numpy as np
def load_ngraw(path):
    lines=open(path,encoding="latin-1").read().splitlines()
    nvar=npts=None; names=[]; i=0; cplx=False
    while i<len(lines):
        l=lines[i]
        if l.startswith("Flags:") and "complex" in l.lower(): cplx=True
        elif l.startswith("No. Variables:"): nvar=int(l.split(":")[1])
        elif l.startswith("No. Points:"): npts=int(l.split(":")[1])
        elif l.startswith("Variables:"):
            for k in range(nvar):
                p=[q for q in lines[i+1+k].split("\t") if q.strip()]
                names.append(p[1] if len(p)>=2 else p[0])
            i+=nvar
        elif l.startswith("Values:"):
            i+=1; break
        i+=1
    def cv(s):
        s=s.strip()
        if "," in s:
            a,b=s.split(","); return complex(float(a),float(b))
        return float(s)
    rows=[]; cur=[]
    for l in lines[i:]:
        if not l.strip(): continue
        if l.startswith("\t"):
            cur.append(cv(l))
        else:
            p=[q for q in l.split("\t") if q.strip()]
            if len(p)>=2:
                if len(cur)>=nvar: rows.append(cur[:nvar])
                cur=[cv(p[1])]
        if len(cur)>=nvar:
            rows.append(cur[:nvar]); cur=[]
    if len(cur)>=nvar: rows.append(cur[:nvar])
    arr=np.array(rows[:npts])
    return {n:arr[:,k].copy() for k,n in enumerate(names)}
