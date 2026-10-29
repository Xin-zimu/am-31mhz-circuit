"""Archive the four observed failed attempts; no simulator is launched."""
import json
from run_selectivity import HERE,WORK,sha

def main():
    failures=[]
    for name in ['B_bb_sine','BB_cold_400ms','BB_reference_400ms','BB_reference_20ms']:
        parse=name=='B_bb_sine';paths=[HERE/'netlists'/(name+'.cir'),HERE/'netlists'/(name+'_source.cir'),WORK/(name+'.log')]
        raw=WORK/(name+'.raw')
        if raw.exists():paths.append(raw)
        dst=HERE/'results'/(name+'.log');data=(WORK/(name+'.log')).read_bytes()
        if dst.exists():assert dst.read_bytes()==data
        else:dst.write_bytes(data)
        failures.append(dict(name=name,status='parse_failure' if parse else 'timeout',
            timeout_s=None if parse else 240,valid_transient_arrays=False,
            reason='duplicate RLOAD name; repaired as RBBLOAD in later uniquely named cases' if parse
                else 'process killed after fixed 240 s timeout; no raw output; root cause not established',
            files=[dict(path=str(p.resolve()),sha256=sha(p),bytes=p.stat().st_size) for p in paths]))
    (HERE/'failures.json').write_text(json.dumps(failures,indent=2),encoding='utf-8')
    print(json.dumps(dict(failed_attempts=len(failures),startup_successes=0)))

if __name__=='__main__':main()
