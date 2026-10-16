# Post-match result polling and 14th-expert metrics — local research only

**Status: PARTIAL. Live collection, deployment, hosted Auth/JWT/RLS and pilot disabled.**

This increment adds `experts/result_scheduler.py` and the manual `scripts/result_cycle.py` CLI. No hourly/daily GitHub Actions cron is activated. This is a controlled bridge, **not** a confirmed live data feed or end-to-end hosted settlement service.

## Evidence/permission design

1. A fixture **must already have a pre-kickoff locked forward prediction**, linked to a persisted model, Red Team and approved referee output. No results poll is planned for an arbitrary fixture or historic replay.
2. Select a **currently reviewed/approved** source and adapter (`engine.adapters.ADAPTERS`); provide the exact source-native match ID and scope parameters, previously independently validated. The code does not invent the mapping.
3. `ResultScheduler.plan(...)` records an immutable plan and enqueues one deduplicated `v2_jobs` `collect` task *not before* kickoff + 120 minutes (default). A new UTC date creates a new cycle, permitting another attempt after a provider publishes a final. The existing queue enforces source review, request quotas, leases, retries and append-only snapshot lineage.
4. Run the existing `runtime.queue.work_one(...)` **separately**, with an explicitly authorized fetcher/worker and real permissions. This module never does HTTP.
5. `ResultScheduler.reconcile(plan_id)` requires a completed source job, **exactly one** associated source snapshot observed after the eligible time and a successful `OutcomeJournal.ingest_result` check of raw hash, source-native match ID, league, season, teams, kickoff/date and regulation-90 goal result. No automatic final if a provider has not yet supplied it.
6. A corrected result or changed provenance triggers `manual_review_required`: previous rows and grades stay append-only; **corrections handling is not implemented**.
7. Grading uses only previously locked predictions and 90-minute results; Brier/Log Loss are computed independently of virtual ROI. `performance_windows()` reports 7/30/90/180-day windows **for locked predictions only**. It does not claim total-market coverage, CLV, ROI, calibration reliability or proof of live performance.

### Commands (run manually, trusted local SQLite only)

A plan manifest is a JSON array of objects with exactly the keys `fixture_id`, `source_id`, `params`, `native_id`. Map provider IDs to locked fixture contracts independently, before submission.

```bash
python -m scripts.result_cycle --db /secure/local.sqlite --mode plan --manifest /secure/verified_result_manifest.json
# Run the existing quota/permission checked source collector explicitly, after not_before.
python -m scripts.result_cycle --db /secure/local.sqlite --mode reconcile
python -m scripts.result_cycle --db /secure/local.sqlite --mode report
python -m unittest tests_experts.test_result_scheduler -v
```

**Security limitations:** SQLite is a trusted-process boundary; there is no hosted worker auth. Provider response observed time is **not** independent published-at attestation. Web access/ToS could have changed since the source registry review; revalidate before production collection. Full-time score may later be revised. The engine's cache can contain a previous result; an observation earlier than `eligible_at` is rejected. If the final remains unavailable, prepare a plan for a **new date**; the earlier task is not silently reexecuted. No mutable prediction revisions, no real money, no bets placed. No migration 001–005 changed.
