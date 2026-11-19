"""Run the per-part datasheet-floor and SRF-corrected corners.

The main matrix was generated before the per-part datasheet floors were solved, so
it carries a single generic "Qx" corner (1.2646, which is correct only for 472).
This script adds the correct per-part corners:
    h90_<tag>_Qds   loss scale solved so that Q(50 MHz) equals the datasheet minimum
    h90_<tag>_srf   extra shunt C that brings the model SRF down to the guaranteed minimum
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import datasheet_corners as dsc

HERE = Path(__file__).resolve().parent
TAGS = [('472', '1812CS-472'), ('392', '1812CS-392'), ('332', '1812CS-332')]


def jobs():
    out = []
    for tag, part in TAGS:
        out.append(dict(name='h90_%s_Qds' % tag, part=part, length_cm=90,
                        coil_loss_scale=dsc.loss_scale_for_q50(part)))
        out.append(dict(name='h90_%s_srf' % tag, part=part, length_cm=90,
                        coil_extra_C_pF=dsc.extra_C_for_srf(part)))   # SI farads
    return out


def _one(job):
    import engine as e
    t = time.time()
    try:
        o = e.run(job)
        return dict(ok=True, text=e.line(o), secs=time.time() - t)
    except Exception as exc:                      # noqa: BLE001
        return dict(ok=False, name=job['name'], secs=time.time() - t,
                    error='%s: %s' % (type(exc).__name__, exc))


def main():
    js = jobs()
    print('cases:', len(js), flush=True)
    with ProcessPoolExecutor(max_workers=min(6, len(js))) as ex:
        futs = [ex.submit(_one, j) for j in js]
        for f in as_completed(futs):
            r = f.result()
            print(('[%6.1fs] ' % r['secs']) + (r['text'] if r['ok'] else 'FAILED ' + r['error']),
                  flush=True)


if __name__ == '__main__':
    main()
