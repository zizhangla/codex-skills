#!/usr/bin/env python3
"""Create a NEW research dossier only. Never executes research or grants permission."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def create(root: Path, direction: Path) -> Path:
    source = direction.expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in {'.md', '.json', '.txt'}:
        raise ValueError('Direction must be an existing .md, .json or .txt file.')
    if source.stat().st_size > 2_000_000:
        raise ValueError('Direction file exceeds the 2 MB metadata-only limit.')
    body = source.read_text(encoding='utf-8-sig')
    dest = root.expanduser().resolve()
    if dest.exists():
        raise FileExistsError(f'Refusing to overwrite existing path: {dest}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir(exist_ok=False)
    now = datetime.now(timezone.utc).isoformat()
    def write(name: str, value: object) -> None:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        (dest/name).write_text(text.rstrip()+'\n', encoding='utf-8')
    write('QUESTION.md', '# Intake / 待执行器收口的问题\n\n'+body)
    write('SOURCE_LEDGER.json', {'sources':[{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'status':'COPIED_NOT_SCIENTIFICALLY_REVIEWED','copied_at_utc':now}]})
    write('CLAIMS.json', {'schema':'research-claims-v1','claims':[]})
    write('SESSION_STATE.json', {'schema':'research-session-v1','stage':'DRAFT','execution_authorized':False,
          'consumed_new_runs':[],'active_run':None,'created_utc':now,
          'next_minimal_action':'Read the direction; record actual user authorization if one exists; do not execute from this scaffold.'})
    write('RUN_ENVELOPE.json', {'schema':'research-run-envelope-v1','authorized_by_user':False,
          'authorization_reference':None,'numerical_experiments':False,'hardware':False,
          'remote_push':False,'workspace':str(dest),'budget':{}})
    write('HANDOFF.md', '# Handoff\n\nOnly intake scaffolding was created. No research, permissions, GPU jobs or Git writes were performed.\n')
    (dest/'runs').mkdir()
    return dest


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path, help='A new, non-existing work directory.')
    p.add_argument('--direction', required=True, type=Path)
    args=p.parse_args()
    try:
        result=create(args.root,args.direction)
    except (OSError,ValueError,UnicodeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 2
    print(json.dumps({'status':'INTAKE_CREATED_ONLY','path':str(result),'execution_authorized':False},ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
