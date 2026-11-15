# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run, log
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
d=os.path.join(STAGE,"bench")

def test(tag, subckt_text):
    subp=os.path.join(d,"t_%s.sub"%tag)
    open(subp,"w",encoding="utf-8").write(subckt_text)
    p=os.path.join(d,"t_%s.net"%tag)
    open(p,"w",encoding="utf-8").write(
        "* title line (LTspice ignores line 1)\n" +
        ".include t_%s.sub\n"%tag +
        "V1 X1 0 0\nV2 VP 0 5\nV3 0 VN 5\nV4 Y1 0 1\nV5 Z 0 0\n"
        "XU X1 0 Y1 0 Z W VP VN AD835_BEHAV\nRL W 0 150\n.op\n.end\n")
    r=run(p); print("==",tag,"rc",r.returncode)
    if r.returncode: print(log(p)[-400:])

test("minimal", ".SUBCKT AD835_BEHAV X1 X2 Y1 Y2 Z W VPOS VNEG\nR1 X1 X2 100k\n.ENDS\n")
test("withsemi", ".SUBCKT AD835_BEHAV X1 X2 Y1 Y2 Z W VPOS VNEG\n.param Slew=1E9 ;slew rate\nB1 9 0 V=(V(X1)-V(X2))\nR5 9 W 10\n.ENDS\n")
test("withlib", ".SUBCKT AD835_BEHAV X1 X2 Y1 Y2 Z W VPOS VNEG\nB1 9 0 V=(V(X1)-V(X2))\nR5 9 W 10\n.lib C:\\Users\\86139\\AppData\\Local\\LTspice\\lib\\cmp\\standard.dio\n.ENDS\n")
