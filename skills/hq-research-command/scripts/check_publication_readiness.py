"""Workflow-record gate, not proof of authenticity or scientific acceptance.
The maintainer must verify every attestation against live Git/evidence first.
Missing/superseded canonical authority never permits ACTIVE scientific direction.
"""
import json,argparse
def check(p):
 e=[]
 def need(c,m):
  if not c:e.append(m)
 need(p.get('execution_authorized') is False,'execution forbidden')
 for k in ('hq_live_identity_verified','hq_active_hashes_verified','hq_current_register_consistent','source_reconciliation_complete','independent_review_conditions_satisfied','changed_paths_allowlisted'):need(p.get(k) is True,k)
 need(bool(p.get('projects')),'projects')
 for x in p.get('projects',[]):
  n=x.get('project','?');need(x.get('canonical_lookup')=='READ_AND_RECONCILED_FOR_METHOD_REVIEW',n+':missing/stale canonical authority blocks activation')
  need(bool(x.get('canonical_evidence')),n+':authority evidence')
  need(x.get('execution_admission')=='NOT_GRANTED_BY_THIS_PACKET',n+':no execution grant')
  need(bool(x.get('native_blockers_and_limits')),n+':scope limits')
 return dict(status='METHOD_PUBLICATION_RECORD_READY__NOT_EXECUTION_AUTHORITY' if not e else 'BLOCKED_KEEP_AFFECTED_DIRECTION_DRAFT',errors=e,execution_authorized=False)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('packet');p=a.parse_args();r=check(json.load(open(p.packet,encoding='utf-8')));print(json.dumps(r));raise SystemExit(bool(r['errors']))
