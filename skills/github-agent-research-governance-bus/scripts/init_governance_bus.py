#!/usr/bin/env python3
"""Initialize a project-local GitHub research governance bus without overwrites."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


class InitError(RuntimeError):
    pass


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=120)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def render(source: Path, destination: Path, substitutions: dict[str, str]) -> None:
    text = source.read_text(encoding="utf-8")
    for key, value in substitutions.items():
        text = text.replace("{{" + key + "}}", value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def ensure_git_repo(target: Path, branch: str) -> str:
    probe = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=target)
    if probe.returncode == 0 and probe.stdout.strip() == "true":
        current = run(["git", "branch", "--show-current"], cwd=target)
        return current.stdout.strip() or "DETACHED"
    created = run(["git", "init", "-b", branch], cwd=target)
    if created.returncode != 0:
        fallback = run(["git", "init"], cwd=target)
        if fallback.returncode != 0:
            raise InitError((created.stderr + fallback.stderr).strip())
        symbolic = run(["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"], cwd=target)
        if symbolic.returncode != 0:
            raise InitError(symbolic.stderr.strip())
    return branch


def build_plan(target: Path) -> list[tuple[Path, Path]]:
    return [
        (SKILL_ROOT / "templates/GPT_DECISION.md", target / "GPT_DECISION.md"),
        (SKILL_ROOT / "templates/PROJECT_STATE.md", target / "PROJECT_STATE.md"),
        (SKILL_ROOT / "templates/CURRENT_TASK.md", target / "CURRENT_TASK.md"),
        (SKILL_ROOT / "templates/REVIEW_PACKET.md", target / "REVIEW_PACKET.md"),
        (SKILL_ROOT / "context-map/PROJECT_MEMORY_MAP.md", target / "context-map/PROJECT_MEMORY_MAP.md"),
        (SKILL_ROOT / "context-map/IDEA_LOG.md", target / "context-map/IDEA_LOG.md"),
        (SKILL_ROOT / "context-map/RESEARCH_HISTORY.md", target / "context-map/RESEARCH_HISTORY.md"),
        (SKILL_ROOT / "bridge/bridge_protocol.md", target / "bridge/bridge_protocol.md"),
        (SKILL_ROOT / "bridge/state_machine.md", target / "bridge/state_machine.md"),
        (SKILL_ROOT / "bridge/message_schema.json", target / "bridge/message_schema.json"),
        (SKILL_ROOT / "bridge/bridge_config.json", target / "bridge/bridge_config.json"),
    ]


def configured_repository_url(target: Path, github_repository: str | None) -> str:
    if github_repository:
        return f"https://github.com/{github_repository}.git"
    remote = run(["git", "remote", "get-url", "origin"], cwd=target)
    return remote.stdout.strip() if remote.returncode == 0 and remote.stdout.strip() else "UNCONFIGURED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_path", type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--authority-branch", default="master")
    parser.add_argument("--github", metavar="OWNER/REPOSITORY", help="create a GitHub remote with gh")
    visibility = parser.add_mutually_exclusive_group()
    visibility.add_argument("--private", action="store_true")
    visibility.add_argument("--public", action="store_true")
    parser.add_argument("--commit", action="store_true", help="create a local scaffold commit")
    parser.add_argument("--push", action="store_true", help="push the scaffold commit; requires --github and --commit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not PROJECT_ID_RE.fullmatch(args.project_id):
        raise InitError("project-id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    if not BRANCH_RE.fullmatch(args.authority_branch) or ".." in args.authority_branch:
        raise InitError("authority branch is malformed")
    if args.push and not (args.github and args.commit):
        raise InitError("--push requires both --github and --commit")
    if (args.private or args.public) and not args.github:
        raise InitError("--private/--public requires --github")

    target = args.project_path.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    plan = build_plan(target)
    extra_paths = [
        target / "bridge/bridge_state.json",
        target / "SOURCE/.gitkeep",
        target / "RESULTS/.gitkeep",
        target / "review-history/.gitkeep",
    ]
    collisions = [str(dst) for _, dst in plan if dst.exists()]
    collisions.extend(str(path) for path in extra_paths if path.exists())
    if collisions:
        raise InitError("refusing to overwrite existing governance paths: " + ", ".join(collisions))

    current_branch = ensure_git_repo(target, args.authority_branch)
    repository_url = configured_repository_url(target, args.github)
    substitutions = {
        "PROJECT_ID": args.project_id,
        "AUTHORITY_BRANCH": args.authority_branch,
        "REPOSITORY_URL": repository_url,
        "TIMESTAMP": utc_now(),
    }
    for source, destination in plan:
        render(source, destination, substitutions)

    state = {
        "schema_version": "github-agent-research-governance-bus.state.v1",
        "project_id": args.project_id,
        "round": 0,
        "state": "INIT",
        "decision_commit": None,
        "decision_sha256": None,
        "reviewed_commit": None,
        "carrier_commit": None,
        "result_id": None,
        "review_packet_sha256": None,
        "communication_failures_consecutive": 0,
        "communication_failures_total": 0,
        "last_error": None,
        "last_updated": utc_now(),
    }
    state_path = target / "bridge/bridge_state.json"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    for path in extra_paths[1:]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    attributes = target / ".gitattributes"
    if not attributes.exists():
        attributes.write_text("*.md text eol=lf\n*.json text eol=lf\n", encoding="utf-8", newline="\n")

    if args.commit:
        add = run(["git", "add", "--", "GPT_DECISION.md", "PROJECT_STATE.md", "CURRENT_TASK.md", "REVIEW_PACKET.md", "context-map", "bridge", "SOURCE/.gitkeep", "RESULTS/.gitkeep", "review-history/.gitkeep", ".gitattributes"], cwd=target)
        if add.returncode != 0:
            raise InitError(add.stderr.strip())
        commit = run(["git", "commit", "-m", "Initialize research governance bus"], cwd=target)
        if commit.returncode != 0:
            raise InitError("scaffold created but commit failed: " + commit.stderr.strip())

    if args.github:
        if shutil.which("gh") is None:
            raise InitError("scaffold created, but GitHub CLI 'gh' was not found")
        visibility = "--public" if args.public else "--private"
        create = run(["gh", "repo", "create", args.github, visibility, "--source", str(target), "--remote", "origin"], cwd=target)
        if create.returncode != 0:
            raise InitError("scaffold created, but GitHub repository creation failed: " + create.stderr.strip())
        if args.push:
            pushed = run(["git", "push", "-u", "origin", args.authority_branch], cwd=target)
            if pushed.returncode != 0:
                raise InitError("GitHub repository created, but push failed: " + pushed.stderr.strip())

    print(json.dumps({
        "status": "initialized",
        "project_path": str(target),
        "project_id": args.project_id,
        "authority_branch": args.authority_branch,
        "current_branch": current_branch,
        "github": args.github,
        "repository_url": repository_url,
        "committed": bool(args.commit),
        "pushed": bool(args.push),
        "execution_authorized": False,
        "next": "Web-GPT must replace the DRAFT decision, commit it on the authority branch, and pass authority validation.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InitError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
