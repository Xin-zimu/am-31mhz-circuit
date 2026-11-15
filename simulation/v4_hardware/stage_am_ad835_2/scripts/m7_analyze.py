# -*- coding: utf-8 -*-
"""Module 7: X/Y diff-input network analysis of Model A (why X2 is unusable)."""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
print("""
MODEL A  ad835.sub  -- X/Y differential input network
=====================================================
Declared in the file:
  R12 1 2 100k      <- differential 100k between X1 and X2
  R1  1 5 500k      <- X1 to node 5 (VN)
  R2  2 5 500k      <- X2 to node 5 (VN)
  R34 3 4 100k      <- differential 100k between Y1 and Y2
  R3  3 5 500k      <- Y1 to VN
  R4  4 5 500k      <- Y2 to VN
  C1..C4 2p to ground each

The common-mode bias is therefore a divider from **VN(-5V)**, not from ground:
  R1(500k) from X1 to -5 V and R12(100k) to X2 (which itself has 500k to -5 V)
  With X2 externally grounded the DC path is:
      X1 --500k--> -5V      (parallel with)   X1 --100k--> X2 --500k--> -5V
  => V(X1) = -5 * (100k+500k) / (500k + 100k + 500k)  ... see numeric below
""")
R1=500e3; R12=100e3; R2=500e3
# X2 hard-grounded by source. Node X1 sees: R1->-5, R12->X2(0V through grounded source)
# so V(X1) = -5 * (R12||? ) ... solve: (Vx1-(-5))/R1 + (Vx1-0)/R12 = 0
G=1/R1+1/R12
Vx1=(5/R1)/G*1.0
print("Predicted V(X1) with only R1/R12 (X2 grounded, R2 shorted by source): %.4f V"%( (5/R1)/G ))
print("Predicted V(X2) forced by the grounded source: 0 V ; current drawn from source = V(X2)/R2 = %.1f uA"%(0))
# actual: X2 source also sinks through R12
print("""
So model A pulls both X inputs toward -5 V through 500k, and the differential
100k sits between them. Consequences measured in the bench:
  * X1 sits at a large negative DC value unless driven by a low impedance
  * the 100k differential resistor loads ANY differential source by 100k
  * an X source that is ground-referenced sees 500k to -5 V, i.e. it must sink
    ~10 uA; that is exactly the "10 uA bias current" the header advertises
""")
print("""
MODEL B  AD835_Behav_Model.asc
==============================
  R1 100k  X1-X2      (differential, matches datasheet 100k)
  R3 100k  Y1-Y2      (differential)
  R6 60k   Z-0        (SINGLE-ENDED to ground; datasheet says 60k DIFFERENTIAL)
  C1..C4 2p, C6 2p
  I1..I5 current sources INJECT into X2, X1, Y2, Y1, Z from VNEG
      Ib1 = 10u + Ioff/2 = 11 uA   (X1, Y1)
      Ib2 = 10u - Ioff/2 =  9 uA   (X2, Y2)
      Ibz = 60 uA                  (Z)
""")
