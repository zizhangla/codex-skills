# GitHub Agent Research Governance Bus

This Skill creates a reusable research control plane for three roles:

- Web-GPT is the scientific planner, architect, reviewer, and decision authority.
- A local agent such as GLM, ZCode, or Codex is the programmer, numerical verifier, and experiment runner.
- GitHub is the only persistent scientific and governance source of truth.

The design separates notification from authority. A browser message can wake a reviewer, but the executor acts only on a committed, validated `GPT_DECISION.md` from the configured authority branch.

## Skill layout

```text
github-agent-research-governance-bus/
|-- SKILL.md
|-- README.md
|-- agents/
|   `-- openai.yaml
|-- scripts/
|   |-- init_governance_bus.py
|   `-- validate_governance_bus.py
|-- templates/
|   |-- GPT_DECISION.md
|   |-- PROJECT_STATE.md
|   |-- CURRENT_TASK.md
|   `-- REVIEW_PACKET.md
|-- context-map/
|   |-- PROJECT_MEMORY_MAP.md
|   |-- IDEA_LOG.md
|   `-- RESEARCH_HISTORY.md
|-- bridge/
|   |-- bridge_protocol.md
|   |-- bridge_config.json
|   |-- message_schema.json
|   `-- state_machine.md
`-- examples/
    `-- HoloGuide3D_example/
        |-- README.md
        `-- ROUND_EXAMPLE.md
```

## Initialize a repository

```powershell
$skill = '{USER_HOME}/.codex/skills/github-agent-research-governance-bus'
python "$skill/scripts/init_governance_bus.py" 'D:/research/my-project' `
  --project-id my-project `
  --authority-branch master
```

This creates a local Git repository when one is absent, the governance documents, `SOURCE/`, `RESULTS/`, `review-history/`, and local bridge state. It does not overwrite existing paths or create a remote by default.

Until `origin` is configured and the scaffold is pushed, structure checks can pass but authority validation will fail closed. This preserves GitHub as the source of truth.

To create a GitHub repository as part of initialization, use the explicit remote option:

```powershell
python "$skill/scripts/init_governance_bus.py" 'D:/research/my-project' `
  --project-id my-project `
  --authority-branch master `
  --github OWNER/REPOSITORY `
  --private
```

The second form requires an authenticated GitHub CLI and creates external state, so it should be used only when requested.

## First governed round

1. Fill `PROJECT_STATE.md`, `CURRENT_TASK.md`, and `context-map/PROJECT_MEMORY_MAP.md`.
2. Web-GPT replaces the draft fields in `GPT_DECISION.md`. The nine required level-two headings must remain unchanged.
3. Commit the decision on the configured authority branch.
4. The local agent runs the authority validator and records the returned decision commit and SHA.
5. The local agent executes the bounded work, preserving sources, raw results, failures, manifests, and tests.
6. Complete `REVIEW_PACKET.md`, calculate its canonical self-excluding SHA, commit the packet with `SOURCE/` and `RESULTS/`, then emit the review-ready message.
7. Web-GPT reviews the exact carrier commit and publishes the next committed decision.

Useful validation commands:

```powershell
python "$skill/scripts/validate_governance_bus.py" structure --repo 'D:/research/my-project'
python "$skill/scripts/validate_governance_bus.py" authority --repo 'D:/research/my-project'
python "$skill/scripts/validate_governance_bus.py" packet --repo 'D:/research/my-project' --write-sha
python "$skill/scripts/validate_governance_bus.py" emit --repo 'D:/research/my-project' --carrier HEAD
python "$skill/scripts/validate_governance_bus.py" message --repo 'D:/research/my-project' --message '<exact-payload>'
```

## Authority boundary

A decision is executable only when all of these conditions are true:

- `GPT_DECISION.md` has been committed and its working copy equals the committed blob.
- The configured Git remote URL matches `bridge_config.json`, a fresh fetch succeeds, and local `HEAD` exactly matches the remote authority branch.
- The checkout is on `authority_branch` from `bridge/bridge_config.json`.
- The decision schema, project ID, round identity, allowed/forbidden sections, and required headings validate.
- `Decision` is `APPROVE` or `REVISE` and `Execution Authority` is `GRANTED`.
- The decision has not expired.
- No validated review packet has already consumed the same decision commit and round.

An accepted result and permission for a new experiment are distinct. A decision can accept prior evidence while denying further execution.

## Evidence and claim control

Each review packet binds the reviewed commit, result ID, evidence paths, hashes, commands, environment, acceptance checks, failures, and proposed claim classifications. Web-GPT may narrow or reject the claims. Local agents may never widen them.

The allowed classifications are:

| Classification | Meaning |
|---|---|
| `SUPPORTED` | The stated claim is directly supported within its explicit population and protocol. |
| `PROTOCOL_RELATIVE` | Supported only under the named solver, metric, threshold, budget, or historical protocol. |
| `DIRECTION_ONLY` | Suggestive signal that does not meet a frozen acceptance gate. |
| `DOCUMENTED` | Recorded from provenance or history but not independently re-established. |
| `RETIRED` | A direction was closed by an explicit decision; retain its evidence and reason. |
| `SUPERSEDED` | A later governed result or correction replaces the earlier interpretation without deleting it. |

## Parallel projects

Parallel use is supported by repository isolation. Each project has a unique `project_id`, repository endpoint, authority branch, state file, lock path, result namespace, and message receiver. Round numbers may repeat across projects because repository and project identity provide the namespace. A shared daemon must route to a project-specific checkout before validation and must never use one project's decision or packet to advance another.
