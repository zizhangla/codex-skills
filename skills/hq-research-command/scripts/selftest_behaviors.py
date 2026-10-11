"""Synthetic negative gates only. Never imports a project's scientific code."""
from pathlib import Path
import importlib.util,tempfile,json,base64,hashlib,copy
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run():
 v=load('validate_packet');c=load('capture_sources');ready=load('check_publication_readiness');results=[]
 def check(name,condition):
  if not condition:raise AssertionError(name)
  results.append(dict(test=name,status='PASS'))
 check('empty template blocks',v.validate(dict(schema='hq.command_packet.v1',execution_authorized=False,projects=[]))['status']=='BLOCKED')
 check('execution claim blocks',v.validate(dict(schema='hq.command_packet.v1',execution_authorized=True,projects=[]))['status']=='BLOCKED')
 check('malformed packet blocks',v.validate(None)['status']=='BLOCKED')
 x={k:'evidence' for k in ('authority','code_evidence','plan_evidence','result_evidence','limitations','primary_hypothesis','strongest_null','counterexamples','novelty_sources','upper_conditions','audit_path')}
 x.update(project='P11',source_head='a'*40,current_axes=[1]*5,upper_axes=[2]*5,metrics=[dict(name='loss',definition='all parents',unit='dimensionless',independent_unit='parent',threshold_status='DRAFT')],stages=[dict(entry='native',exit='accepted',kill='reject',authority_needed='fresh',budget_status='UNKNOWN')])
 p=dict(schema='hq.command_packet.v1',execution_authorized=False,projects=[x]);check('complete is not scientific grant',v.validate(p)['status']=='COMPLETE_ONLY_NOT_SCIENTIFIC_ACCEPTANCE')
 for name,fn in [('nonhex head',lambda y:y.update(source_head='z'*40)),('NaN axes',lambda y:y.update(current_axes=[float('nan')]*5)),('missing counterexample',lambda y:y.pop('counterexamples')),('missing independent unit',lambda y:y['metrics'][0].pop('independent_unit'))]:
  z=copy.deepcopy(p);fn(z['projects'][0]);check(name,v.validate(z)['status']=='BLOCKED')
 rr=dict(execution_authorized=False,projects=[dict(project='P11',canonical_lookup='READ_AND_RECONCILED_FOR_METHOD_REVIEW',canonical_evidence=['verified path/hash'],execution_admission='NOT_GRANTED_BY_THIS_PACKET',native_blockers_and_limits='Q1 remains blocked')])
 rr.update({k:True for k in ('hq_live_identity_verified','hq_active_hashes_verified','hq_current_register_consistent','source_reconciliation_complete','independent_review_conditions_satisfied','changed_paths_allowlisted')})
 check('ready record is method only',ready.check(rr)['status']=='METHOD_PUBLICATION_RECORD_READY__NOT_EXECUTION_AUTHORITY')
 for state in ('ALL_MISSING','SUPERSEDED_UNRECONCILED'):
  z=copy.deepcopy(rr);z['projects'][0]['canonical_lookup']=state;check('workflow '+state,ready.check(z)['status']=='BLOCKED_KEEP_AFFECTED_DIRECTION_DRAFT')
 b=b'read-only synthetic';sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 def mock(repo,path):
  if path.startswith('branches/'):
   if 'bad' in path:raise RuntimeError('synthetic branch unavailable')
   return {'commit':{'sha':'b'*40}}
  if path.startswith('git/trees/'):return {'tree':[dict(path='CONTRACT.md',sha=sha,type='blob')],'truncated':False}
  if path.startswith('git/blobs/'):return {'content':base64.b64encode(b).decode()}
  raise AssertionError('unexpected API')
 c.api=mock
 with tempfile.TemporaryDirectory(prefix='hq_skill_synthetic_') as d:
  good=dict(project='P11',repo='synthetic/repo',branch='ok',paths=['CONTRACT.md','MISSING.md'])
  rows=c.capture([good],d);check('capture pins/hash and records missing',rows[0]['head']=='b'*40 and rows[0]['files'][1]['missing'])
  for name,change in [('path traversal',dict(paths=['../escape.txt'])),('project traversal',dict(project='../escape')),('missing branch',dict(branch='bad'))]:
   s=dict(good);s.update(change)
   try:c.capture([good,s],Path(d)/name.replace(' ','_'))
   except RuntimeError:
    q=Path(d)/name.replace(' ','_');check(name,json.loads((q/'CAPTURE_ERRORS.json').read_text()) and len(json.loads((q/'SOURCE_STATE.json').read_text()))==1)
   else:raise AssertionError(name+' did not block')
 return dict(status='PASS_SYNTHETIC_BEHAVIOR_ONLY',tests=results,science_executed=False)
if __name__=='__main__':print(json.dumps(run(),indent=2))
