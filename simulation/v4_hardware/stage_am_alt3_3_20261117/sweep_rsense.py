"""A/B/C sweep on the 10 ohm measurement shunt, 90 cm, frozen driver.

A: keep 10 ohm (baseline, already exists as h90_nom)
B: reduce to 5 / 2 / 1 ohm
C: final-operation case with 0.01 ohm (electrically 'removed')

Every case is re-tuned and run through the full transistor transient: reducing the
shunt changes the load the driver sees, so the current is NOT assumed to rise.
"""
import joint_sim as s

CASES = [
    ('rs5',  5.0),
    ('rs2',  2.0),
    ('rs1',  1.0),
    ('rs01', 0.01),
]

if __name__ == '__main__':
    for label, rs in CASES:
        s.RSENSE = rs
        s.execute((.9, label, .25, 1, 1, 0, .2, .5e-12, 1, 1))
