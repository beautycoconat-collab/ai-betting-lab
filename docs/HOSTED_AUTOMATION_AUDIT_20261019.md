# Hosted automation readiness audit — 2026-10-19

This is a read-only production-state snapshot. No migrations, wagers, source calls or worker credentials were used.

- Supabase project: oswpkwwbjwyktuqcakhr (existing, active).
- lab.collection_jobs: 0.
- lab.raw_snapshots: 2.
- lab.quota_usage: 0.
- lab.source_access_policies with approved, unexpired review: 0.
- lab.predictions: 62 (existing records, not evidence of fresh automated predictions).
- Imported Python overlay on feature/expert-engines: commit 8ba45a1db605959630dfc67463ad2351a5976148.
- Import verification workflow: GitHub Actions run 39307759855, succeeded.

## Current blocker

Production fixture collection must remain disabled while there are no currently approved sources and no verified durable quota/worker publication path. The prepared daily-research workflow remains manual-only and gated. The SQLite cache in that workflow is not sufficient proof of durable quota accounting.

## Required before enabling cron

1. Review actual provider permissions, license, quota and expiration and approve at least one source.
2. Bind a least-privilege worker to durable Supabase source jobs/quota transactions; test idempotency and retries.
3. Verify JWT and RLS with real anonymous/authenticated/worker sessions and record evidence.
4. Confirm dashboard publication is read-only and independent of betting execution.
5. Run one supervised end-to-end dry run and verify persisted job, raw snapshot, prediction and result reconciliation.
6. Enable cron only after checks pass. No real-money or virtual portfolio execution.

Do not infer deployment readiness from a passing unit test or from a manually uploaded ZIP.
