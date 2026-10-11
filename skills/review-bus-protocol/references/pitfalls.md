# Operational pitfalls catalog (all observed in production)

Distilled from 70+ rounds of the HoloGuide3D Review Bus (round tags like R51
mark the precedent). Read before operating a live bus; when a rule here
conflicts with the project's own protocol docs, the project wins.

## Identity and hashes

1. **Full 40-char hashes everywhere.** Abbreviated hashes pass human review
   and then fail `match_identity` → a forced packet-correction second commit.
   Recurred five times (R51/R53/R54/R56/R57) before "full hash from the
   start" became standard.
2. **Packet `Git commit` = registered base = round N−1's REVIEW DECISION
   commit** — not the carrier (unknowable at write time), not an older round
   (R31: registering on an old commit pulled multiple rounds of files into
   the diff; R72: right result, one-round-stale base → CHANGED_FILES_MISMATCH).
3. **Decision `Reviewed Commit` must echo the registered base**, not the
   carrier — the bridge check is mechanical (R72 defect, fixed by re-emission).
4. **Verdict vocabulary is closed**: `APPROVE|REVISE|REJECT|HUMAN_REVIEW`.
   `ACCEPT` is out of vocabulary (R72) and fails validation.
5. **Hash domains are distinct**: canonical packet sha (LF, self-excluding),
   raw committed blob sha, decision sha, carrier commit. Never mix them in
   records or receipts.
6. **Write packets with `newline="\n"`** on Windows — Python `write_text`
   otherwise produces CRLF and the raw sha diverges from the committed LF
   blob (R36). Repair a diverged transport state only through the bridge's
   own idempotent publish, never by hand-editing.

## Packet format

7. **Changes lines must be `<path> - <description>` or `<path>: <description>`**
   with a path-likeness guard. Bare bullets parse as ZERO declarations →
   `CHANGED_FILES_NOT_DECLARED` blocks the wake (R35). The packet is immutable
   after push; repair = a new packet-correction commit, never a rewrite (R33).
8. **`REVIEW_PACKET.md` is implicitly declared** (self-referential; discarded
   symmetrically from both sets) — the validator fix for the round-22 stall.
9. **Required sections must be present and non-empty**: Result Summary,
   Evidence, Changes. A packet missing `## Changes` failed ingest even though
   the science was fine (R49 incident).
10. **Avoid same-carrier delete+add of similar content** — `git diff
    --name-only base..carrier` emits `old<TAB>new` as one unparseable entry
    (R60). Keep the old file as a documented superseded artifact instead.
11. **Re-verify round fields after every packet write** (`git show
    <carrier>:REVIEW_PACKET.md`): a stale tmp script silently rewrote a
    packet with the previous round's content (R51).
12. **Scalar tables must be mechanically generated**, never hand-entered — a
    hand-entered value contradicted the recomputed one and both cannot be
    true (R28→R29).

## FSM ordering

13. **Closeout order is fixed**: carrier commit → push →
    `record_published_carrier` → `register-result` → `ingest-review` →
    release lease → wake. Pushing without the trio leaves the bridge
    WAITING_FOR_GLM/unbound and the wake correctly fails with drift (R49);
    `ingest-review` before push leaves the gate refusing publication writes.
14. **`register-result` is NOT idempotent**: on retry, detect
    WAITING_FOR_REVIEW_PACKET with matching round/commit/result and SKIP.
15. **Release the lease (with carrier commit) BEFORE the wake cycle** — the
    wake is IDLE while a lease is ACTIVE.
16. **`ingest-decision` + `advance-decision` are executor-owned**: skipping
    the advance leaves the bridge on the old round and the review repo's
    pre-commit hook then refuses carrier commits ("master is read-only") —
    the hook message is the diagnostic, not a bug (R49-R52).
17. **Every decision is ingested exactly once** (consumed-keys ledger); never
    execute the same decision twice; never replay consumed attempts.
18. **Fail-closed beats clever**: no hand-edited `state.json`, no lock
    deletion, no renames to bypass. Control-plane repair (audited FSM flip +
    round repair record) only under explicit user authorization (R43/R60).
19. **Relayed "execution complete" claims can be false** — verify artifacts,
    task-request round, lease round/owner/status, and bridge state before any
    closeout (R41/R43). If execution truly didn't happen, report the gap.
20. **Clean-closeout health check** (one pass, four domains): bridge
    `state.json` (round, WAITING_FOR_GPT, bound ids); lease RELEASED with
    carrier commit; wake receipts confirm the NEW round's idempotency key;
    local HEAD == origin/master == carrier.

## Decision intake

21. **Schema-defective decisions fail closed**: missing `## Instructions For
    GLM`, non-standard headings, wrong reviewed commit, out-of-vocabulary
    verdict. Resolution = exactly-once `DECISION_REQUEST.md`; web GPT
    re-emits as a new commit (precedents R22, R44, R52, R72×2). Re-read the
    fresh file after fast-forward sync before ingesting — the working tree
    may lag the fetch.
22. **Identity mismatches stop everything** (fail-closed
    STOPPED_IDENTITY_MISMATCH): web GPT writing decisions at its own commit,
    or citing a different result id, blocks until it re-writes with matching
    identity fields or a DECISION_REQUEST reconciles. The daemon rejecting is
    correct behavior, not a bug to patch.

## Wake and browser mechanics

23. **Verify submission by the TRANSCRIPT, never the composer.** The first
    submit click can succeed while the composer still shows the draft; the
    button's aria-label then flips to STOP — a second click interrupts the
    reviewer mid-generation (R55). Trigger must appear in the transcript
    exactly once.
24. **The ChatGPT composer is ProseMirror**: `fill()` does not register the
    internal state — use real keystrokes (`locator.type`), clear via
    `execCommand('selectAll'/'delete')`, submit via the submit button element
    through `evaluate`; Enter often leaves an UNSENT draft (R39-R54).
25. **Re-navigate the browser tab by URL before typing** — tabs get reset to
    about:blank between rounds (R68); browser target config stays local and
    is never committed.
26. **`STOPPED_REPO_BLOCKED` can be a transient network failure** — verify
    with an explicit fetch + rev-parse (local == origin, tree clean) before
    treating it as a real blocker; it self-heals next cycle (R55).
27. **Wrong-base / stale-packet wakes are refused by design** —
    `STOP_POST_CARRIER_REPO_DRIFT` on a new carrier means a closeout step was
    skipped, not that the watcher is broken.

## Daemons and OS (Windows)

28. **Single-instance guard on daemons** (O_EXCL lock before the poll loop):
    a watchdog relaunching on liveness misreads once spawned 9 racing
    instances (R67).
29. **A HUNG daemon is invisible to pid-liveness probes** (process alive,
    state frozen) — also check `watcher_state.json` advances and enumerate
    process command lines; kill + restart is the fix (R49/R52).
30. **`CREATE_NO_WINDOW` on every subprocess** in polled daemons, or each
    git/powershell call flashes a console at the poll interval (R52).
31. **Scheduled-task actions must be ASCII-safe + hidden**: a GBK-mojibake
    script path made python exit 2 every minute (console flash, watchdog
    down 16 h). Deploy via pure-ASCII scripts + VBS hidden wrapper (R52).
32. **Windows git cannot spawn a bare `.py` hook** — install `#!/bin/sh`
    wrappers exec'ing the Python body (R35).
33. **Budget-cycled schedulers MUST requeue incomplete jobs** — the first
    budget-cycled run silently dropped 20 jobs and printed a premature
    COMPLETE (R52). Jobs should be checkpoint-resumable.
34. **Test fixtures lag gates**: legacy watcher tests stub newer guards and
    turn real checks into false failures — keep drift/gate coverage in
    current tests, not stale fixtures (R35).
35. **Quota gates gate model work only**: transport, integrity checks, wake,
    and failure notification stay alive during quota pauses (realtime
    architecture rule); below the weekly floor, latch model-call silence.
