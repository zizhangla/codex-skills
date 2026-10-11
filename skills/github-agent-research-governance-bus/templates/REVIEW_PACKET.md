# REVIEW PACKET

Project ID: {{PROJECT_ID}}
Round ID: 0
Git commit: NONE
Reviewed commit: NONE
Timestamp: {{TIMESTAMP}}
Result ID: UNASSIGNED
Decision commit: NONE
Decision SHA256: NONE
SHA256: 0000000000000000000000000000000000000000000000000000000000000000

## Result Summary

State what ran, what did not run, the final protocol outcome, and the narrowest defensible interpretation.

## Evidence

List committed paths and SHA256 values for manifests, raw results, summaries, logs, tests, and relevant failures.

## Changes

List every changed path in the carrier and its purpose. Preserve previous rounds.

## Protocol Compliance

Map each acceptance criterion, allowed change, forbidden change, resource cap, retry rule, and stop rule to evidence.

## Failures And Negative Results

Record all failed, inconclusive, interrupted, and excluded outcomes with reasons fixed by the protocol.

## Claim Classification

For every proposed conclusion, use exactly one of `SUPPORTED`, `PROTOCOL_RELATIVE`, `DIRECTION_ONLY`, `DOCUMENTED`, `RETIRED`, or `SUPERSEDED`, with its evidence boundary.

## Provenance And Reproduction

Record commands, runtime, seeds, input and source hashes, population IDs, timestamps, hardware when material, and whether checks were independently reproduced or only documented.

## Reviewer Questions

Ask only questions that affect the next scientific decision or claim boundary.

## Wake Payload

After committing this packet, generate exactly one payload using the carrier commit and the SHA256 of this committed packet:

`HOLOBRIDGE_REVIEW_READY round=0 carrier_commit=<commit> reviewed_commit=<commit> result_id=<result-id> packet_sha=<64-lowercase-hex>`
