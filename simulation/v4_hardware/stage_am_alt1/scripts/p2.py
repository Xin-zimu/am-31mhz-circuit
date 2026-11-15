import re
p=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1\scripts\emit2.py"
s=open(p,encoding="utf-8").read()
# ngspice lowercases node names in the raw file
s=s.replace('R["v(m9E)"]','R["v(m9e)"]')
open(p,"w",encoding="utf-8").write(s); print("patched")
