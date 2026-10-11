import argparse,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import os
W=Path(os.environ.get('WAVEFRONT_PROJECT_ROOT', '.')).resolve()
def capture(p):
 if not p.exists():return {'path':str(p),'status':'NOT_AVAILABLE'}
 b=p.read_bytes();r={'path':str(p.resolve()),'sha256':hashlib.sha256(b).hexdigest(),'mtime_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),'bytes':len(b)}
 if p.suffix=='.json':
  try:r['data']=json.loads(b)
  except Exception:r['status']='PARSE_CONFLICT'
 else:r['excerpt']=b.decode('utf-8',errors='replace')[:16000]
 return r
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--include-file',action='append',default=[]);a=ap.parse_args();paths=[]
 for q in range(1,7):
  # Capture all explicitly goal-labelled candidate workspaces; no date authority.
  for p in (W/'research_scouts').glob(f'FRONTIER_V3_Q{q}_*'):
   goal=p/'RESEARCH_GOAL.json'
   if not goal.exists():continue
   try:
    g=json.loads(goal.read_bytes())
    if g.get('project')!=f'Q{q}':continue
   except Exception:continue
   paths.extend(p/n for n in ['SESSION_STATE.json','RESEARCH_GOAL.json','PLATFORM_GOAL_RECEIPT.json','CLAIMS.json','GOAL_ACCEPTANCE.json','GOAL_PROGRESS_REPORT.md','GOAL_REPORT.md','GOAL_CLOSEOUT.md','CLOSURE_REPORT.md','GOAL_CLOSURE_REPORT.md','REPORT_CYCLE2.md','REPORT.md'] if (p/n).exists())
 roots=[Path('D:/P5/current/P5_LOCAL_RESEARCH/explorations'),Path('D:/P11/HoloGuide3D-Review/P11_REVIEW_BUS/EXPLORATION'),Path('D:/P12/research'),Path('D:/P13/reports')]
 for root in roots:
  if not root.exists():continue
  dirs=sorted((p for p in root.iterdir() if p.is_dir()),key=lambda p:p.stat().st_mtime,reverse=True)[:3]
  for d in dirs:
   for name in ['RESULT.json','RESULTS.json','OUTPUT/RESULTS.json','STATE.json','SESSION_STATE.json','HANDOFF.md','SCIENCE_RECONCILIATION.md','GRAND_AUDIT_AND_HANDOFF.md','DERIVATION.md','summary.json','result.json']:
    p=d/name
    if p.exists():paths.append(p)
 paths.append(W/'reports/total_project_takeover_20261007/TOTAL_PROJECT_REGISTRY.json')
 paths.extend(Path(p) for p in a.include_file)
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'observed_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'INCOMPLETE_READ_ONLY_CANDIDATE_CAPTURE_NOT_CURRENT_AUTHORITY_OR_SCIENTIFIC_VALIDATION','discovery_limits':['Q goal-labelled workspace candidates; current owner selected separately from live chat/HQ/native index','P three mtime candidate directories only, NOT exhaustive or proof of current active evidence','Historical registry explicitly 2026-10-07, not live status','Pass --include-file for actual current evidence selected from live authority/goal/thread index'], 'authoritatively_selected_additional_files':a.include_file,'files':[capture(p) for p in dict.fromkeys(paths)]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'snapshot':str(out.resolve()),'captured_files':len(paths),'complete_current_status':False}))
if __name__=='__main__':main()
