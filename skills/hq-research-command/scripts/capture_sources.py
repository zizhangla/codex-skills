"""Pin explicit review-approved text paths; no scientific evaluation.
spec: list of {project,repo,branch,paths:[exact repo relative paths]}.
Caller must exclude protected paths; this is not an access-control sandbox.
"""
from pathlib import Path
import json,subprocess,base64,hashlib,datetime,argparse,concurrent.futures,re
def api(repo,path):
 p=subprocess.run(['gh','api','repos/'+repo+'/'+path],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
 return json.loads(p.stdout)
def capture(spec,out):
 root=Path(out);root.mkdir(parents=True,exist_ok=True)
 def one(s):
  assert re.fullmatch(r'[A-Z][A-Z0-9_]*',s['project']),'INVALID_PROJECT_ID'
  h=api(s['repo'],'branches/'+s['branch'])['commit']['sha'];assert re.fullmatch(r'[0-9a-f]{40}',h),'INVALID_HEAD'
  t=api(s['repo'],'git/trees/'+h+'?recursive=1');assert not t.get('truncated'),'TRUNCATED_TREE'
  d=root/'sources'/s['project'];d.mkdir(parents=True,exist_ok=True);(d/'tree.json').write_text(json.dumps(t),encoding='utf-8');mt={x['path']:x['sha'] for x in t['tree'] if x['type']=='blob'};rows=[]
  for p in s['paths']:
   q=(d/p).resolve();assert q.is_relative_to(d.resolve()) and not Path(p).is_absolute()
   if p not in mt:rows.append(dict(path=p,missing=True));continue
   b=base64.b64decode(api(s['repo'],'git/blobs/'+mt[p])['content']);assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==mt[p]
   q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);rows.append(dict(path=p,blob=mt[p],sha256=hashlib.sha256(b).hexdigest()))
  state=dict(project=s['project'],repo=s['repo'],branch=s['branch'],head=h,read_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=rows)
  (d/'STATE.json').write_text(json.dumps(state,indent=2),encoding='utf-8');return state
 states=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as e:
  jobs={e.submit(one,s):s['project'] for s in spec}
  for f in concurrent.futures.as_completed(jobs):
   try:states.append(f.result())
   except Exception as ex:errors.append(dict(project=jobs[f],error=str(ex)))
 (root/'SOURCE_STATE.json').write_text(json.dumps(states,indent=2),encoding='utf-8')
 (root/'CAPTURE_ERRORS.json').write_text(json.dumps(errors,indent=2),encoding='utf-8')
 if errors:raise RuntimeError('SOURCE_CAPTURE_BLOCKED '+json.dumps(errors))
 return states
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(capture(json.loads(Path(a.spec).read_text(encoding='utf-8')),a.out)))
