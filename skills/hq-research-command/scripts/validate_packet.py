"""Completeness only; no scientific validity or execution grant."""
import json,argparse,math,re
def validate(p):
 errors=[];need=lambda ok,msg:errors.append(msg) if not ok else None
 if not isinstance(p,dict):return dict(status='BLOCKED',errors=['packet must be object'],execution_authorized=False)
 need(p.get('schema')=='hq.command_packet.v1','schema');need(p.get('execution_authorized') is False,'no execution grant')
 projects=p.get('projects',[])
 if not isinstance(projects,list):return dict(status='BLOCKED',errors=['projects must be array'],execution_authorized=False)
 need(bool(projects),'projects');ids=set()
 for x in projects:
  if not isinstance(x,dict):errors.append('project must be object');continue
  n=x.get('project','?');need(n not in ids,'duplicate:'+n);ids.add(n)
  for k in ('source_head','authority','code_evidence','plan_evidence','result_evidence','limitations','primary_hypothesis','strongest_null','counterexamples','metrics','stages','novelty_sources','current_axes','upper_axes','upper_conditions','audit_path'):need(bool(x.get(k)),n+':'+k)
  need(isinstance(x.get('source_head'),str) and bool(re.fullmatch(r'[0-9a-f]{40}',x.get('source_head',''))),n+':head')
  for label in ('current_axes','upper_axes'):
   v=x.get(label,[]);need(isinstance(v,list) and len(v)==5 and all(isinstance(a,(int,float)) and not isinstance(a,bool) and math.isfinite(a) and 0<=a<=10 for a in v),n+':'+label)
  for m in x.get('metrics',[]):
   for k in ('name','definition','unit','independent_unit','threshold_status'):need(bool(m.get(k)),n+':metric:'+k)
  for s in x.get('stages',[]):
   for k in ('entry','exit','kill','authority_needed','budget_status'):need(bool(s.get(k)),n+':stage:'+k)
 return dict(status='COMPLETE_ONLY_NOT_SCIENTIFIC_ACCEPTANCE' if not errors else 'BLOCKED',errors=errors,execution_authorized=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('packet');a=p.parse_args();r=validate(json.load(open(a.packet,encoding='utf-8')));print(json.dumps(r));raise SystemExit(bool(r['errors']))
