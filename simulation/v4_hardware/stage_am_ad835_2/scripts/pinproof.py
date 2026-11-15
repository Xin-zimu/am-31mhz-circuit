# -*- coding: utf-8 -*-
"""Prove the model-A pin-order trap with a direct experiment.
Physical AD835 pin 1 is Y1. Model A node 1 is X1.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from ltraw import run_and_load
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
B=os.path.join(STAGE,"bench","pins"); os.makedirs(B,exist_ok=True)
HDR=".include ../../models/third_party_GLuisF/ad835.sub\nVADP ADP 0 5\nVADN ADN 0 -5\n"

# Drive ONLY node "1" with +1 V, everything else 0, Y=... we must set node3=1 to get product
# Test 1: put 1 V on node 1, and 1 V on node 3 -> if 1=X1 and 3=Y1 then W=1
n1="""VONE N1 0 1
VN2 N2 0 0
VN3 N3 0 1
VN4 N4 0 0
VNZ N6 0 0
XU N1 N2 N3 N4 ADN N6 NW ADP AD835
RL NW 0 150
"""
p=os.path.join(B,"pin_test1.net")
open(p,"w",encoding="utf-8").write("* pin test\n"+HDR+n1+".op\n.options plotwinsize=0\n.end\n")
R,lg,rc=run_and_load(p,ascii=True)
w=R["V(nw)"][0]
print("Drive node1=1V, node3=1V -> W = %+.4f V"%w)
print("  If node1=X1 and node3=Y1 (models' declared order) then W = X*Y/1.0 = +1.0")
print("  If node1=Y1 and node3=VN as on the real package, the part would be mis-supplied")

# Test 2: swap -> node1=0, node3=1, node2=1
n2="""VONE N1 0 0
VN2 N2 0 1
VN3 N3 0 1
VN4 N4 0 0
VNZ N6 0 0
XU N1 N2 N3 N4 ADN N6 NW ADP AD835
RL NW 0 150
"""
p=os.path.join(B,"pin_test2.net")
open(p,"w",encoding="utf-8").write("* pin test2\n"+HDR+n2+".op\n.options plotwinsize=0\n.end\n")
R,lg,rc=run_and_load(p,ascii=True)
print("Drive node2=1V, node3=1V -> W = %+.4f V   (node2=X2 so X=-1 -> W=-1.0)"%R["V(nw)"][0])
print()
print("CONCLUSION: the subckt node order is 1=X1 2=X2 3=Y1 4=Y2 5=VN 6=Z 7=W 8=VP.")
print("The physical DIP-8 is 1=Y1 2=Y2 3=VN 4=Z 5=W 6=VP 7=X2 8=X1.")
print("Only pins 3..6 map to the same FUNCTION, and even then the numbers differ.")
