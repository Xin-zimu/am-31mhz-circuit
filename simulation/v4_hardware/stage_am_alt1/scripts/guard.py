# -*- coding: utf-8 -*-
"""Name-collision guard: compare only the ADDED lines against the oscillator."""
def used_names(net_text):
    names=set()
    for ln in net_text.splitlines():
        s=ln.strip()
        if not s or s.startswith(("*",".","+")): continue
        names.add(s.split()[0].lower())
    return names

def added_lines(osc, full):
    """Return element lines present in full but not in osc."""
    return [l for l in full.splitlines() if l.strip() and not l.strip().startswith(("*",".","+"))][len([l for l in osc.splitlines() if l.strip() and not l.strip().startswith(("*",".","+"))]):]

def check(osc, stage_text):
    u=used_names(osc); bad=[]
    for ln in stage_text.splitlines():
        s=ln.strip()
        if not s or s.startswith(("*",".","+")): continue
        t=s.split()[0].lower()
        if t in u: bad.append(t)
    return bad
