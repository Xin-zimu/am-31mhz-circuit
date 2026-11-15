# -*- coding: utf-8 -*-
"""Write clean stage netlists without the AC test source."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import am022_lib as L

DESC = {
    "A": "2N3904 common emitter, unbypassed RE=100",
    "B": "2N3904 common base, base AC-grounded",
    "C": "2N3904 CE followed by emitter follower",
    "D": "2N3904 cascode: CE Q1 + CB Q2",
    "E": "2N3904 emitter-follower input + CE gain",
}

for c in "ABCDE":
    body = L.circuit(c, 10000.0).split("VCC vcc 0 DC 5\n", 1)[1]
    text = f"""* AM-02.2 candidate {c}: {DESC[c]}
* Input node: {L.input_node(c)} (connect from AM-01 output after its 100 pF COUT)
* Default load: 10 kOhm || 10 pF; change RL/CL for the 2 kOhm interface.
VCC vcc 0 DC 5
{body}{L.MODEL}
.options method=trap maxord=2 reltol=1e-4 trtol=7 temp=27 tnom=27
.op
.end
"""
    (L.NETLISTS / f"stage_{c}.cir").write_text(text, encoding="utf-8", newline="\n")
print("stage netlists written")
