# -*- coding: utf-8 -*-
"""Inspect the exact bytes around the Values: block."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
p=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_alt1\bench\ng\c4.raw"
lines=open(p,encoding="latin-1").read().splitlines()
i=[k for k,l in enumerate(lines) if l.startswith("Values:")][0]
for k in range(i, i+10):
    print(k, repr(lines[k]))
