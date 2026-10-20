"""Motor D. Research/experiments never spend money; prospective execution disabled."""
import json
import math
from datetime import timedelta
from typing import Literal
import numpy as np
from pydantic import Field
from foundation.contracts import Contract
from .contracts import Fixture, Odds, Verdict
from .research import aware, approved


class RiskState(Contract):
    balance_kurus: int = Field(ge=0, strict=True)
    spent_today_kurus: int = Field(ge=0, strict=True)
    open_risk_kurus: int = Field(ge=0, strict=True)
    minimum_coupon_kurus: int = Field(default=5000, ge=0, strict=True)


class RiskDecision(Contract):
    action: Literal['wait', 'skip']
    reason: str
    stake_kurus: Literal[0] = 0
    execution_enabled: Literal[False] = False


class OddsAnalyst:
    def analyze(self, fixture, odds, probabilities, as_of, registry, max_age_seconds=300):
        f, o, at = Fixture.model_validate(fixture), Odds.model_validate(odds), aware(as_of)
        p = np.asarray(probabilities, float)
        if p.shape != (3,) or not np.isfinite(p).all() or p.min() < 0 or abs(p.sum()-1) > 1e-8:
            raise ValueError('invalid_probability_mass')
        if f.id != o.fixture_id or f.target != o.target:
            raise ValueError('odds_fixture_or_target_mismatch')
        policy = registry.get(o.source_id, {})
        if not approved(policy, at) or not policy.get('odds_allowed'):
            raise ValueError('odds_permission_unverified')
        if at >= f.kickoff_at or any(not 0 <= (at-t).total_seconds() <= max_age_seconds for t in (o.observed_at, o.published_at)):
            raise ValueError('stale_or_future_odds')
        implied = 1/np.array(o.prices)
        return {'overround': float(implied.sum()-1), 'no_vig_method': 'proportional',
                'no_vig_probabilities': (implied/implied.sum()).tolist(),
                'expected_return': (p*np.array(o.prices)-1).tolist()}

    def clv(self, entry, closing, kickoff_at, window_seconds=300):
        if closing is None:
            return {'status': 'insufficient_data', 'price_clv': None}
        a, b, kickoff = Odds.model_validate(entry), Odds.model_validate(closing), aware(kickoff_at)
        if (a.fixture_id, a.target, a.market, a.source_id) != (b.fixture_id, b.target, b.market, b.source_id):
            raise ValueError('incomparable_closing_odds')
        if not a.observed_at <= b.observed_at < kickoff or any(not 0 < (kickoff-t).total_seconds() <= window_seconds for t in (b.observed_at, b.published_at)):
            raise ValueError('closing_time_invalid')
        return {'status': 'available', 'price_clv': [x/y-1 for x, y in zip(a.prices, b.prices)],
                'definition': 'entry_price/closing_price-1; not realized ROI'}


class RiskManager:
    def decide(self, state, verdict, expected_return=None, uncertainty=1.0):
        s, v = RiskState.model_validate(state), Verdict.model_validate(verdict)
        if not math.isfinite(uncertainty) or not 0 <= uncertainty <= 1:
            raise ValueError('invalid_uncertainty')
        if expected_return is not None and not math.isfinite(expected_return):
            raise ValueError('invalid_edge')
        ceiling = max(0, min(10000, 10000-s.spent_today_kurus, s.balance_kurus,
                             10000-s.open_risk_kurus, s.balance_kurus//100))
        action, reason = 'wait', 'security_and_live_data_acceptance_pending'
        if v.status in ('abstain', 'rejected'):
            action, reason = 'skip', 'review_blocked'
        elif v.status != 'approved':
            reason = 'review_pending'
        elif expected_return is None:
            reason = 'real_odds_missing'
        elif expected_return <= 0 or uncertainty > .2:
            action, reason = 'skip', 'edge_or_uncertainty'
        elif ceiling == 0 or s.minimum_coupon_kurus > ceiling:
            action, reason = 'skip', 'minimum_exceeds_risk_limit'
        return RiskDecision(schema_version='1.0', action=action, reason=reason)


class PortfolioJournal:
    def __init__(self, runtime):
        self.runtime = runtime

    def record(self, fixture, decision, key, as_of, mode):
        f, d, at = Fixture.model_validate(fixture), RiskDecision.model_validate(decision), aware(as_of)
        if mode != 'prospective':
            raise ValueError('historical_experiment_not_portfolio')
        payload = {'fixture': f.model_dump(mode='json'), 'decision': d.model_dump(mode='json'),
                   'as_of': at.isoformat(), 'mode': mode}
        with self.runtime.transaction():
            rows = [json.loads(r[0]) for r in self.runtime.db.execute("SELECT body FROM f_audit WHERE event='portfolio_decision'")]
            prior = next((r for r in rows if r['key'] == key), None)
            if prior:
                if prior['payload'] != payload:
                    raise ValueError('idempotency_conflict')
                return prior
            now = aware(self.runtime.clock())
            if not 0 <= (now-at).total_seconds() <= 5 or now >= f.kickoff_at:
                raise ValueError('not_realtime')
            record = {'key': key, 'payload': payload}
            self.runtime.audit('portfolio_decision', record)
            return record


class LearningAuditor:
    def evaluate(self, distributions, results):
        if not distributions or len(distributions) != len(results):
            raise ValueError('evaluation_length')
        brier, logloss, scoreloss, scorebrier, calibration = [], [], [], [], [[] for _ in range(10)]
        score_calibration = [[] for _ in range(10)]
        for d, (h, a) in zip(distributions, results):
            # PMF validates integer nonnegative labels.
            actual = d.probability(h, a)
            outcome = 0 if h > a else 1 if h == a else 2
            p, y = d.outcome(), np.eye(3)[outcome]
            brier.append(float(np.sum((p-y)**2)))
            logloss.append(-math.log(max(float(p[outcome]), 1e-300)))
            scoreloss.append(-math.log(max(actual, 1e-300)))
            grid, tail = d.grid(100)
            if tail*tail > 1e-24:
                raise ValueError('score_brier_tail_too_large')
            scorebrier.append(float(np.sum(grid**2)+1-2*actual))
            top_h, top_a = np.unravel_index(grid.argmax(), grid.shape)
            top_p = float(grid[top_h, top_a])
            score_calibration[min(9, int(top_p*10))].append((top_p, float((h, a) == (top_h, top_a))))
            for q, truth in zip(p, y):
                calibration[min(9, int(q*10))].append((float(q), float(truth)))
        return {'n': len(results), 'brier_1x2': float(np.mean(brier)), 'logloss_1x2': float(np.mean(logloss)),
                'score_logloss': float(np.mean(scoreloss)), 'score_brier': float(np.mean(scorebrier)),
                'score_brier_absolute_error_bound': 1e-24,
                'calibration_top_score': [{'n': len(b), 'mean_probability': float(np.mean([p for p, _ in b])) if b else None,
                    'frequency': float(np.mean([y for _, y in b])) if b else None} for b in score_calibration],
                'calibration_1x2': [{'n': len(b), 'mean_probability': float(np.mean([p for p, _ in b])) if b else None,
                    'frequency': float(np.mean([y for _, y in b])) if b else None} for b in calibration]}

    def portfolio(self, settled, mode):
        if mode not in ('prospective', 'historical') or any(r['mode'] != mode for r in settled):
            raise ValueError('mixed_portfolio_modes')
        if len({r['id'] for r in settled}) != len(settled):
            raise ValueError('duplicate_settlement')
        equity = peak = 100000
        spent = profit = maximum = 0
        for r in sorted(settled, key=lambda r: aware(r['settled_at'])):
            if any(type(r[k]) is not int or r[k] < 0 for k in ('stake_kurus', 'payout_kurus')):
                raise ValueError('invalid_settlement_amount')
            spent += r['stake_kurus']
            delta = r['payout_kurus']-r['stake_kurus']
            profit += delta
            equity += delta
            peak = max(peak, equity)
            maximum = max(maximum, (peak-equity)/peak)
        return {'mode': mode, 'realized_roi': profit/spent if spent else None,
                'max_settled_equity_drawdown': maximum, 'open_risk_included': False}

    def windows(self, records, as_of):
        at = aware(as_of)
        times = [aware(r['created_at']) for r in records]
        if any(t > at for t in times):
            raise ValueError('future_record')
        return {days: sum(at-timedelta(days=days) <= t <= at for t in times) for days in (7, 30, 90, 180)}

    def compare(self, champion_losses, challenger_losses):
        a, b = np.asarray(champion_losses, float), np.asarray(challenger_losses, float)
        if a.ndim != 1 or a.shape != b.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('invalid_paired_losses')
        delta = b-a
        rng = np.random.default_rng(20261015)
        samples = [float(rng.choice(delta, len(delta)).mean()) for _ in range(1000)]
        low, high = np.quantile(samples, [.025, .975]).tolist()
        return {'mean_challenger_minus_champion': float(delta.mean()), 'iid_bootstrap_95ci': [low, high],
                'recommendation': 'review' if len(delta) >= 100 and high < 0 else 'retain',
                'auto_promote': False, 'pending': ['temporal block bootstrap', 'multiple-comparison control']}
