# Governance State Machine

## Canonical round path

```text
INIT
  -> PLANNING
  -> AUTHORIZED
  -> EXECUTING
  -> RESULT_READY
  -> REVIEW
  -> ACCEPTED
  -> NEXT_ROUND
  -> PLANNING
```

Every transition is persisted in the project repository or in project-local bridge state. Invalid input leaves the prior state unchanged.

| Current state | Required event and guard | Next state | Authority effect |
|---|---|---|---|
| `INIT` | Repository and governance files initialized; project ID unique | `PLANNING` | None |
| `PLANNING` | Web-GPT decision committed on authority branch; schema and identity valid; authority granted | `AUTHORIZED` | Exact decision scope becomes executable |
| `AUTHORIZED` | Live preflight passes; executor records decision commit/SHA and acquires project lock | `EXECUTING` | No scope expansion |
| `EXECUTING` | Required outputs and packet produced; failures preserved; packet validates | `RESULT_READY` | Execution authority is consumed for the bounded round |
| `RESULT_READY` | Carrier commit exists; packet is read from carrier; message identity and SHA validate | `REVIEW` | None; wake message is not authority |
| `REVIEW` | New committed decision accepts the reviewed carrier/result | `ACCEPTED` | Prior result accepted only within stated claim boundary |
| `ACCEPTED` | History and project state updated; next-round decision may be drafted | `NEXT_ROUND` | No automatic new execution |
| `NEXT_ROUND` | Round increments and prior identities are archived | `PLANNING` | None |

## Review branches

| Decision | Execution Authority | Transition | Meaning |
|---|---|---|---|
| `APPROVE` | `GRANTED` | `REVIEW -> ACCEPTED -> NEXT_ROUND -> AUTHORIZED` after new-round identity validation | Accept result and authorize the stated bounded next work |
| `APPROVE` | `DENIED` | `REVIEW -> ACCEPTED -> NEXT_ROUND -> PLANNING` | Accept result; no next execution |
| `REVISE` | `GRANTED` | `REVIEW -> NEXT_ROUND -> AUTHORIZED` after validation | Keep stated caveats and authorize exact revised work |
| `REVISE` | `DENIED` | `REVIEW -> NEXT_ROUND -> PLANNING` | Revision requested; no execution |
| `REJECT` | either | `REVIEW -> STOPPED` | Preserve rejected evidence; do not continue |
| `HUMAN_REVIEW` | either | `REVIEW -> HUMAN_REVIEW_REQUIRED` | Await an explicit committed resolution |

## Exceptional states

- `BLOCKED`: a scientific, engineering, input, equipment, budget, or provenance prerequisite failed. Record the blocker and preserve all evidence.
- `HUMAN_REVIEW_REQUIRED`: authority conflict, Git divergence, ambiguous ownership, repeated communication failure, or an explicit human question prevents safe progress.
- `STOPPED`: a reject decision, exhausted budget, triggered stop rule, or retired direction ends the current route.

Only a new committed decision may move an exceptional state back to `PLANNING` or `AUTHORIZED`. Transport recovery alone restores communication state and grants no scientific authority.

## Round invariants

- Round numbers increase monotonically within one project.
- `project_id`, repository, and authority branch bind every state transition.
- One round has one active result identity and one carrier identity.
- A consumed attempt is never replayed under the same identity.
- Prior `SOURCE/`, `RESULTS/`, decisions, packets, and history remain immutable.
- A new round may supersede an interpretation, but it never rewrites the historical record.
