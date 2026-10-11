#!/usr/bin/env python3
"""Check dossier structure and local evidence paths; NOT science, security, or budget certification."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

STATUSES={'CONSTRUCTIVE_EVIDENCE','CONDITIONAL_THEORY','NUMERICAL_EVIDENCE','ENGINEERING_QUALIFIED',
          'FALSIFIED_WITHIN_SCOPE','CLASSICAL_BASELINE_SUFFICIENT','RESOURCE_REVERSAL','UNKNOWN',
          'NOT_READ','NOT_AVAILABLE'}
EVIDENCE_REQUIRED=STATUSES-{'UNKNOWN','NOT_READ','NOT_AVAILABLE'}
REQUIRED={'QUESTION.md','SOURCE_LEDGER.json','CLAIMS.json','SESSION_STATE.json','RUN_ENVELOPE.json','HANDOFF.md'}


def check(root: Path) -> dict:
    errors=[]
    root=root.expanduser().resolve()
    if not root.is_dir():
        return {'status':'STRUCTURAL_FAIL','errors':['Workspace is not a directory.'],'science_validated':False}
    for name in sorted(REQUIRED):
        if not (root/name).is_file(): errors.append(f'Missing file: {name}')
    loaded={}
    for name in sorted(n for n in REQUIRED if n.endswith('.json')):
        if not (root/name).is_file(): continue
        try:
            data=json.loads((root/name).read_text(encoding='utf-8-sig'))
            if not isinstance(data,dict): raise ValueError('expected JSON object')
            loaded[name]=data
        except (OSError,ValueError) as exc:
            errors.append(f'{name}: {exc}')
    claims=loaded.get('CLAIMS.json',{}).get('claims',[])
    if not isinstance(claims,list):
        errors.append('claims must be a list'); claims=[]
    ids=set()
    for i,c in enumerate(claims):
        if not isinstance(c,dict):
            errors.append(f'claim {i}: not an object');continue
        cid=c.get('id')
        if not isinstance(cid,str) or not cid: errors.append(f'claim {i}: missing string id')
        elif cid in ids: errors.append(f'duplicate id: {cid}')
        else: ids.add(cid)
        status=c.get('status')
        if status not in STATUSES: errors.append(f'{cid}: unrecognized status')
        paths=c.get('evidence_paths',[])
        if not isinstance(paths,list):
            errors.append(f'{cid}: evidence_paths must be a list'); paths=[]
        if status in EVIDENCE_REQUIRED and not paths: errors.append(f'{cid}: evidence path required')
        if status in EVIDENCE_REQUIRED and not c.get('scope'): errors.append(f'{cid}: scope required')
        for text in paths:
            if not isinstance(text,str):
                errors.append(f'{cid}: evidence path must be a string');continue
            try:
                p=(root/text).resolve()
                p.relative_to(root)
                if not p.is_file(): errors.append(f'{cid}: missing evidence: {text}')
            except (ValueError,OSError):
                errors.append(f'{cid}: evidence path leaves the dossier: {text}')
    env=loaded.get('RUN_ENVELOPE.json',{})
    if env.get('numerical_experiments'):
        if env.get('authorized_by_user') is not True or not env.get('authorization_reference'):
            errors.append('Numerical execution marked enabled but no declared user authorization reference.')
    return {'status':'STRUCTURAL_FAIL' if errors else 'STRUCTURAL_PASS',
            'errors':errors,'claims_seen':len(claims),'science_validated':False,
            'note':'No theorem, numerical result, grant authenticity, hardware safety, budget use, or reproducibility was verified.'}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace',type=Path)
    args=parser.parse_args()
    report=check(args.workspace)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='STRUCTURAL_PASS' else 2

if __name__=='__main__':
    raise SystemExit(main())
