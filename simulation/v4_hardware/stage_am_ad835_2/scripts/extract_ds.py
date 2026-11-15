import fitz
doc = fitz.open(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835\sources\ad835.pdf")
out = []
for i, p in enumerate(doc):
    out.append("\n\n========== PAGE " + str(i+1) + " ==========\n")
    out.append(p.get_text())
txt = "".join(out)
open(r"D:\实验报告文件夹\电路2\simulation\v4_hardware\stage_am_ad835_2\sources\ad835_datasheet_text.txt","w",encoding="utf-8").write(txt)
print("pages", len(doc), "chars", len(txt))
