"""Write metrics templates (assumptions only) for cases whose .raw exists but
whose _metrics.json was never produced, so reanalyse_all.py can rebuild them."""
import json
import os

import datasheet_corners as dsc
import engine as e

TEMPLATES = {}
for tag, part in [('472', '1812CS-472'), ('392', '1812CS-392'), ('332', '1812CS-332')]:
    TEMPLATES['h90_%s_Qds' % tag] = dict(part=part, length_cm=90,
                                         coil_loss_scale=dsc.loss_scale_for_q50(part))
    TEMPLATES['h90_%s_srf' % tag] = dict(part=part, length_cm=90,
                                         coil_extra_C_pF=dsc.extra_C_for_srf(part) * 1e12)

for name, kw in TEMPLATES.items():
    path = 'joint/%s_metrics.json' % name
    if os.path.exists(path):
        print('exists, skipped', name)
        continue
    job = dict(name=name, part=kw['part'], length_cm=kw['length_cm'], step_ns=0.25)
    for k, v in kw.items():
        job[k] = v
    # replicate the reporting block engine writes, without analysing
    job.setdefault('contact', e.CONTACT)
    job.setdefault('cbase', e.CBASE)
    job.setdefault('cant_scale', 1.0)
    job.setdefault('coil_loss_scale', 1.0)
    job.setdefault('coil_L_scale', 1.0)
    job.setdefault('coil_extra_C_pF', 0.0)
    job.setdefault('trim_tand', e.TRIM_TAND)
    job.setdefault('retune', True)
    stub = dict(name=name, part=kw['part'], length_cm=kw['length_cm'], step_ns=0.25,
                assumptions=dict(contact_ohm=job['contact'],
                                 cbase_pF=job['cbase'] * 1e12,
                                 cant_scale=job['cant_scale'],
                                 coil_loss_scale=job['coil_loss_scale'],
                                 coil_L_scale=job['coil_L_scale'],
                                 coil_extra_C_pF=job['coil_extra_C_pF'] * 1e12,
                                 retune=job['retune'],
                                 trim_tand=job['trim_tand']))
    json.dump(stub, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('seeded', name)
