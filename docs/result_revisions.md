# Versioned result acceptance — 2026-10-16

`experts.result_versions.VersionedResults` reuses raw-byte verification from
`OutcomeJournal`. Snapshot id, raw hash, exact native identity, competition,
season, teams, kickoff precision, score target and observation time are retained.
Provider publication remains explicitly `unknown` when the feed has no verified
publication field. Neither HTTP Last-Modified nor retrieval time is relabelled
as match-result publication time.

`observe(fixture_id, snapshot_id, native_id)` appends an immutable observation.
Initial verified results and later matching scores are accepted; a different
score or an older observation is `conflicting`. No prior result is overwritten.
`review(ResultReview)` requires a fixture-bound scientific-referee run, candidate
snapshot evidence and an explicit reason. This is a trusted local operator
boundary, not proof of Supabase worker authentication. Only reviewed corrections
become current. `grade(prediction_id)` adds a grade per approved result version.
Old grades remain audit history. Metrics select only the latest approved version
and count each locked prediction once. Multiple models use paired fixtures;
ambiguous duplicate model/fixture forecasts block that comparison.

ResultScheduler now exposes `result_version_id`, `versioned_grades`, and
`current_performance` (7/30/90/180 days). Its old `performance` field is the
immutable first-result ledger retained for compatibility; use current_performance
for reviewed corrections. No implicit wallet re-settlement occurs.

Calibration is multiclass 1X2 reliability bins, not exact-score calibration.
Coverage and abstain remain null because the all-candidate denominator is not
recorded. Resolved fraction is labelled with the locked-prediction denominator.
ROI and CLV remain null without valid decision/price/closing-price records.
No automatic champion promotion or pilot is enabled.

Real network acceptance: OpenFootball 2025-26/de.1 returned 306 fixtures/results.
Initial parser rejected 12 legacy `[home,away]` score arrays. Supporting that
explicit provider representation and offline replay of the same raw bytes
accepted all 306, with zero additional network requests. Missing scores and
half-time-only scores remain missing. Snapshot and parser hashes are in
reports/experts/source_acceptance_20261016.json. This is retrospective source
acceptance, not a recorded forward-model success.

Primary policy references: https://github.com/openfootball/football.json and
https://github.com/openfootball/football.json/blob/master/LICENSE.md (CC0).
OpenLigaDB API documentation was accessible, but its licence page returned only
a cookie notice to the research tool; no new live OpenLigaDB licence acceptance
is claimed. Existing policy and adapter are preserved.

Run `python -m scripts.ci_python` and
`python -m unittest tests_experts.test_result_versions -v`.
All new storage is local SQLite. No hosted migration was applied. Migrations
001–005 remain byte-identical. Hosted JWT/RLS and worker acceptance remain open.
