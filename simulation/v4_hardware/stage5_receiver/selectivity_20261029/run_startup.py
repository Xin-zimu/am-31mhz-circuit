from run_baseband import run
from run_selectivity import HERE
import json

if __name__=='__main__':
    if (HERE/'failures.json').exists():
        print(json.dumps(dict(status='prior_startup_failures_preserved',success=False,
            note='Three bounded attempts timed out. No automatic retry; see failures.json.')))
        raise SystemExit(0)
    # Ideal detector-equivalent pulse + 4.7k source resistance. Slow reference /
    # coupling test only; it does not validate RF start-up or wireless reception.
    # Full 0-to-9 V power ramp with uic was attempted once as BB_cold_400ms:
    # 240 s timeout, no raw arrays. Retained failure is not rerun by default.
    # A 400ms reference-start run also timed out once. Keep both failed files.
    # One bounded 20ms diagnostic is the final startup attempt in this batch.
    run('BB_reference_20ms',integrated=False,wave='square',duty=.5,reference_start=True,
        low=.11,high=.56,step=1000,stop=20000,start=0)
