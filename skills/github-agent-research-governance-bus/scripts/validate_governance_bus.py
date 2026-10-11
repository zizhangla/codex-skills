#!/usr/bin/env python3
"""Fail-closed validator for governance structure, authority, packets, and wakes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DECISION_HEADINGS = [
    "Scientific Assessment",
    "Problems Found",
    "Evidence Assessment",
    "Required Next Actions",
    "Acceptance Criteria",
    "Allowed Changes",
    "Forbidden Changes",
    "Questions Requiring Human Review",
    "Instructions For GLM",
]
PACKET_HEADINGS = [
    "Result Summary",
    "Evidence",
    "Changes",
    "Protocol Compliance",
    "Failures And Negative Results",
    "Claim Classification",
    "Provenance And Reproduction",
    "Reviewer Questions",
    "Wake Payload",
]
RESULT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,64}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MESSAGE_RE = re.compile(
    r"^HOLOBRIDGE_REVIEW_READY "
    r"round=(?P<round>0|[1-9][0-9]*) "
    r"carrier_commit=(?P<carrier_commit>[0-9a-f]{7,64}) "
    r"reviewed_commit=(?P<reviewed_commit>[0-9a-f]{7,64}) "
    r"result_id=(?P<result_id>[A-Za-z0-9._:-]{1,128}) "
    r"packet_sha=(?P<packet_sha>[0-9a-f]{64})$"
)


class ValidationError(RuntimeError):
    pass


def git(repo: Path, *args: str, binary: bool = False):
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=not binary,
        timeout=120,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace") if binary else completed.stderr
        raise ValidationError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return completed.stdout


def canonical_text_bytes(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_unique_scalars(text: str, names: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for name in names:
        values = [line[len(name) + 2 :].strip() for line in lines if line.startswith(name + ": ")]
        if len(values) != 1 or not values[0]:
            raise ValidationError(f"expected exactly one non-empty '{name}:' scalar")
        result[name] = values[0]
    return result


def validate_headings(text: str, expected: list[str]) -> None:
    found = [line[3:].strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.startswith("## ")]
    if found != expected:
        raise ValidationError(f"level-two headings must be exact and ordered; found {found!r}")
    parts = re.split(r"(?m)^## [^\n]+\n", text)
    for heading, body in zip(expected, parts[1:]):
        if not body.strip():
            raise ValidationError(f"section '{heading}' is empty")


def read_config(repo: Path) -> dict:
    path = repo / "bridge/bridge_config.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read bridge config: {exc}") from exc
    required = [
        "project_id", "repository_remote", "repository_url", "authority_branch",
        "authority_path", "review_packet_path", "state_path",
    ]
    if any(not isinstance(config.get(key), str) or not config[key] for key in required):
        raise ValidationError("bridge config has missing or invalid required fields")
    if config.get("browser_messages_are_authority") is not False or config.get("memory_is_authority") is not False:
        raise ValidationError("bridge config violates authority separation")
    return config


def validate_structure(repo: Path) -> dict:
    required = [
        "GPT_DECISION.md", "PROJECT_STATE.md", "CURRENT_TASK.md", "REVIEW_PACKET.md",
        "context-map/PROJECT_MEMORY_MAP.md", "context-map/IDEA_LOG.md", "context-map/RESEARCH_HISTORY.md",
        "bridge/bridge_protocol.md", "bridge/state_machine.md", "bridge/message_schema.json",
        "bridge/bridge_config.json", "bridge/bridge_state.json", "SOURCE", "RESULTS", "review-history",
    ]
    missing = [item for item in required if not (repo / item).exists()]
    if missing:
        raise ValidationError("missing required paths: " + ", ".join(missing))
    config = read_config(repo)
    state = json.loads((repo / config["state_path"]).read_text(encoding="utf-8"))
    if state.get("project_id") != config["project_id"]:
        raise ValidationError("bridge state project_id does not match config")
    return {"status": "PASS", "check": "structure", "project_id": config["project_id"]}


def parse_decision(text: str) -> dict[str, str]:
    if not text.startswith("# GPT DECISION"):
        raise ValidationError("decision title must be '# GPT DECISION'")
    fields = parse_unique_scalars(text, [
        "Project ID", "Decision", "Execution Authority", "Round", "Reviewed Commit",
        "Reviewed Result ID", "Authority Branch", "Valid Until",
    ])
    validate_headings(text, DECISION_HEADINGS)
    if fields["Decision"] not in {"APPROVE", "REVISE", "REJECT", "HUMAN_REVIEW"}:
        raise ValidationError("Decision must be APPROVE, REVISE, REJECT, or HUMAN_REVIEW")
    if fields["Execution Authority"] not in {"GRANTED", "DENIED"}:
        raise ValidationError("Execution Authority must be GRANTED or DENIED")
    if not fields["Round"].isdigit():
        raise ValidationError("Round must be a non-negative integer")
    if fields["Reviewed Commit"] != "NONE" and not COMMIT_RE.fullmatch(fields["Reviewed Commit"]):
        raise ValidationError("Reviewed Commit must be a Git SHA or NONE")
    if fields["Reviewed Result ID"] != "NONE" and not RESULT_ID_RE.fullmatch(fields["Reviewed Result ID"]):
        raise ValidationError("Reviewed Result ID is malformed")
    if fields["Valid Until"] != "NONE":
        try:
            expires = datetime.fromisoformat(fields["Valid Until"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError("Valid Until must be ISO-8601 with timezone or NONE") from exc
        if expires.tzinfo is None:
            raise ValidationError("Valid Until must include a timezone")
        if expires.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise ValidationError("decision has expired")
    return fields


def validate_authority(repo: Path) -> dict:
    config = read_config(repo)
    authority_rel = config["authority_path"]
    config_rel = "bridge/bridge_config.json"
    authority_path = repo / authority_rel
    working = authority_path.read_text(encoding="utf-8")
    fields = parse_decision(working)
    branch = git(repo, "branch", "--show-current").strip()
    if branch != config["authority_branch"] or fields["Authority Branch"] != config["authority_branch"]:
        raise ValidationError(f"authority branch mismatch: checkout={branch!r}")
    if fields["Project ID"] != config["project_id"]:
        raise ValidationError("decision project_id does not match bridge config")
    dirty = git(repo, "status", "--porcelain=v1", "--", authority_rel, config_rel).strip()
    if dirty:
        raise ValidationError("authority decision or bridge config has staged, unstaged, or untracked changes")
    committed_raw = git(repo, "show", f"HEAD:{authority_rel}", binary=True)
    if canonical_text_bytes(working) != canonical_text_bytes(committed_raw.decode("utf-8")):
        raise ValidationError("working decision does not match the committed HEAD blob")
    committed_config = git(repo, "show", f"HEAD:{config_rel}", binary=True)
    if (repo / config_rel).read_bytes() != committed_config:
        raise ValidationError("working bridge config does not match the committed HEAD blob")
    if config["repository_url"] == "UNCONFIGURED":
        raise ValidationError("GitHub repository URL is unconfigured")
    remote = config["repository_remote"]
    actual_remote_url = git(repo, "remote", "get-url", remote).strip()
    normalize_url = lambda value: value.rstrip("/")[:-4] if value.rstrip("/").endswith(".git") else value.rstrip("/")
    if normalize_url(actual_remote_url) != normalize_url(config["repository_url"]):
        raise ValidationError("configured repository URL does not match the Git remote")
    git(repo, "fetch", remote, config["authority_branch"])
    head_commit = git(repo, "rev-parse", "HEAD").strip()
    remote_commit = git(repo, "rev-parse", f"refs/remotes/{remote}/{config['authority_branch']}").strip()
    if head_commit != remote_commit:
        raise ValidationError("local HEAD is not exactly synchronized with the configured GitHub authority branch")
    decision_commit = git(repo, "log", "-1", "--format=%H", "--", authority_rel).strip()
    if not decision_commit:
        raise ValidationError("cannot resolve the commit that published GPT_DECISION.md")
    packet_path = repo / config["review_packet_path"]
    if packet_path.is_file():
        try:
            prior_packet = parse_packet(packet_path.read_text(encoding="utf-8"), config["project_id"], require_sha=True)
        except ValidationError:
            prior_packet = None
        if (
            prior_packet
            and prior_packet["Decision commit"] == decision_commit
            and int(prior_packet["Round ID"]) == int(fields["Round"])
        ):
            raise ValidationError("this decision already has a completed review packet and cannot be replayed")
    if fields["Execution Authority"] != "GRANTED" or fields["Decision"] not in {"APPROVE", "REVISE"}:
        raise ValidationError("decision is valid governance text but does not grant execution authority")
    return {
        "status": "PASS",
        "check": "authority",
        "project_id": config["project_id"],
        "round": int(fields["Round"]),
        "decision": fields["Decision"],
        "decision_commit": decision_commit,
        "decision_sha256": sha256(canonical_text_bytes(working)),
        "authority_branch": branch,
    }


def packet_without_sha(text: str) -> bytes:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    filtered = [line for line in lines if not line.startswith("SHA256: ")]
    return ("\n".join(filtered)).encode("utf-8")


def parse_packet(text: str, project_id: str, require_sha: bool = True) -> dict[str, str]:
    if not text.startswith("# REVIEW PACKET"):
        raise ValidationError("packet title must be '# REVIEW PACKET'")
    fields = parse_unique_scalars(text, [
        "Project ID", "Round ID", "Git commit", "Reviewed commit", "Timestamp", "Result ID",
        "Decision commit", "Decision SHA256", "SHA256",
    ])
    validate_headings(text, PACKET_HEADINGS)
    if fields["Project ID"] != project_id:
        raise ValidationError("packet project_id does not match bridge config")
    if not fields["Round ID"].isdigit():
        raise ValidationError("Round ID must be a non-negative integer")
    for name in ["Git commit", "Reviewed commit", "Decision commit"]:
        if not COMMIT_RE.fullmatch(fields[name]):
            raise ValidationError(f"{name} must be a Git SHA")
    if fields["Git commit"] != fields["Reviewed commit"]:
        raise ValidationError("Git commit and Reviewed commit must identify the same result commit")
    if not RESULT_ID_RE.fullmatch(fields["Result ID"]):
        raise ValidationError("Result ID is malformed")
    if not SHA_RE.fullmatch(fields["Decision SHA256"]):
        raise ValidationError("Decision SHA256 is malformed")
    try:
        stamp = datetime.fromisoformat(fields["Timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("Timestamp must be ISO-8601 with timezone") from exc
    if stamp.tzinfo is None:
        raise ValidationError("Timestamp must include a timezone")
    computed = sha256(packet_without_sha(text))
    if require_sha and fields["SHA256"] != computed:
        raise ValidationError(f"packet canonical SHA mismatch: declared={fields['SHA256']} computed={computed}")
    fields["computed_sha256"] = computed
    return fields


def validate_packet(repo: Path, write_sha: bool = False) -> dict:
    config = read_config(repo)
    path = repo / config["review_packet_path"]
    text = path.read_text(encoding="utf-8")
    if write_sha:
        fields = parse_packet(text, config["project_id"], require_sha=False)
        text = re.sub(r"(?m)^SHA256: .+$", "SHA256: " + fields["computed_sha256"], text, count=1)
        path.write_text(text, encoding="utf-8", newline="\n")
    fields = parse_packet(text, config["project_id"], require_sha=True)
    for commit_field in ["Reviewed commit", "Decision commit"]:
        git(repo, "cat-file", "-e", fields[commit_field] + "^{commit}")
    return {
        "status": "PASS", "check": "packet", "project_id": config["project_id"],
        "round": int(fields["Round ID"]), "result_id": fields["Result ID"],
        "reviewed_commit": fields["Reviewed commit"], "canonical_packet_sha256": fields["computed_sha256"],
        "sha_written": write_sha,
    }


def carrier_packet(repo: Path, carrier: str) -> tuple[dict, bytes, dict]:
    config = read_config(repo)
    git(repo, "cat-file", "-e", carrier + "^{commit}")
    git(repo, "merge-base", "--is-ancestor", carrier, config["authority_branch"])
    raw = git(repo, "show", f"{carrier}:{config['review_packet_path']}", binary=True)
    if len(raw) > int(config.get("max_input_bytes", 1048576)):
        raise ValidationError("committed review packet exceeds max_input_bytes")
    packet = parse_packet(raw.decode("utf-8"), config["project_id"], require_sha=True)
    return config, raw, packet


def emit_message(repo: Path, carrier: str) -> dict:
    carrier_full = git(repo, "rev-parse", carrier).strip()
    _, raw, packet = carrier_packet(repo, carrier_full)
    payload = (
        f"HOLOBRIDGE_REVIEW_READY round={int(packet['Round ID'])} "
        f"carrier_commit={carrier_full} reviewed_commit={packet['Reviewed commit']} "
        f"result_id={packet['Result ID']} packet_sha={sha256(raw)}"
    )
    return {"status": "PASS", "check": "emit", "message": payload, "authority_granted": False}


def validate_message(repo: Path, message: str) -> dict:
    match = MESSAGE_RE.fullmatch(message.strip())
    if not match:
        raise ValidationError("message does not match the canonical HOLOBRIDGE_REVIEW_READY format")
    values = match.groupdict()
    _, raw, packet = carrier_packet(repo, values["carrier_commit"])
    expected = {
        "round": str(int(packet["Round ID"])),
        "reviewed_commit": packet["Reviewed commit"],
        "result_id": packet["Result ID"],
        "packet_sha": sha256(raw),
    }
    mismatches = {key: {"message": values[key], "packet": value} for key, value in expected.items() if values[key] != value}
    if mismatches:
        raise ValidationError("message identity mismatch: " + json.dumps(mismatches, sort_keys=True))
    return {
        "status": "PASS", "check": "message", "round": int(values["round"]),
        "carrier_commit": values["carrier_commit"], "reviewed_commit": values["reviewed_commit"],
        "result_id": values["result_id"], "packet_sha": values["packet_sha"], "authority_granted": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["structure", "authority"]:
        child = sub.add_parser(name)
        child.add_argument("--repo", type=Path, required=True)
    packet = sub.add_parser("packet")
    packet.add_argument("--repo", type=Path, required=True)
    packet.add_argument("--write-sha", action="store_true")
    emit = sub.add_parser("emit")
    emit.add_argument("--repo", type=Path, required=True)
    emit.add_argument("--carrier", default="HEAD")
    message = sub.add_parser("message")
    message.add_argument("--repo", type=Path, required=True)
    message.add_argument("--message", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.expanduser().resolve()
    if args.command == "structure":
        result = validate_structure(repo)
    elif args.command == "authority":
        result = validate_authority(repo)
    elif args.command == "packet":
        result = validate_packet(repo, args.write_sha)
    elif args.command == "emit":
        result = emit_message(repo, args.carrier)
    else:
        result = validate_message(repo, args.message)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
