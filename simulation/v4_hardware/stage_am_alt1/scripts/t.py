import os, sys, subprocess
sys.stdout.reconfigure(encoding="utf-8")
NG=r"D:\ms_xsp\s04_crosscheck_20261017\Spice64\bin\ngspice_con.exe"
ST=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1"
B=os.path.join(ST,"bench","M_6800_470_100_470")
p=os.path.join(B,"t.cir")
src=open(os.path.join(B,"M_6800_470_100_470.cir"),encoding="latin-1").read()
src=src.replace("tran 0.5n 0.90m 0.75m 0.5n uic","tran 0.5n 0.90m 0 0.5n uic")
open(p,"w",encoding="latin-1").write(src.replace("write M_6800_470_100_470.raw","write t.raw"))
r=subprocess.run([NG,"-b","t.cir"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=900,cwd=B)
print("rc",r.returncode)
print(r.stdout[-1200:])
print("ERR:",r.stderr[-600:])
