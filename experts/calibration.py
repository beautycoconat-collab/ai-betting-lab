"""Chronologically fitted, *research-only* 1X2 temperature calibration challenger.

Input rows are genuine previously issued probability forecasts, not scoreline
matrices. The calibrator must never rewrite the original predictions or infer
probabilities for score-dependent markets from a transformed 1X2 triplet.

Only retrospective tests are implemented. Prospective deployment requires
independently timestamped pre-kickoff inputs and production approval.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

import numpy as np
from scipy.optimize import minimize_scalar


@dataclass(frozen=True)
class ForecastObservation:
    fixture_id: str
    match_date: str
    probabilities: tuple[float, float, float]
    outcome: int  # 0 home, 1 draw, 2 away

    def __post_init__(self):
        if not isinstance(self.fixture_id, str) or not self.fixture_id.strip():
            raise ValueError('fixture_id_required')
        date.fromisoformat(self.match_date)
        if not isinstance(self.outcome, int) or self.outcome not in (0, 1, 2):
            raise ValueError('invalid_outcome')
        _validated(self.probabilities)


def _validated(value):
    probs = np.asarray(value, dtype=float)
    if (probs.shape != (3,) or not np.isfinite(probs).all()
            or (probs <= 0).any() or not np.isclose(probs.sum(), 1.0, atol=1e-10, rtol=0)):
        raise ValueError('invalid_probability_mass')
    return probs


def temperature_scale(probabilities, temperature: float) -> tuple[float, float, float]:
    probs = _validated(probabilities)
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('invalid_temperature')
    logs = np.log(probs) / temperature
    logs -= logs.max()
    weights = np.exp(logs)
    return tuple(float(x) for x in weights / weights.sum())


def _fingerprint(records: Sequence[ForecastObservation]):
    payload = [(r.fixture_id, r.match_date, r.probabilities, r.outcome) for r in records]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()).hexdigest()


def _chronological(records: Sequence[ForecastObservation]):
    if not records:
        raise ValueError('calibration_data_empty')
    if len({r.fixture_id for r in records}) != len(records):
        raise ValueError('duplicate_fixture_in_calibration')
    if list(records) != sorted(records, key=lambda r: (r.match_date, r.fixture_id)):
        raise ValueError('calibration_data_not_chronological')


def _metrics(records: Sequence[ForecastObservation], probabilities):
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray([r.outcome for r in records], dtype=int)
    if len(y) != len(p) or p.shape != (len(y), 3):
        raise ValueError('evaluation_length_mismatch')
    return {'n': len(y),
            'log_loss_1x2': float(-np.log(np.maximum(p[np.arange(len(y)), y], 1e-300)).mean()),
            'brier_1x2': float(np.sum((p - np.eye(3)[y]) ** 2, axis=1).mean())}


def _temporal_bootstrap_effect(rows, before, after, *, resamples=2000, seed=20261016):
    """Paired circular-block uncertainty over chronological fixture-day clusters.

    Observations on the same date stay in the same block; this estimates
    variability under dependence but cannot establish multi-season stability.
    """
    grouped = []
    for index, row in enumerate(rows):
        if not grouped or grouped[-1][0] != row.match_date:
            grouped.append((row.match_date, []))
        grouped[-1][1].append(index)
    n_days = len(grouped)
    block_days = max(2, round(n_days ** .5))
    rng = np.random.default_rng(seed)
    metrics = {}
    y = np.array([r.outcome for r in rows])
    indices = np.arange(len(rows))
    losses = {
        'log_loss_1x2': (-np.log(np.maximum(before[indices,y],1e-300)),
                          -np.log(np.maximum(after[indices,y],1e-300))),
        'brier_1x2': (np.sum((before-np.eye(3)[y])**2,axis=1),
                     np.sum((after-np.eye(3)[y])**2,axis=1)),
    }
    blocks = [np.asarray(members,dtype=int) for _,members in grouped]
    for name,(a,b) in losses.items():
        delta = b-a
        observed = float(delta.mean())
        samples=[]
        for _ in range(resamples):
            selected=[]
            while len(selected)<n_days:
                start=int(rng.integers(0,n_days))
                selected.extend((start+i)%n_days for i in range(block_days))
            sample_indices=np.concatenate([blocks[i] for i in selected[:n_days]])
            samples.append(float(delta[sample_indices].mean()))
        low, high=np.quantile(samples,[.025,.975])
        metrics[name]={'challenger_minus_baseline':observed,
                       'paired_block_bootstrap_95ci':[float(low),float(high)],
                       'difference_sign_established':bool(high<0 or low>0)}
    return {'block_length_days':block_days,'resamples':resamples,'unique_fixture_dates':n_days,
            'metrics':metrics,'note':'single-season retrospective; intervals are exploratory'}


def evaluate_calibration_challenger(
        calibration_rows: Sequence[ForecastObservation],
        test_rows: Sequence[ForecastObservation], *, minimum_history: int = 30):
    """Fit on calibration only and evaluate on a strictly later untouched test.

    A performance increase here does not automatically promote the calibrator.
    The exact baseline forecast model must be held fixed on both partitions.
    """
    calibration_rows, test_rows = list(calibration_rows), list(test_rows)
    _chronological(calibration_rows)
    _chronological(test_rows)
    if len(calibration_rows) < max(20, minimum_history):
        raise ValueError('insufficient_calibration_sample')
    if date.fromisoformat(calibration_rows[-1].match_date) >= date.fromisoformat(test_rows[0].match_date):
        raise ValueError('calibration_overlaps_test')
    if {r.fixture_id for r in calibration_rows} & {r.fixture_id for r in test_rows}:
        raise ValueError('calibration_fixture_overlap')
    cp = np.array([r.probabilities for r in calibration_rows])
    outcomes = np.asarray([r.outcome for r in calibration_rows])
    logs = np.log(cp)

    def loss(log_temperature):
        temperature = float(np.exp(log_temperature))
        a = logs / temperature
        a -= a.max(axis=1, keepdims=True)
        log_softmax = a - np.log(np.exp(a).sum(axis=1, keepdims=True))
        return float(-log_softmax[np.arange(len(outcomes)), outcomes].mean())

    result = minimize_scalar(loss, bounds=(math.log(0.25), math.log(4)), method='bounded',
                             options={'xatol': 1e-10})
    if not result.success or not math.isfinite(result.fun):
        raise ValueError('calibration_optimizer_failed')
    temperature = float(np.exp(result.x))
    before = [r.probabilities for r in test_rows]
    after = [temperature_scale(r.probabilities, temperature) for r in test_rows]
    before_arr, after_arr = np.asarray(before), np.asarray(after)
    return {'schema_version': '1.0', 'mode': 'retrospective_challenger_only',
            'method': 'temperature_scaling_multiclass', 'temperature': temperature,
            'calibration_n': len(calibration_rows), 'test_n': len(test_rows),
            'calibration_last_date': calibration_rows[-1].match_date,
            'test_first_date': test_rows[0].match_date,
            'calibration_sha256': _fingerprint(calibration_rows),
            'test_sha256': _fingerprint(test_rows),
            'baseline': _metrics(test_rows, before),
            'challenger': _metrics(test_rows, after),
            'paired_uncertainty': _temporal_bootstrap_effect(test_rows, before_arr, after_arr),
            'calibration_training_log_loss': loss(result.x),
            'not_auto_promoted': True,
            'scope': '1X2 only; does not transform or override goal-score matrices',
            'evidence_limit': 'retrospective archive, not point-in-time live operational validation'}
