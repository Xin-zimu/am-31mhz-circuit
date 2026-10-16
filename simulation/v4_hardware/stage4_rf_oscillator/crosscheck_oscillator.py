"""Run the unchanged exploratory oscillator with verified ngspice-47 (64-bit).

Only the analysis wrapper and numerical options differ from the archived DUT.
Nothing here turns assumed crystal parameters into C518062 specifications.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import ctypes
import json
import re
import shutil
import subprocess
import time
import numpy as np
import verify_oscillator as analysis

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'c518062_model_20261016/lowdrive_1ms_tail.cir'
OUT=HERE/'crosscheck_20261017'
WORK=Path('D:/ms_xsp/s04_crosscheck_20261017')
EXE=WORK/'Spice64/bin/ngspice_con.exe'


def read_ngraw(path):
    with path.open('rb') as f:
        names=[]; header=[]; in_vars=False
        while True:
            line=f.readline().decode('ascii').strip()
            header.append(line)
            if line=='Binary:': break
            if line=='Variables:': in_vars=True; continue
            if in_vars and line: names.append(line.split()[1].lower())
        assert 'Flags: real' in header
        expected=int(next(x.split(':',1)[1] for x in header if x.startswith('No. Points:')))
        values=np.fromfile(f,dtype='<f8').reshape(-1,len(names))
    assert len(values)==expected and np.isfinite(values).all()
    assert np.all(np.diff(values[:,0])>=0)
    return names,values


class MemoryCounters(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in
        ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
         'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]


def run(a):
    OUT.mkdir(exist_ok=True)
    assert a.name.isascii() and a.name.replace('_','').isalnum()
    assert 0<=a.save_from_us<a.stop_us and a.step_ns>0
    assert not any((WORK/(a.name+e)).exists() for e in ('.raw','.log','.status.json'))
    source=SOURCE.read_text(encoding='ascii')
    body=source[:source.lower().rfind('.end')]
    # Explicit options are used by ngspice. Multisim's options were not overridden.
    options=f'.options method=trap maxord=2 reltol={a.reltol} trtol=7 temp=27 tnom=27'
    control=(f'set filetype=binary\nset num_threads=1\nsave v(vcc) v(base) v(emit) v(isupply) v(imotional)\n'
             f'tran {a.step_ns}n {a.stop_us}u {a.save_from_us}u {a.step_ns}n uic\n'
             f'write {WORK.as_posix()}/{a.name}.raw\nquit\n')
    net=body+options+'\n.control\n'+control+'.endc\n.end\n'
    (OUT/(a.name+'.cir')).write_text(net,encoding='ascii')
    (OUT/(a.name+'.cmd')).write_text(control,encoding='ascii')
    p=json.loads((SOURCE.with_suffix('.input.json')).read_text())
    p.update(name=a.name,solver='ngspice-47 64-bit console',step_ns=a.step_ns,stop_us=a.stop_us,
             save_from_us=a.save_from_us,reltol=a.reltol,method='trap',trtol=7,
             source_dut_sha256=analysis.sha(SOURCE),dut_body_sha256=__import__('hashlib').sha256(body.encode('ascii')).hexdigest(),
             executable_sha256=analysis.sha(EXE),raw_format='ngspice binary real float64',
             no_component_or_model_parameter_changes=True)
    (OUT/(a.name+'.input.json')).write_text(json.dumps(p,indent=2),encoding='utf-8')
    shutil.copy2(OUT/(a.name+'.cir'),WORK/(a.name+'.cir'))
    shutil.copy2(OUT/(a.name+'.cmd'),WORK/(a.name+'.cmd'))
    start=time.monotonic(); peak_rss=0; peak_commit=0
    with (WORK/(a.name+'.console.txt')).open('wb') as stdout:
        proc=subprocess.Popen([str(EXE),'-b','-n','-o',str(WORK/(a.name+'.log')),str(WORK/(a.name+'.cir'))],
            cwd=WORK,stdout=stdout,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        while proc.poll() is None:
            counters=MemoryCounters(); counters.cb=ctypes.sizeof(counters)
            if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(proc._handle)),ctypes.byref(counters),counters.cb):
                peak_rss=max(peak_rss,counters.PeakWorkingSetSize)
                peak_commit=max(peak_commit,counters.PeakPagefileUsage)
            if time.monotonic()-start>a.timeout_s:
                proc.kill(); proc.wait(); break
            time.sleep(.2)
    log=(WORK/(a.name+'.log')).read_text(errors='replace')
    errors=[line for line in log.splitlines() if re.match(r'\s*(error|fatal)',line,re.I)]
    status=dict(solver='ngspice-47',exit_code=proc.returncode,seconds=time.monotonic()-start,
                state=0 if proc.returncode==0 else 1,last_error='' if proc.returncode==0 else 'ngspice process failed',
                log_errors=errors,output_exists=(WORK/(a.name+'.raw')).exists(),
                sampled_peak_working_set_bytes=peak_rss,sampled_peak_commit_bytes=peak_commit)
    (WORK/(a.name+'.status.json')).write_text(json.dumps(status,indent=2),encoding='utf-8')
    for ext in ('console.txt','log','status.json'):
        shutil.copy2(WORK/(a.name+'.'+ext),OUT/(a.name+'.'+ext))
    print(json.dumps(status),flush=True)
    assert proc.returncode==0 and not errors and status['output_exists'],status
    # Reuse exactly the established time-weighted measurement / 100 us screen.
    analysis.OUT=OUT; analysis.WORK=WORK; analysis.read_raw=read_ngraw
    analysis.measure(SimpleNamespace(name=a.name))
    result_path=OUT/(a.name+'.result.json')
    result=json.loads(result_path.read_text())
    result.update(solver='ngspice-47',no_component_or_model_parameter_changes=True)
    result_path.write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    parser.add_argument('--stop-us',type=float,default=1000)
    parser.add_argument('--save-from-us',type=float,default=900)
    parser.add_argument('--step-ns',type=float,default=.25)
    parser.add_argument('--reltol',type=float,default=.001)
    parser.add_argument('--timeout-s',type=float,default=240)
    run(parser.parse_args())
