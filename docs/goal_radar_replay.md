# Goal radar: PARTIAL replay / BLOCKED live

The separate `experts.goal_radar` module fits a homogeneous Poisson interval rate
from at least 30 non-overlapping, timestamped labelled intervals. Observation
times must precede fitting. Replay fixtures must not overlap training fixtures.
It exposes next-window goal probability capped at minute 90 and a 95% rate
parameter interval. This interval is not a calibrated prediction interval.

There is no live adapter, shot/pressure model, lineup adjustment, or score-state
effect. Red cards and stale observations (>30 seconds) return insufficient_data.
Live mode always returns BLOCKED. No LLM, wallet, odds or real platform call.
Evaluation reports held-out replay Brier/Log Loss and false-alarm fraction at
the declared 0.5 threshold. It rejects duplicate cases, missing/future labels and
premature outcome observations. Multiple cases of one fixture are correlated;
the fixture count is retained and no independent-sample significance is claimed.

Tests use synthetic interval evidence only. No genuine live performance or
calibration claim is made. Provider event evidence verification and empirical
calibration remain prerequisites for any future live implementation.

Manual offline automation is prepared in research-replay.yml with no schedule,
no cloud credentials, no external data fetch and no portfolio activation.
It reproduces the preserved real two-season model report. Daily production
research and the Vercel dashboard remain incomplete.
