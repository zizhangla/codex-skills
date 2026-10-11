---
name: review-bus-protocol
description: "GitHub Review Bus 三角色协作协议 — 网页版 ChatGPT/GPT 负责科学规划与审查，本地 GLM/ZCode 代理只做有界执行，GitHub 私有仓库作为唯一的任务/结果/权威总线（GPT_DECISION.md、REVIEW_PACKET.md、bridge 有限状态机、browser wake、reverse-wake daemon）。Use whenever setting up, operating, reviewing, debugging, or porting this protocol — including mentions of Review Bus / 审查总线, GPT_DECISION, REVIEW_PACKET, bridge 状态机 / WAITING_FOR_GPT, wake / reverse-wake / 唤醒, 规划审核执行分离, 双模型接力协作, register-result / ingest-decision / DECISION_REQUEST, or running/ closing a round in such a setup. Canonical reference implementation: HoloGuide3D."
---

> 公开项目模板：项目路径、聊天ID及账户绑定须由安装者配置。历史示例和本技能不授予消息发送、定时任务、科学执行或硬件权限；依据当前用户请求与本地项目合同使用。


# Review Bus Protocol (Web-GPT plans · GLM executes · GitHub is the bus)

A three-role collaboration in which a web ChatGPT project is the scientific
planner/reviewer, a local agent (ZCode/GLM) is the bounded executor, and a
private GitHub repository is the ONLY channel that carries tasks, results, and
authority. Everything else — chat prose, screen text, Slack, telemetry — is
never execution authority. Canonical reference implementation: the HoloGuide3D
project (bus repo `HoloGuide3D-Review`, bridge + protocol docs under
`.ai_orchestrator/`).

**Authority precedence**: when operating inside a project that already runs
this bus, that project's own protocol docs, AGENTS.md, and frozen contracts
override this skill. This skill is the portable method plus the distilled
operational lessons.

## Core principle

Local authority, attempts, locks, frozen contracts, and stop rules are always
stronger than transport convenience. The bus transports exact text and
validates identity; it never infers approval. Invalid input leaves the prior
state intact (fail closed). There are no implicit retries, sleeps, or loops;
every mutation is explicit, idempotent-guarded, and auditable as a Git commit.

## Roles

- **Web GPT (browser ChatGPT project)** — sole scientific planner, reviewer,
  and project-level decision-maker. Reads the repo independently; writes
  `GPT_DECISION.md` directly on GitHub. Cannot touch the local workspace.
  Every decision binds `Round`, `Reviewed Commit`, `Reviewed Result ID`, and
  contains fixed required sections. `Instructions For GLM` grants exactly ONE
  bounded, verifiable task per round.
- **GLM executor (local agent)** — executes exactly the one bounded task;
  produces hash-bound evidence; writes `REVIEW_PACKET.md`; validates every
  incoming decision before executing anything. Never self-assigns authority,
  never edits a decision file, never hand-edits bridge state.
- **User** — human-only forks only: research-direction changes, frozen-contract
  changes, irreversible/unique attempts under ambiguity, credentials/devices/
  costs, privacy choices, explicit HUMAN_REVIEW. A valid decision requiring no
  human review is itself the execution token; do not re-ask the user.
- **GitHub repo (the bus)** — compact exchange repo: markdown packets, small
  evidence artifacts, state JSONs. Never datasets, checkpoints, caches,
  credentials, or the full results tree.

## Bus artifacts

| File | Writer | Purpose |
|---|---|---|
| `REVIEW_PACKET.md` | executor | hash-bound result report for one round (identity fields + Result Summary + Evidence + Changes) |
| `GPT_DECISION.md` | web GPT | the review verdict; the ONLY thing that advances execution authority |
| `PROJECT_STATE.md` | executor | durable project/authority snapshot for the reviewer |
| `CURRENT_TASK.md` | executor | compact pointer to the round under review |
| `DECISION_REQUEST.md` | executor | asks web GPT to adjudicate an operational conflict or re-emit a defective decision |
| `GPT_OPERATIONAL_DECISION.md` | web GPT | reversible in-scope operational choice; may narrow but never expand authority |

Exact schemas, hash domains, and real examples: read
`references/file-schemas.md` before writing or validating any of these files.

## Bridge finite state machine

A local bridge (reference: `.ai_orchestrator/codex/bridge.py`) holds the round
state and enforces identity before any transition:

| State | Event | Next state |
|---|---|---|
| `WAITING_FOR_GLM` | `register-result` (commit + result id) | `WAITING_FOR_REVIEW_PACKET` |
| `WAITING_FOR_REVIEW_PACKET` | valid matching `REVIEW_PACKET.md` | `WAITING_FOR_GPT` |
| `WAITING_FOR_GPT` | valid matching `GPT_DECISION.md` | decision ingested; `advance-decision` opens next round `WAITING_FOR_GLM` |
| any non-human state | 2nd consecutive communication failure | `HUMAN_INTERVENTION_REQUIRED` (manual recovery only) |

Rules that make it safe:

- Identity must match exactly before acceptance: packet `Round ID` / `Git
  commit` / `Result ID` == registered state; decision `Reviewed Commit` /
  `Reviewed Result ID` == the accepted packet's identity.
- Hashes: canonical UTF-8/LF text with the `SHA256:` line omitted (packet);
  full canonical text (decision). Validation failures are protocol errors,
  never "communication failures" that bump the retry counter.
- Executor-owned steps after a decision arrives: `validate-decision` →
  `ingest-decision` (exactly once, consumed-key guarded) → `advance-decision`
  (exact confirmation string, e.g. `DECISION_ACCEPTED`) → execute.
- Mutating commands take an exclusive lock; writes are atomic (temp file +
  replace); existing locks are never auto-deleted.

## Round lifecycle (production-proven order)

1. **Intake** — sync the bus repo (fast-forward only); confirm the new
   decision's identity against registered state; ingest once; advance to the
   new round; acquire the per-round execution lease (single-writer model).
2. **Execute** — exactly the task in `Instructions For GLM`. Freeze specs,
   manifests, and thresholds by hash in their own commit BEFORE any
   outcome-producing compute. Record blockages honestly instead of weakening
   contracts.
3. **Closeout** — in this order; do not reorder:
   1. Stage results + evidence + `REVIEW_PACKET.md` (full 40-char base hash in
      the packet `Git commit` field; the base is round N−1's review decision
      commit, NOT the carrier and NOT an older round).
   2. Carrier commit + push (push BEFORE ingest-review).
   3. Publication validator (carrier≠base, strict descendant, carrier-byte
      packet, canonical + raw SHA, identity, two-directional changed-file
      equality; validator file must byte-match its committed copy).
   4. `record_published_carrier` → `register-result` → `ingest-review`
      (register-result is NOT idempotent — skip if state already matches).
   5. Release the lease (with carrier commit).
   4. **Wake** — ONE browser wake to the pre-authorized web GPT conversation
      with the fixed transport-identity trigger; verify via the receipts state
      machine (`submit_confirmed` = composer-empty AND trigger appears in the
      transcript exactly once), never by composer appearance alone.
5. **Wait** — a model-free watcher detects the next decision on GitHub,
   validates it fail-closed, and writes a dispatch request; the executor
   consumes it → go to 1.

## Defective decisions and operational escalation

- Schema-defective decisions (missing required sections, non-standard
  headings, out-of-vocabulary verdict, wrong reviewed commit) are REJECTED
  fail-closed. Never self-repair the decision file or hand-edit bridge state.
  Publish `DECISION_REQUEST.md` (exactly once per defect) asking web GPT to
  re-emit; it re-emits as a new commit; re-read the fresh file after sync
  before ingesting.
- Operational conflicts: if exactly one safe path follows from existing
  authority and integrity rules, take it automatically. If two or more
  materially different reversible paths remain, publish `DECISION_REQUEST.md`
  with identities, exact error, options + consequences, a recommendation, and
  the minimum evidence; web GPT answers via `GPT_OPERATIONAL_DECISION.md`,
  which may only narrow or choose inside existing authority.

## Safety invariants

- Authority arrives ONLY through a hash-valid decision ingested by the bridge.
  Browser-visible prose is transport, never authority.
- Full 40-character SHA hashes in EVERY identity field (packet, decision,
  package indexes). Abbreviated hashes pass human review but fail the
  identity check.
- Never delete locks, replay consumed attempts, rename paths to bypass
  budgets, or retrospectively relabel results. Repair = new audited commits.
- One wake per idempotency key (round + carrier + packet sha); retries only
  after a bounded timeout and only if no valid decision appeared.
- Engineering success is not scientific success; numerical/synthetic evidence
  never claims hardware, human-viewing, real-time, or publication-level
  performance.
- Transport/integrity checks (state inspection, fetch, hash checks, wake) are
  always allowed; model-heavy execution obeys the project's quota policy.

## Automation layers (optional)

Deploy in this order only as round volume justifies:

1. **Primary realtime path**: executor publish → carrier tuple → lease
   release → drift gate → single wake → non-model bounded poll for the new
   decision → exactly-once dispatch to the executor.
2. **Reverse-wake daemon + OS watchdog**: model-free 5 s poller (validate →
   atomic lease → ingest once → dispatch request) plus an OS-scheduler
   watchdog that restarts it. On Windows: single-instance O_EXCL guard,
   `CREATE_NO_WINDOW` on every subprocess, hidden VBS wrapper for scheduled
   tasks, pure-ASCII deploy scripts (GBK mojibake corrupts scheduled actions).
3. **Scheduled watcher cycles (Watcher A/B)** — watchdog/recovery fallback
   only; they must never race the primary path and stay quiet while a lease
   is ACTIVE.

Setup details for a fresh project: `references/bootstrap-new-project.md`.
Before operating a live bus, read `references/pitfalls.md` — it is distilled
from 70+ production rounds and every item there has actually happened.
