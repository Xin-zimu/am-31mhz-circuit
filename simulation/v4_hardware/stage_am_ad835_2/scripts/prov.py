# -*- coding: utf-8 -*-
import os, sys, hashlib, json, datetime
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
M=os.path.join(STAGE,"models","third_party_GLuisF")
BASE="https://github.com/GLuisF/LTspice/tree/master/examples/LtSpicePlus/Multiplicadores/ad835"
RAW="https://raw.githubusercontent.com/GLuisF/LTspice/master/examples/LtSpicePlus/Multiplicadores/ad835/"
rows=[]
for f in sorted(os.listdir(M)):
    p=os.path.join(M,f)
    b=open(p,"rb").read()
    rows.append({"file":f,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),
                 "url":RAW+f,"repo_page":BASE,
                 "retrieved_utc":"2026-11-14T17:33:00Z","retrieved_local":"2026-11-15T01:33:00+08:00"})
for r in rows:
    print("%-24s %7d  %s"%(r["file"],r["bytes"],r["sha256"]))
json.dump({"retrieved":"2026-11-15T01:33:00+08:00","source_repo":BASE,"files":rows},
          open(os.path.join(STAGE,"sources","provenance.json"),"w"),indent=1)
with open(os.path.join(STAGE,"sources","SHA256SUMS.txt"),"w",encoding="utf-8") as fh:
    for r in rows:
        fh.write("%s  models/third_party_GLuisF/%s\n"%(r["sha256"],r["file"]))
print("\nwrote provenance.json + SHA256SUMS.txt")
