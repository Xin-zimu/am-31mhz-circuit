import re
p=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1\scripts\run_mod.py"
s=open(p,encoding="utf-8").read()
s=s.replace('"v(mcol)","v(memit)","v(mbase)","v(mode)","v(modb)"','"v(m9col)","v(m9emit)","v(m9base)","v(m9e)","v(m9b)"')
open(p,"w",encoding="utf-8").write(s); print("patched")
