# -*- coding: utf-8 -*-
p=r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\bench\chk.raw"
raw=open(p,'rb').read()
i=raw.find(b"Values:")
print(repr(raw[i:i+260]))
