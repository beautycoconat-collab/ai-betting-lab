# Offline expert-worker chain — 16 October 2026

**Scope:** local, retrospective, synthetic-evidence acceptance only. This code is
**not** a live prediction product, real-lineup verification or hosted worker.

The new `experts/worker_pipeline.py` connects four **real callable handlers**
through the existing `foundation.Runtime` + `experts.Dispatcher`:

```text
Immutable fixture / claims / as_of / snapshots
           |
    VALIDATE (DataValidator)  -- blocked -> dependent jobs blocked
           |
    MODEL (ScoreEngine + Synthesizer) -- versioned 1X2, spread, input hash
           |
    RED_TEAM (RedTeam.inspect) -- typed findings, no numeric override
           |
    REFEREE (ScientificReferee.decide) -- 2 rounds max, unresolved -> abstain
           |
    Immutable task output + hash-chain audit; PUBLISHING DISABLED
```

Dependencies are awaited in the existing persistent queue; handlers check the
prior output's stage and the immutable input fingerprint. Source identity,
cutoff, claim publication time, training/test separation, model version and
result probability mass are checked. Timeouts, cancellations, retry/fencing,
append-only output and idempotency reuse existing tested dispatcher behavior.

The model task stores only bounded probability and version metadata, **not**
a fabricated xG or halftime model. The referee never overrides probabilities.
An `approved` referee verdict means local deterministic checks had no findings
for these inputs; it does **not** authorize a live prediction or virtual bet.
Every output has `publishing_enabled=false`. The flow intentionally does not
save a `f_prediction_revisions` entry or create portfolio transactions.

The demonstration is `python -m scripts.demo_worker_pipeline`; its source
claims and kickoff time are **synthetic**, and the numerical models were fitted
from archived Bundesliga match results discovered *after* the games. No historic
live/prematch evidence is implied. Real source snapshot attestation from
`collection_pipeline` into this worker is **not yet complete**; do not treat
caller-supplied mock snapshot dictionaries as trusted production evidence.

## Acceptance tests

`python -m unittest tests_experts.test_worker_pipeline -v`

Verifies end-to-end task ordering, deterministic model output, Red Team
findings, referee verdict, immutable audit, proof of no portfolio side effect,
missing / conflicting / future observations, expired source policy, cancellation,
lease expiry, idempotency and retrospective-only gating.

## Outstanding blockers

- Immutable *trusted* source evidence publication and actual lineage from
  persisted source jobs to all four worker handlers.
- Full first-half, lineup and odds providers; licensed live data access.
- Hosted worker authorization, JWT/Auth/RLS acceptance and native PostgreSQL
  concurrency CI; no hosted migration applied here.
- End-to-end deterministic source->settlement journal, result adapter, dashboard,
  scheduled job and forward-only pilot.
- Independent multi-season Red Team/Referee ablation. Synthetic verdicts do
  not quantify predictive value.

The older `ResearchLab.run()` and Coordinator are unchanged. This is an additive,
separate worker orchestration step until independent data evidence and hosted
integration are validated.
