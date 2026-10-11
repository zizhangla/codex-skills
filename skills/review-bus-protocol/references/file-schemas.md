# Review Bus file schemas (with real examples)

All files are UTF-8 Markdown. Scalars occur exactly once as unindented
`Name: value` lines. Text is stored unchanged apart from canonical LF line
endings (on Windows write packets with `newline="\n"` or the raw-blob hash
diverges from the local file).

## GPT_DECISION.md (written by web GPT)

Header scalars — each exactly once:

```text
# GPT DECISION

Decision: APPROVE | REVISE | REJECT | HUMAN_REVIEW
Round: non-negative integer
Reviewed Commit: exact accepted Git commit (the registered BASE, full 40-char)
Reviewed Result ID: exact accepted Result ID
```

Required non-empty `##` sections (all nine, exact headings):

- `Scientific Assessment`
- `Evidence Assessment`
- `Problems Found`
- `Required Next Actions`
- `Allowed Changes`
- `Forbidden Changes`
- `Acceptance Criteria`
- `Instructions For GLM`
- `Questions Requiring Human Review`

Hard rules learned in production:

- The verdict vocabulary is exactly `{APPROVE, REVISE, REJECT, HUMAN_REVIEW}`;
  anything else (e.g. `ACCEPT`) fails validation.
- `Reviewed Commit` must echo the REGISTERED BASE commit (round N−1's review
  decision commit), not the result carrier — the identity check is mechanical.
- `Instructions For GLM` grants exactly one bounded, verifiable task per
  round; multi-task or open-ended instructions are a schema defect.

Real example (R72, abridged):

```text
# GPT DECISION

Decision: APPROVE
Round: 72
Reviewed Commit: 024730ae5302f10cf2622ea330c115d9cbfdb6ce
Reviewed Result ID: P3L_EVIDENCE_REPAIR_COMPLETE_CONFOUND_INVENTORY_GPU_PARITY_ACCEPTABLE_R72

## Scientific Assessment
Web-GPT reviewed the Round-72 carrier `1e7110a...` against the registered
Round-72 authority/base commit `024730ae...`, independently checked the
three-commit lineage, ...
```

## REVIEW_PACKET.md (written by executor)

```text
# REVIEW PACKET

Round ID: non-negative integer
Git commit: FULL 40-char base hash (round N−1 review decision commit)
Timestamp: ISO-8601 timestamp with timezone
Result ID: letters, digits, dot, underscore, colon, or hyphen
SHA256: 64 lowercase hex chars

## Result Summary
...

## Evidence
...

## Changes
<path> - <one-line description>
...
```

Rules:

- `SHA256` is computed over the full text normalized to LF with the entire
  `SHA256:` line omitted (canonical self-excluding hash). Distinct hash
  domains exist alongside it: the raw committed blob sha and the decision sha
  — never mix them in records.
- The packet's `Git commit` is the REGISTERED BASE, not the carrier. The
  carrier is unknowable at packet-write time.
- `## Changes` must declare every path in `base..carrier` as
  `<path> - <description>` (or `<path>: <description>`); bare markdown
  bullets parse as ZERO declarations and block the wake. `REVIEW_PACKET.md`
  itself is implicitly declared (self-referential, discarded symmetrically).
  Two-directional set equality against the real diff is the security property.
- The packet is IMMUTABLE once pushed. A defect (abbreviated hash, missing
  section) is repaired by a NEW packet-correction commit — never by rewriting
  the pushed packet, never by hand-editing bridge state. The carrier tip
  (packet-correction commit) is the review carrier.
- After writing the packet, verify the committed bytes:
  `git show <carrier>:REVIEW_PACKET.md` and re-check round fields (stale tmp
  scripts have silently rewritten packets with the previous round's content).
- Avoid delete+add of similar-content files in one carrier: `git diff
  --name-only base..carrier` emits `old<TAB>new` as one entry the validator
  cannot parse.

Real example (R73, abridged):

```text
# REVIEW PACKET

Round ID: 73
Git commit: 024730ae5302f10cf2622ea330c115d9cbfdb6ce
Timestamp: 2026-09-15T03:27:04+08:00
Result ID: P3M_SPATIAL_BANDWIDTH_MANIPULATION_INVALID_R73
SHA256: 9937afe6870504c58506627107d0962ef5d29d62f7c272bcd485ed79d4fede31

## Result Summary
Executed the authorized macro-round ... and the predeclared
manipulation-validity gate correctly stopped mechanism interpretation: ...
```

## DECISION_REQUEST.md (written by executor, exactly once per issue)

Required content: active round/result/carrier/base identities; the exact
pause reason/error; current authority/attempt/lock state; options considered
with concrete consequences; the executor's recommendation and why; files/state
each option would change; reversibility and provenance impact; whether any
option would expand authority, consume an attempt, touch a frozen contract,
or run scientific compute; the minimum evidence needed to decide. No secrets,
tokens, cookies, or remote-control URLs. End by requesting the wake.

## GPT_OPERATIONAL_DECISION.md (written by web GPT)

Valid ONLY for a reversible implementation/recovery choice already inside the
current decision's scope. It may choose or narrow a path but may NEVER: grant
new scientific authority; approve construction; consume/reset/increase an
attempt; create/delete/bypass a lock; alter a frozen contract, seed/order/
split, threshold, or protected set; authorize compute not already granted; or
replace a required HUMAN_REVIEW.

## CURRENT_TASK.md / PROJECT_STATE.md

Compact executor-maintained pointers for the reviewer: current round, macro
round + governing decision commit, result id, outcome one-paragraph, and what
web GPT must decide next. PROJECT_STATE carries the durable authority/attempt/
lock snapshot. Keep them small; they are re-read every round by the reviewer.

## Wake trigger and receipts

The browser wake types ONE fixed structured trigger into the pre-authorized
web GPT conversation — transport identity only, no content:

```text
HOLOBRIDGE_REVIEW_READY round=<n> carrier_commit=<sha> reviewed_commit=<sha> result_id=<id> packet_sha=<sha>. Read the <Project> Review Repo and complete the normal governed review. GitHub is source of truth.
```

Receipts state machine (idempotent, per attempt): `browser_target_found` →
`submit_confirmed` (requires composer-empty AND the trigger appearing in the
transcript region exactly once) → optional `reviewer_message_observed` (may
legitimately stay null). Never infer submission from composer state alone;
never re-click submit (the button may have become the STOP button and a
second click interrupts the reviewer's response mid-generation).
