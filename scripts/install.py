"""Install a reviewed local bundle without overwriting existing Codex skills."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--all',action='store_true')
    ap.add_argument('--skills',nargs='+')
    ap.add_argument('--dest',type=Path)
    ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args()
    if a.all == bool(a.skills):ap.error('choose exactly one of --all or --skills')
    repo=Path(__file__).resolve().parents[1]
    manifest=json.loads((repo/'catalog.json').read_text(encoding='utf-8'))
    available={s['name']:s for s in manifest['skills']}
    chosen=sorted(available) if a.all else a.skills
    unknown=set(chosen)-available.keys()
    if unknown:ap.error('unknown skills: '+', '.join(sorted(unknown)))
    destination=a.dest or Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'skills'
    destination=destination.resolve()
    integrity=json.loads((repo/'checksums.json').read_text(encoding='utf-8'))
    for name in chosen:
        source=repo/'skills'/name
        if not (source/'SKILL.md').is_file():raise ValueError('missing skill entrypoint')
        for p in source.rglob('*'):
            if p.is_symlink():raise ValueError('symlinks are not supported')
            if p.is_file():
                key=p.relative_to(repo).as_posix()
                if integrity.get(key)!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('checksum mismatch: '+key)
    refs=repo/'skills'/'shared-references'
    for p in refs.rglob('*'):
        if p.is_file():
            key=p.relative_to(repo).as_posix()
            if integrity.get(key)!=hashlib.sha256(p.read_bytes()).hexdigest():raise ValueError('checksum mismatch: '+key)
    installed=[];skipped=[]
    for name in chosen:
        dest=destination/name
        if dest.exists() or (destination/'.system'/name).exists():
            skipped.append(name);continue
        if not a.dry_run:
            destination.mkdir(parents=True,exist_ok=True)
            shutil.copytree(repo/'skills'/name,dest)
        installed.append(name)
    # Many skills link ../shared-references. Install once beside the skills.
    refs_dest=destination/'shared-references'
    if not refs_dest.exists() and not a.dry_run:
        destination.mkdir(parents=True,exist_ok=True)
        shutil.copytree(refs,refs_dest)
    print(json.dumps({'dry_run':a.dry_run,'destination':str(destination),
                      'installed_count':len(installed),'skipped_count':len(skipped),
                      'installed':installed,'skipped_existing':skipped},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
