"""Deterministic, purely virtual settlement. No wallet mutations or wager submission.

Only a verified 90-minute final may resolve supported full-time markets.
Cancelled/abandoned events require explicit provider rules and remain blocked.
"""
import math
from typing import Literal
from pydantic import Field, model_validator
from foundation.contracts import Contract


class Pick(Contract):
    market: Literal['1X2', 'over', 'under', 'btts_yes', 'btts_no',
                    'home_over', 'home_under', 'away_over', 'away_under',
                    'home_handicap']
    selection: Literal['1', 'X', '2'] | None = None
    line: float | None = None
    score_target: Literal['regulation90'] = 'regulation90'

    @model_validator(mode='after')
    def check_contract(self):
        if self.market == '1X2':
            if self.selection not in ('1', 'X', '2') or self.line is not None:
                raise ValueError('invalid_1x2_selection')
        elif self.market in ('btts_yes', 'btts_no'):
            if self.selection is not None or self.line is not None:
                raise ValueError('invalid_btts_spec')
        else:
            if self.selection is not None or self.line is None or not math.isfinite(self.line):
                raise ValueError('market_line_required')
            if not 0 <= abs(self.line) <= 20 or self.line * 2 != int(self.line * 2):
                raise ValueError('unsupported_market_line')
        return self


class FinalScore(Contract):
    status: Literal['final', 'pending', 'postponed', 'cancelled', 'abandoned']
    home: int | None = Field(default=None, ge=0, le=100)
    away: int | None = Field(default=None, ge=0, le=100)
    target: Literal['regulation90', 'final_including_extra_time', 'provider_final_unknown']

    @model_validator(mode='after')
    def check_result(self):
        if self.status == 'final':
            if self.home is None or self.away is None:
                raise ValueError('incomplete_final_score')
        elif self.home is not None or self.away is not None:
            raise ValueError('nonfinal_score_is_not_result')
        return self


def settle_pick(pick, result):
    """Return a verdict, not a virtual transaction or invented provider rule."""
    p, r = Pick.model_validate(pick), FinalScore.model_validate(result)
    if r.status in ('pending', 'postponed'):
        return {'status': 'pending', 'reason': 'official_final_required'}
    if r.status in ('cancelled', 'abandoned'):
        return {'status': 'blocked', 'reason': 'provider_void_rules_required'}
    if p.score_target != r.target:
        return {'status': 'blocked', 'reason': 'score_target_mismatch'}
    h, a = r.home, r.away
    if p.market == '1X2':
        winner = '1' if h > a else '2' if h < a else 'X'
        verdict = 'won' if p.selection == winner else 'lost'
    elif p.market == 'btts_yes':
        verdict = 'won' if h > 0 and a > 0 else 'lost'
    elif p.market == 'btts_no':
        verdict = 'won' if h == 0 or a == 0 else 'lost'
    else:
        comparison = (h + a if p.market in ('over', 'under') else
                      h if p.market.startswith('home_') and p.market != 'home_handicap' else
                      a if p.market.startswith('away_') else h - a)
        margin = comparison + p.line if p.market == 'home_handicap' else comparison - p.line
        if p.market in ('under', 'home_under', 'away_under'):
            margin = -margin
        verdict = 'push' if abs(margin) < 1e-12 else 'won' if margin > 0 else 'lost'
    return {'status': verdict, 'reason': 'verified_regulation90'}
