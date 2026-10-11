"""Explicit, isolated Windows COMSOL engineering smoke test; no project files loaded."""
import argparse, ctypes as C, hashlib, json, math, os, re, shutil, subprocess, time
from ctypes import wintypes as W
from pathlib import Path

class Basic(C.Structure):
    _fields_=[('ProcessTime',C.c_longlong),('JobTime',C.c_longlong),('Flags',W.DWORD),
              ('MinWS',C.c_size_t),('MaxWS',C.c_size_t),('ActiveLimit',W.DWORD),
              ('Affinity',C.c_size_t),('Priority',W.DWORD),('Scheduling',W.DWORD)]
class IO(C.Structure):
    _fields_=[(x,C.c_ulonglong) for x in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
class Extended(C.Structure):
    _fields_=[('Basic',Basic),('IO',IO),('ProcessMemoryLimit',C.c_size_t),
              ('JobMemoryLimit',C.c_size_t),('PeakProcessMemoryUsed',C.c_size_t),('PeakJobMemoryUsed',C.c_size_t)]

def execute(argv, directory, seconds, cap):
    # Suspend before assignment so descendant processes inherit the bounded job.
    k=C.WinDLL('kernel32',use_last_error=True)
    k.CreateJobObjectW.argtypes=[C.c_void_p,W.LPCWSTR]; k.CreateJobObjectW.restype=W.HANDLE
    k.SetInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD]
    k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE]
    k.QueryInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p]
    k.TerminateJobObject.argtypes=[W.HANDLE,W.UINT]; k.CloseHandle.argtypes=[W.HANDLE]
    job=k.CreateJobObjectW(None,None)
    if not job: raise C.WinError(C.get_last_error())
    info=Extended(); info.Basic.Flags=0x2000|0x200; info.JobMemoryLimit=cap
    p=None; started=time.monotonic()
    try:
        if not k.SetInformationJobObject(job,9,C.byref(info),C.sizeof(info)):
            raise C.WinError(C.get_last_error())
        p=subprocess.Popen(argv,cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           creationflags=0x4|subprocess.CREATE_NO_WINDOW)
        if not k.AssignProcessToJobObject(job,W.HANDLE(int(p._handle))):
            p.kill(); p.communicate(); raise C.WinError(C.get_last_error())
        nt=C.WinDLL('ntdll'); nt.NtResumeProcess.argtypes=[W.HANDLE]
        if nt.NtResumeProcess(W.HANDLE(int(p._handle)))!=0: raise RuntimeError('resume failed')
        timed_out=False
        try: output,_=p.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out=True; k.TerminateJobObject(job,124); output,_=p.communicate(timeout=15)
        peak=Extended()
        if not k.QueryInformationJobObject(job,9,C.byref(peak),C.sizeof(peak),None):
            raise C.WinError(C.get_last_error())
        return {'argv':argv,'exit_code':p.returncode,'timeout':timed_out,
                'wall_seconds':time.monotonic()-started,'peak_job_committed_bytes':peak.PeakJobMemoryUsed},output
    finally:
        k.CloseHandle(job) # Only this helper's processes; never unrelated executors.
        if p is not None and p.poll() is None: p.wait(timeout=15)

def validate(text):
    records=re.findall(r'^COMSOL_SMOKE_RESULT=(.*)$',text,re.M)
    if len(records)!=1 or text.splitlines().count('COMSOL_SMOKE_DONE')!=1:
        raise ValueError('missing/duplicate result or completion marker')
    result=json.loads(records[0])
    if set(result)!={'integral_u','area','squared_error_integral'}: raise ValueError('schema')
    if not all(isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) for v in result.values()):
        raise ValueError('non-finite/type')
    if abs(result['area']-1)>1e-10 or abs(result['integral_u']-.5)>1e-10:
        raise ValueError('analytic area/mean mismatch')
    if not 0<=result['squared_error_integral']<=1e-18: raise ValueError('analytic field mismatch')
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-dir',required=True)
    ap.add_argument('--comsol-bin',default='C:/Program Files/COMSOL/COMSOL64/Multiphysics/bin/win64')
    args=ap.parse_args()
    if os.name!='nt': raise RuntimeError('Windows only')
    run=Path(args.run_dir).resolve(); run.mkdir(parents=True,exist_ok=False)
    binary=Path(args.comsol_bin).resolve()
    source=Path(__file__).with_name('ComsolSmoke.java'); shutil.copy2(source,run/source.name)
    receipt={'scope':'ENGINEERING_ANALYTIC_LAPLACE_ONLY','authority':'explicit user request to test COMSOL',
             'status':'STARTED','np':2,'memory_cap_bytes':4*1024**3,'timeout_per_stage_seconds':180,
             'compile_starts':0,'batch_starts':0,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    def persist():
        (run/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    persist()
    try:
        receipt['compile_starts']=1
        persist()
        stage,raw=execute([str(binary/'comsolcompile.exe'),source.name],str(run),180,receipt['memory_cap_bytes'])
        (run/'compile.log').write_bytes(raw); receipt['compile']=stage
        cls=run/'ComsolSmoke.class'
        if stage['timeout'] or stage['exit_code']!=0 or not cls.is_file() or cls.stat().st_size==0 or b'Compilation failed' in raw:
            raise RuntimeError('compile failed; batch not started')
        receipt['class_sha256']=hashlib.sha256(cls.read_bytes()).hexdigest()
        for d in ('prefs','tmp'): (run/d).mkdir()
        argv=[str(binary/'comsolbatch.exe'),'-np','2','-prefsdir',str(run/'prefs'),
              '-tmpdir',str(run/'tmp'),'-inputfile',str(cls),'-outputfile',str(run/'smoke.mph'),
              '-batchlog',str(run/'batch.log')]
        receipt['batch_starts']=1
        persist()
        stage,raw=execute(argv,str(run),180,receipt['memory_cap_bytes'])
        (run/'stdout.log').write_bytes(raw); receipt['batch']=stage
        text=raw.decode('utf-8',errors='strict')
        if stage['timeout'] or stage['exit_code']!=0: raise RuntimeError('batch process failed')
        if re.search(r'运行 Java 类时出错|Error running java|Compilation failed',text,re.I):
            raise RuntimeError('COMSOL reported Java error')
        receipt['result']=validate(text)
        models=list(run.glob('*.mph'))
        if len(models)!=1 or models[0].stat().st_size==0:
            raise RuntimeError('missing/ambiguous saved model')
        receipt['saved_model']=models[0].name
        receipt['status']='PASS_ANALYTIC_ENGINEERING_SMOKE'
    except Exception as e:
        receipt['status']='FAIL_CLOSED'; receipt['error']=str(e)
    finally:
        receipt['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in run.iterdir() if p.is_file()}
        persist()
        print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return 0 if receipt['status']=='PASS_ANALYTIC_ENGINEERING_SMOKE' else 1

if __name__=='__main__': raise SystemExit(main())
