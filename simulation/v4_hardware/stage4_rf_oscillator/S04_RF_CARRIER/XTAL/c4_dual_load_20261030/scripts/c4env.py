# -*- coding: utf-8 -*-
"""Make c3lib importable from the C4 workspace without copying it."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # .../c4_dual_load_20261030/scripts
ROOT4 = os.path.dirname(HERE)                              # .../c4_dual_load_20261030
XTAL = os.path.dirname(ROOT4)                              # .../XTAL
C3_SCRIPTS = os.path.join(XTAL, "c3_numeric_20261030", "scripts")
if C3_SCRIPTS not in sys.path:
    sys.path.insert(0, C3_SCRIPTS)
import c3lib as L   # noqa: E402

if not os.path.isdir(C3_SCRIPTS):
    raise RuntimeError("c3 scripts not found at " + C3_SCRIPTS)

# C4 keeps its own netlist/result directories
L.NETDIR = os.path.join(ROOT4, "netlists")
L.RESDIR = os.path.join(ROOT4, "results")
for _d in (L.NETDIR, L.RESDIR):
    os.makedirs(_d, exist_ok=True)
