"""Write clean metrics templates for the three _cx5 detuning corners.

These kept getting corrupted because earlier repair scripts rewrote the
assumptions block in place while treating it as SI.  The block is written ONCE,
in reporting units (pF for capacitance, boolean for retune), and nothing else in
this stage is allowed to edit it.
"""
import json

for tag in ('472', '392', '332'):
    name = 'h90_%s_cx5' % tag
    stub = dict(
        name=name,
        part='1812CS-%s' % tag,
        length_cm=90,
        step_ns=0.25,
        assumptions=dict(
            contact_ohm=0.2,
            cbase_pF=0.5,
            cant_scale=1.0,
            coil_loss_scale=1.0,
            coil_L_scale=1.0,
            coil_extra_C_pF=0.5,     # pF, reporting units
            retune=False,            # boolean: do NOT absorb the stray by retuning
            trim_tand=0.0025,
        ),
    )
    json.dump(stub, open('joint/%s_metrics.json' % name, 'w', encoding='utf-8'),
              indent=2, ensure_ascii=False)
    print('seeded', name)
