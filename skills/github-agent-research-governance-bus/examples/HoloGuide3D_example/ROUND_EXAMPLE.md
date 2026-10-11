# Fictional Governed Round

This example demonstrates structure only. All identifiers and findings are invented.

## Web-GPT decision

Web-GPT reviews result commit `1111111`, records `Decision: REVISE`, and sets `Execution Authority: GRANTED` for one bounded numerical verification. It freezes the population, metric, threshold, seed rule, resource cap, and stop conditions. It allows a new verification script and a new result directory. It forbids retraining, population changes, threshold changes, deletion of earlier failures, and optical or hardware claims.

## Local execution

The local agent validates the committed decision on `master`, records the decision commit and SHA, checks inputs and budgets, and runs only the authorized verification. It commits:

```text
SOURCE/round_12_verifier.py
SOURCE/round_12_manifest.json
RESULTS/round_12/raw_records.jsonl
RESULTS/round_12/summary.json
RESULTS/round_12/failures.jsonl
REVIEW_PACKET.md
```

The result misses the frozen gate. The agent preserves the result and proposes classification `PROTOCOL_RELATIVE`; it does not lower the threshold or claim general failure.

## Review wake

After committing the packet in carrier `2222222`, the bridge computes the exact committed packet blob SHA and emits:

```text
HOLOBRIDGE_REVIEW_READY round=12 carrier_commit=2222222 reviewed_commit=1111111 result_id=fictional-round-12 packet_sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

This message wakes Web-GPT. It does not authorize another run.

## Forensic correction

A later audit discovers that an older analysis used a different stopping rule. The old files remain unchanged. The audit marks the old claim `PROTOCOL_RELATIVE`, adds the corrected evidence and Git ancestry, and a later committed decision marks the broader wording `SUPERSEDED`.
