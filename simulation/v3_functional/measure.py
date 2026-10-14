from pathlib import Path
import numpy as np
import json, sys

def read_raw(path):
    text = Path(path).read_text(errors='replace')
    head, body = text.split('Values:',1)
    names = [line.split()[-1].lower() for line in head.split('\nVariables:',1)[1].splitlines() if line.strip()]
    # Each time line includes the point index; subsequent lines contain one value.
    numbers = np.fromstring(body, sep=' ')
    data = numbers.reshape(-1, len(names)+1)[:,1:]
    assert len(data) == int(head.split('No. Points:')[1].splitlines()[0])
    return dict(zip(names,data.T))

def measurements(d):
    t=d['time']; assert t[-1] >= .00499999, f'Incomplete run: {t[-1]}'
    sel=t>=.0048; t=t[sel]
    result={}
    for name in ['v(v1)','v(v2)']:
        y=d[name][sel]; lo, hi=np.percentile(y,[2,98]); mid=(lo+hi)/2
        crossings=[]
        for direction in [1,-1]:
            ix=np.where(((y[:-1]<mid)&(y[1:]>=mid)) if direction==1 else ((y[:-1]>=mid)&(y[1:]<mid)))[0]
            crossings.append(t[ix]+(mid-y[ix])*(t[ix+1]-t[ix])/(y[ix+1]-y[ix]))
        rising,falling=crossings
        period=np.median(np.diff(rising))
        widths=[falling[falling>r][0]-r for r in rising if np.any(falling>r)]
        result[name]={'vpp_98_2':float(hi-lo),'vpp_max_min':float(np.ptp(y)),
                      'low':float(lo),'high':float(hi),'frequency_hz':float(1/period),
                      'duty_pct':float(100*np.median(widths)/period)}
    return result

if __name__=='__main__':
    for arg in sys.argv[1:]:
        d=read_raw(arg)
        print(arg, json.dumps(measurements(d)),flush=True)
