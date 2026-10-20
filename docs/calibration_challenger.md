# Multiclass 1X2 temperature calibration — retrospective challenger

**Status:** PARTIAL / research-only. This addition changes no production prediction,
portfolio, odds, Supabase migration, pilot, or GitHub deployment.

- `experts/calibration.py`: fitted 1X2 temperature challenger; strict input probability
  contract, duplicate match guard, chronological calibration/test separation,
  deterministic fingerprint, paired **fixture-day circular-block bootstrap**.
- `experts/calibration_benchmark.py`: reproducible Bundesliga study.
- `tests_experts/test_calibration.py`: contract, leakage and real-data tests.
- `reports/experts/calibration_challenger.json`: actual local report, not a live prediction.

## Evaluation

Run: `python -m experts.calibration_benchmark`.

| Metric | Uncalibrated Poisson | Calibrated Poisson | Difference |
|---|---:|---:|---:|
| Multiclass 1X2 log loss (98 test games) | 1.110270 | 1.078709 | -0.031561 |
| Multiclass 1X2 Brier (98 test games) | 0.671348 | 0.651689 | -0.019658 |

Temperature selected only using 73 January–February 2025 games: `T=1.26992053`.
The underlying Poisson model was fitted with 135 matches before January 2025.
The later 98 March–May 2025 matches were not used to fit temperature.

On 29 unique match dates, the deterministic exploratory paired block bootstrap
(2,000 resamples; 5-day blocks) finds the challenger-minus-baseline 95% interval:

- Log loss: [-0.073430, -0.001740]
- Brier: [-0.039498, -0.002247]

**Limitations:** This source archive was observed in October 2026, **after** the
2024–25 season, so this is a reconstructed retrospective evaluation and **not a
live time-locked prediction pilot**. It covers one season in one league, uses
no verified historical odds or upcoming lineups, and does not prove ROI or
cross-league stability. The bootstrap estimates uncertainty under one particular
block model, not a guarantee of future superiority. No automatic champion
promotion. The 1X2 transformation MUST NOT be inserted into the score matrix,
1X2-to-special-market derivations or virtual-stake decision as though it were
an internally consistent goal-score distribution.

## Related test correction

`tests_experts/test_source_bridge.py` now deep-copies the source registry per
fixture. Previously one test changed the common dictionary and corrupted
subsequent unrelated tests, causing order-dependent false failures.

## Next

Independent multi-season and multi-league forecasts; published-at and observed-at
provenance for the source and actual prediction snapshots; out-of-sample RPS and
coverage; production policy review before any model promotion; remaining
14-role handler wiring and native PostgreSQL/JWT acceptance.
