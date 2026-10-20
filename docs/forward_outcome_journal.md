# Forward-only verified outcome journal — 2026-10-16

**Status: PARTIAL, local SQLite research integration only.** This code never places bets, changes a wallet, asserts provider-published-at, checks live scores over HTTP, or activates an automated runner. Supabase schema/migrations remain unchanged. The API must not be exposed directly as a public web endpoint: `foundation.Runtime` is a *trusted-process* SQLite boundary, not JWT/RLS.

## Purpose

`experts/outcome_journal.py` composes existing local systems:

1. `ResearchWorkerPipeline` produces a chain of **immutable** tasks: model -> Red Team -> Scientific Referee. Only a `prematch` model whose referee verdict was `approved` and whose review input corresponds to the fixture may be locked; `abstain` is rejected.
2. `OutcomeJournal.lock_prediction(...)` captures the real clock time. It rejects observations at/after kickoff, unapproved reviews, missing model dependency, mismatching model version fingerprint (`digest(versions)`), false probability mass, or changed prediction ID contents. A pre-kickoff full fixture contract is stored in an append-only local table.
3. The separate, permissioned `engine.queue.Queue.work_one()` fetches after the match under the existing legal source policy, network and quota rules. `OutcomeJournal.ingest_result(fixture_id, snapshot_id, native_id)` **does not fetch**. It re-decompresses SHA-256 verified raw bytes and reruns the exact source adapter, then compares results to the persisted normalized row. Source URL, permitted adapter, collection job state, observation time, explicit `regulation90` target, kickoff, teams, date, league, season and available neutral metadata must agree. Snapshots before the possible 90th minute and unknown target semantics are blocked. Unknown publication time is recorded as **unknown**.
4. `OutcomeJournal.grade(prediction_id)` appends **one** Brier Score and Log Loss evaluation plus optional `settle_pick` verdict (won/lost/push). Repeats are idempotent. No odds, ROI or CLV values are invented; `summary` returns `None` for both.
5. Append-only SQLite triggers protect the three outcome journal tables. `foundation.Runtime.audit()` also writes hash-linked audit events.

## Example use (in a trusted local process only)

```python
from experts.outcome_journal import OutcomeJournal
from betting_lab.domain import digest
journal = OutcomeJournal(runtime)  # existing Runtime, not a new Supabase connection
journal.lock_prediction(
    prediction_id=model_result['prediction_id'],
    fixture_id=fixture_id, probabilities=model_result['probabilities'],
    model_hash=digest(model_result['versions']),
    referee_task_id=approved_referee_task_id,
    pick={'schema_version': '1.0', 'market': '1X2', 'selection': '1',
          'score_target': 'regulation90'},
)
# AFTER full time, a separate source worker stores its completed raw snapshot:
journal.ingest_result(fixture_id, result_snapshot_id, exact_provider_match_id)
journal.grade(model_result['prediction_id'])
print(journal.summary())
```

The source collection itself must be legitimately authorized and performed by the existing `Queue`. The example is not a runnable live prediction/pilot without approved prospective model version, verified source evidence, stored fixtures and a trusted deployment.

## Validation

- `python -m unittest tests_experts.test_outcome_journal -q` — **20 tests passed** using synthetic HTTP data, including OpenFootball and OpenLiga parsing, after-match time locking, tampered byte hash, wrong season/league, referee abstention, wrong model version, repeat grading and append-only enforcement.
- `python -m unittest tests_experts.test_outcome_journal tests_experts.test_settlement tests_experts.test_collection_pipeline tests_experts.test_worker_pipeline -q` — **52 tests passed** (the newly added journal tests and selected prior acceptance tests; overlap possible).
- Earlier expert regression **175 passed** before the final competition/season and source-adapter changes. A later full suite rerun **timed out**; do not assert full-regression acceptance of this final package. No hosted CI, Supabase JWT or actual live sports-data acceptance.

## Pending work / security gates

- Connect actual permissible live source fixtures and result collection to scheduled, bounded workers; no automatic result crawler is active.
- Independent published-at evidence, external score correction/adjudication policy, conflicting provider reconciliation, and proven fixture/provider ID mapping.
- Real forward-only multi-match calibration and performance windows with benchmark comparison; verified odds, CLV and virtual portfolio journal remain unimplemented.
- Native PostgreSQL, Supabase RLS/JWT/role gates and migrations >=006 require separate review/approval; **do not activate** pilot, money accounts or unattended production jobs.
