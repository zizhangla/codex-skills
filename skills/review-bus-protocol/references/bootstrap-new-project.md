# Standing up the Review Bus in a new project

The HoloGuide3D reference implementation lives in `{WAVEFRONT_PROJECT_ROOT}`
(bridge: `.ai_orchestrator/codex/bridge.py`; protocol docs:
`.ai_orchestrator/protocol/`) with the bus repo at `D:\HoloGuide3D-Review`
(GitHub `zizhangla/HoloGuide3D-Review`). Read those files as the authoritative
templates before adapting; do not reimplement from this checklist alone when
the reference is reachable.

## 1. Create the bus repo

- One private GitHub repo, separate from the research workspace.
- Contents: `README.md` (round-trip description), `PROJECT_STATE.md`,
  `CURRENT_TASK.md`, `GPT_DECISION.md`, `REVIEW_PACKET.md`,
  `DECISION_REQUEST.md`, `GPT_OPERATIONAL_DECISION.md`, plus small
  allowlisted `SOURCE/`, `RESULTS/`, `HISTORY/`, `AUDIT/` exports.
- `.gitignore` blocks credentials/session names and large data/model formats.
  Binary evidence is committed only when a decision explicitly authorizes it
  (`git add -f` + justification in the packet Changes section).
- Keep the repo compact: markdown packets, compact JSON state, hash records.
  Checkpoints/datasets stay local, hash-bound.

## 2. Install the protocol docs

Copy and adapt four documents into the project (paths under
`.ai_orchestrator/protocol/` in the reference):

1. `PROTOCOL.md` — FSM table, identity/hash rules, persistence, failure
   handling, recovery commands.
2. `GPT_DECISION_SCHEMA.md` — decision header + nine required sections.
3. `REVIEW_PACKET_SCHEMA.md` — packet scalars + three required sections.
4. `WEB_GPT_PROJECT_BRIEF.md` — the reviewer's role brief and scientific
   objective (project-specific; rewrite for the new project).

Plus, in the bus repo: `OPERATIONAL_ESCALATION_POLICY.md` (DECISION_REQUEST /
GPT_OPERATIONAL_DECISION rules) and `HOLOBRIDGE_REALTIME_ARCHITECTURE.md`
(transport design) — both in the reference bus repo root.

## 3. Port or deploy the bridge

Reference: `.ai_orchestrator/codex/bridge.py` (single file, stdlib-only).
Requirements it encodes:

- States: `WAITING_FOR_GLM` → `WAITING_FOR_REVIEW_PACKET` → `WAITING_FOR_GPT`
  → (ingest + advance) → next round. Fail-closed on every mismatch.
- Commands (one-shot, never looped): `status`, `audit`, `round0 --dry-run`,
  `validate-review PATH`, `validate-decision PATH`, `register-result --commit
  COMMIT --result-id ID`, `ingest-review PATH`, `ingest-decision PATH`,
  `advance-decision --confirmation DECISION_ACCEPTED`,
  `record-communication-failure --channel ... --message ...`,
  `recover-manual-web --confirmation BRIDGE_TEST_OK`,
  `recover-verified-push --confirmation PUSH_VERIFIED`.
- State in `state.json` (schema_version, round, state, glm_commit, result_id,
  review_packet_sha256, gpt_reviewed_commit, gpt_reviewed_result_id,
  gpt_decision_sha256, failure counters). Atomic writes; exclusive bounded
  lock; locks never auto-deleted.
- A pre-commit/pre-push repo hook that refuses carrier commits outside the
  legal transition is cheap insurance (Windows git cannot spawn a bare `.py`
  hook — install a `#!/bin/sh` wrapper that execs the Python body).

## 4. Bootstrap the web GPT reviewer

In the dedicated web ChatGPT project/conversation, paste once (adapt names;
reference: `WEB_GPT_BOOTSTRAP_PROMPT.md`):

```text
你是 <项目名> 的科研决策者和审查者。私有审查仓库是：<repo URL>

请先读取 PROJECT_STATE.md、README.md、CURRENT_TASK.md、REVIEW_PACKET.md 和
GPT_DECISION.md。若无法直接访问私有仓库，要求我上传这些文件，不要猜测。
每轮只审查 REVIEW_PACKET.md 绑定的一个 round，并严格核对 round、commit、
result ID、SHA256、authority、budget、lock、provenance、门槛与 stop rules。
网页回复不覆盖本地 authority；数值/合成证据不得写成硬件、人眼、实时或论文
级证据。禁止重跑已消耗 attempt、绕过 lock、修改冻结阈值或恢复已关闭路线。

输出必须包含：Decision、Round、Reviewed Commit、Reviewed Result ID，以及
Scientific Assessment、Evidence Assessment、Problems Found、Required Next
Actions、Allowed Changes、Forbidden Changes、Acceptance Criteria、Instructions
For GLM、Questions Requiring Human Review。Instructions For GLM 每轮只能给出
一个有界且可验证的授权任务。Reviewed Commit 必须写已登记 base 的完整 40 位
哈希；Decision 只能取 APPROVE/REVISE/REJECT/HUMAN_REVIEW。

现在先进行通信测试。请只回复：BRIDGE_TEST_OK
```

The `BRIDGE_TEST_OK` reply is the transport test; it grants no authority.

## 5. Round-0 transport test (no scientific authority)

1. Write a dummy round-0 packet; `bridge.py round0 --dry-run` → clean.
2. Push; wake the web GPT once (manual is fine at this stage).
3. Web GPT reads the repo and writes `GPT_DECISION.md`; validate + ingest +
   advance. Run the full validation matrix from the realtime architecture doc
   (duplicate wake idempotency, wrong identity blocked, tampered decision
   rejected, fail-closed on unexpected browser target).

## 6. Optional automation (add only when round volume justifies)

Order (each layer subsumes the previous as fallback):

1. **Manual**: user or executor manually prompts the web GPT after each push.
2. **Browser wake adapter**: fixed trigger, receipts state machine, one wake
   per idempotency key. Store the target conversation URL/config LOCALLY only
   (never committed). Stop-and-notify on unexpected pages.
3. **Model-free reverse-wake daemon** (5 s poll): fetch origin (direct git,
   per-command proxy fallback; never change global proxy settings) → validate
   full decision schema/identity → atomic-lease claim → ingest exactly once →
   write `dispatch_request.json` → release → require executor heartbeat.
   Fail-closed receipts; consumed-keys ledger prevents double processing.
4. **OS watchdog** (Windows Task Scheduler, 1 min): restarts a dead daemon;
   hidden via a VBS wrapper (`window style 0`); deploy script pure ASCII
   (build paths from Unicode codepoints, write VBS with explicit CP936) so
   GBK mojibake cannot corrupt the stored action. Daemon spawns all
   subprocesses with `CREATE_NO_WINDOW`; single-instance O_EXCL guard.
5. **Scheduled watcher cycles** (Watcher A = decision dispatch, B = packet
   wake): watchdog/recovery ONLY; quiet while a lease is ACTIVE; never race
   the primary path.
6. **Single-writer lease** (`execution_lease.json`, round-keyed, atomic
   acquire with ownership token, released with the carrier commit).
7. **Quota gate**: transport/integrity work always allowed; model-heavy
   execution gated by the project's quota policy (e.g. Beijing-time free
   window + remaining-quota thresholds; below the weekly floor latch silence
   for model calls only).

## 7. First real round checklist

- [ ] Project's own AGENTS.md / frozen contracts name what web GPT may
      authorize (the bus carries authority; it does not create it).
- [ ] Bus repo synced; bridge state clean (`status` + `audit`).
- [ ] Lease acquired for the round; executor knows the ONE bounded task.
- [ ] Specs frozen by hash in their own commit before compute.
- [ ] Closeout order followed (SKILL.md § Round lifecycle); packet carries
      the full 40-char base hash; Changes section complete.
- [ ] Validator PASS → register/ingest → lease released → ONE wake →
      receipts confirmed.
- [ ] Handoff persisted: changed files/hashes, test outcome, blockers, next
      authorized action, prohibitions.
