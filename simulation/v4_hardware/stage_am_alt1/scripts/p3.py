import re
p=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1\scripts\emod.py"
s=open(p,encoding="utf-8").read()
s=s.replace("bad=check(OSC,txt)","bad=check(OSC,stage_txt_for_check)")
s=s.replace("def go(tag,txt,tstop","def go(tag,txt,tstop")
# pass the stage text separately
s=s.replace("def go(tag,txt,tstop=\"0.90m\",tstart=\"0.75m\",tmax=\"0.5n\",to=900):",
            "def go(tag,txt,stage_txt_for_check=\"\",tstop=\"0.90m\",tstart=\"0.75m\",tmax=\"0.5n\",to=900):")
s=s.replace('d=go(tag,net(tag,stage(rm,rb,re,rc)))',
            'st=stage(rm,rb,re,rc); d=go(tag,net(tag,st),st)')
open(p,"w",encoding="utf-8").write(s); print("patched")
