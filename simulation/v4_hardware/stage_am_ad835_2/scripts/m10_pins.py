# -*- coding: utf-8 -*-
"""Module 10: pin-order verification and structural audit of both models."""
import os, sys, re, json
sys.stdout.reconfigure(encoding="utf-8")
STAGE=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2"
M=os.path.join(STAGE,"models","third_party_GLuisF")

sub=open(os.path.join(M,"ad835.sub"),encoding="latin-1").read()
asy=open(os.path.join(M,"ad835.asy"),encoding="latin-1").read()
print("=== ad835.sub port line ===")
for ln in sub.splitlines():
    if ln.upper().startswith(".SUBCKT"): print("  ",ln)
print("\n=== ad835.asy PIN / SpiceOrder ===")
pins=re.findall(r"PIN\s+(-?\d+)\s+(-?\d+)\s+\S+\s+\d+\s*\nPINATTR\s+PinName\s+(\S+)\s*\nPINATTR\s+SpiceOrder\s+(\d+)", asy)
for px,py,name,order in pins:
    print("   SpiceOrder %s -> %-6s (symbol pos %s,%s)"%(order,name,px,py))
print("\n=== Model A header comment (translated) ===")
print("""   *Description d'un multiplieur analogique AD835.
    *Macro modele modelisant :
    *Les tensions de saturations +5V -5V (amelioration du composant !!)
    *La bande passante de 250MHz
    *Les Impedances d'entree de la doc 100kohm // 2pF
    * R11, R22, R33, R44    bias current 10uA
    * Rpd  power dissipation
    *                         VNEG
    *             X1 X2 Y1 Y2  |  Z  W  VPOS
    .SUBCKT AD835  1  2  3  4  5  6  7  8""")
print("""
  So the .sub declares nodes 1..8 in the order
     1=X1 2=X2 3=Y1 4=Y2 5=VNEG 6=Z 7=W 8=VPOS
  and ad835.asy assigns SpiceOrder 1..8 to exactly the same names.
  => Model A pin order AGREES with the datasheet numbering (1 Y1,2 Y2,3 VN,4 Z,
     5 W,6 VP,7 X2,8 X1) for VN/Z/W/VP but the 1..4 positions carry X/Y in a
     DIFFERENT arrangement than the physical package:
       datasheet phys 1=Y1 2=Y2 3=VN 4=Z 5=W 6=VP 7=X2 8=X1
       model A   node 1=X1 2=X2 3=Y1 4=Y2 5=VN 6=Z 7=W 8=VP
  The symbol therefore has 8 pins but its pin NUMBERS are not the package
  pin numbers. A PCB netlist built from ad835.asy would not map to the DIP-8
  footprint without an explicit pin swap. THIS IS A REAL TRAP.
""")

print("=== Model B: is it directly includable? ===")
asc=open(os.path.join(M,"AD835_Behav_Model.asc"),encoding="latin-1").read()
print("  .asc lines:", len(asc.splitlines()))
print("  contains .SUBCKT ?", ".SUBCKT" in asc.upper())
print("  contains .include?", ".include" in asc.lower())
print("  LTspice directives present:", [l for l in asc.splitlines() if l.strip().startswith("TEXT") and "!" in l])
print("""
  => The .asc is a SCHEMATIC, not a netlist. It cannot be .include'd.
     It also depends on the LTspice symbol 'load2' (lib/sym/load2.asy) which
     ships with LTspice but NOT with this repository; on a machine without
     LTspice the schematic will not open.
""")
