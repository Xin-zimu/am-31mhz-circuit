# -*- coding: utf-8 -*-
"""Generate the machine-readable datasheet conformance table."""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
RES=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\results"
rows = [
 # param, datasheet, modelA, modelB, verdictA, verdictB, note
 ("Transfer function W=(X1-X2)(Y1-Y2)/U+Z","eq.(1)","same eq., U=1.000","same eq., U=1.000","不一致","不一致","both hard-wire U=1.0 V; datasheet U=1.05 V nom."),
 ("Scale factor U","1.05 V nom (1.00 by divider)","1.000 V","1.000 V","不一致","不一致","31 MHz envelope error follows directly"),
 ("X/Y differential R","100 k","100 k","100 k","一致","一致",""),
 ("X/Y single-sided C","2 pF","2 pF","2 pF","一致","一致",""),
 ("X/Y diff voltage range","+-1 V","unlimited in model (only output clamps)","clipped at +-1.387 V","不一致","近似","datasheet clipping 1.21 typ / 1.40 max"),
 ("X/Y common-mode range","-2.5 .. +3 V","not modelled (inputs pulled to VN via 500k)","not modelled (current sources to VNEG)","未实现","未实现",""),
 ("X/Y bias current","10 uA typ / 20 max / 27 over temp","10.0 uA fixed both pins","11.0 / 9.0 uA (Ioff=2uA)","近似","近似","A has no offset current; B adds Ios=2uA"),
 ("X/Y offset bias current","2 uA","0 (identical both pins)","2 uA","未实现","一致",""),
 ("X feedthrough","-46 dB","not modelled (-inf)","-46.00 dB (forced)","未实现","一致","B sets it as a fixed parameter, not a physical path"),
 ("Y feedthrough","-60 dB","not modelled (-inf)","-60.00 dB (forced)","未实现","一致","ditto"),
 ("Z differential R","60 k","60 k but referenced to VN -> 9.09 k to ground","60 k to ground only","不一致","近似","A measured 9.09 k, B 7.32 k at V(Z)=0.5 V"),
 ("Z single-sided C","2 pF","2 pF","2 pF","一致","一致",""),
 ("Z bias current","50 uA typ (no max published)","50.0 uA","60 uA","近似","近似","B uses 60 uA, above the datasheet typ"),
 ("Z->W gain","0.990..0.995 (f<=10 MHz)","0.9993","1.0000 (0.99999 at DC)","不一致","不一致","both ~1.00, datasheet <=0.995"),
 ("-3 dB bandwidth","250 MHz typ / 150 min","250 MHz (single pole)","250 MHz (single pole)","近似","近似","see phase row - the pole shape is wrong"),
 ("Gain at 31 MHz","-0.180 dB (Fig.5 digitised)","-0.066 dB","-0.066 dB","不一致","不一致","models are 0.114 dB optimistic"),
 ("Phase at 31 MHz","-28.3 deg (Fig.5 digitised)","-7.05 deg","-7.16 deg","不一致","不一致","~21 deg optimistic - the key 31 MHz error"),
 ("Phase at 10 MHz","-11.4 deg","-2.29 deg","-2.33 deg","不一致","不一致",""),
 ("Phase at 100 MHz","-86.5 deg","-21.8 deg","-22.2 deg","不一致","不一致",""),
 ("-0.1 dB gain flatness freq","15 MHz","~24 MHz","~24 MHz","近似","近似",""),
 ("Slew rate","1000 V/us","1500 V/us (RC limited, no explicit SR)","1000 V/us (parameter)","近似","一致","A overshoots because 63.7 pF/10 ohm sets it"),
 ("Output swing","+-2.2 min / +-2.5 typ (RL=150)","+-2.998 (rail limited)","+-2.047 @150R","不一致","近似","B's 33.3R shunt sets the 150R value"),
 ("Output swing into 50 ohm","+-2.0 V min","+-2.994","+-1.501","不一致","不一致","B cannot reach +-2.0 V into 50 ohm"),
 ("Output swing into 25 ohm","drive loads as low as 25 ohm","+-2.988","+-1.071","不一致","不一致","B collapses"),
 ("Short-circuit current","75 mA","not limited (15 A measured)","74.8 mA","不一致","一致",""),
 ("Output offset Vos","+-25 mV typ / +-75 max","0.000 V","+25.0 mV","未实现","近似","A has no offset at all"),
 ("Quiescent supply current","16 mA typ / 25 max","16.667 / 16.757 mA","16.000 / 16.100 mA","一致","一致",""),
 ("Supply voltage","+-5 V nom, +-4.5..5.5","no supply dependence","no supply dependence","未实现","未实现",""),
 ("PSRR","0.5 %/V","not modelled","not modelled","未实现","未实现",""),
 ("CMRR","70 dB (<=100 kHz)","not modelled","not modelled","未实现","未实现",""),
 ("Nonlinearity","0.3/0.51 % FS","none (ideal multiply)","none (ideal multiply)","未实现","未实现",""),
 ("Harmonic distortion","-70 dB @10 MHz, -40 dB @50 MHz","not modelled","not modelled","未实现","未实现",""),
 ("Noise 50 nV/rtHz","50 nV/rtHz","noiseless","noiseless","未实现","未实现",""),
 ("Temperature drift","specified over -40..+85 C","none","none","未实现","未实现",""),
 ("Package / pin numbers","1 Y1 2 Y2 3 VN 4 Z 5 W 6 VP 7 X2 8 X1","1 X1 2 X2 3 Y1 4 Y2 5 VN 6 Z 7 W 8 VP","adapter forced to datasheet order","不一致","一致","A's node order is NOT the package order"),
]
out=[{"parameter":r[0],"datasheet":r[1],"modelA":r[2],"modelB":r[3],
      "verdictA":r[4],"verdictB":r[5],"note":r[6]} for r in rows]
json.dump(out,open(os.path.join(RES,"conformance.json"),"w"),ensure_ascii=False,indent=1)
print("rows:",len(out))
from collections import Counter
print("A verdicts:",Counter(r["verdictA"] for r in out))
print("B verdicts:",Counter(r["verdictB"] for r in out))
