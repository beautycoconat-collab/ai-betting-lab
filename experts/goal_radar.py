"""Disabled-live goal radar baseline for timestamped interval replay.

Fits a homogeneous Poisson rate, not an in-play pressure/shot model. There is
no live adapter or activation switch. Never uses this baseline for portfolios.
"""
import math
from datetime import timedelta
from typing import Literal
from pydantic import AwareDatetime, Field, model_validator
from scipy.stats import chi2
from foundation.contracts import Contract
from .football import digest
from .research import aware


class Interval(Contract):
    fixture_id: str = Field(min_length=1)
    start_minute: float = Field(ge=0,lt=90)
    end_minute: float = Field(gt=0,le=90)
    goals: int = Field(ge=0,le=30,strict=True)
    ended_at: AwareDatetime
    observed_at: AwareDatetime
    evidence_id: str = Field(min_length=1)
    target: Literal['regulation90']

    @model_validator(mode='after')
    def times(self):
        if self.end_minute<=self.start_minute or self.observed_at<self.ended_at:
            raise ValueError('invalid_interval_or_observation')
        return self


class ReplayState(Contract):
    fixture_id: str = Field(min_length=1)
    minute: float = Field(ge=0,lt=90)
    home_goals: int = Field(ge=0,le=30,strict=True)
    away_goals: int = Field(ge=0,le=30,strict=True)
    red_cards: int = Field(ge=0,le=10,strict=True)
    observed_at: AwareDatetime
    as_of: AwareDatetime
    evidence_id: str = Field(min_length=1)
    mode: Literal['replay','live']


class GoalRadar:
    def fit(self, intervals, as_of):
        rows=[Interval.model_validate(r) for r in intervals];cut=aware(as_of)
        if len(rows)<30:
            raise ValueError('insufficient_training_intervals')
        by_fixture={}
        for r in rows:
            if r.observed_at>cut:
                raise ValueError('future_training_label')
            by_fixture.setdefault(r.fixture_id,[]).append(r)
        for values in by_fixture.values():
            values.sort(key=lambda r:r.start_minute)
            if any(a.end_minute>b.start_minute for a,b in zip(values,values[1:])):
                raise ValueError('overlapping_training_intervals')
        self.exposure=sum(r.end_minute-r.start_minute for r in rows)
        self.goals=sum(r.goals for r in rows)
        self.rate=self.goals/self.exposure
        self.training_end=cut;self.training_fixtures=set(by_fixture)
        self.version=digest([r.model_dump(mode='json') for r in rows])
        return self

    def predict(self, value, horizon_minutes=10):
        s=ReplayState.model_validate(value)
        if s.mode=='live':
            return dict(schema_version='1.0',status='BLOCKED',probability=None,
                        reason='live_source_and_calibration_acceptance_missing')
        if not hasattr(self,'rate'):
            raise ValueError('model_not_fitted')
        if s.fixture_id in self.training_fixtures or s.as_of<=self.training_end:
            raise ValueError('training_replay_overlap')
        age=(s.as_of-s.observed_at).total_seconds()
        if age<0:raise ValueError('future_live_observation')
        if age>30 or s.red_cards:
            return dict(schema_version='1.0',status='insufficient_data',probability=None,
                        reason='stale_observation' if age>30 else 'red_card_effect_not_modelled')
        if type(horizon_minutes) not in (int,float) or not math.isfinite(horizon_minutes) or not 0<horizon_minutes<=90:
            raise ValueError('invalid_horizon')
        horizon=min(float(horizon_minutes),90-s.minute)
        low=0 if self.goals==0 else chi2.ppf(.025,2*self.goals)/(2*self.exposure)
        high=chi2.ppf(.975,2*(self.goals+1))/(2*self.exposure)
        return dict(schema_version='1.0',status='PARTIAL',mode='historical_replay',
            probability=-math.expm1(-self.rate*horizon),
            parameter_interval_95=[-math.expm1(-low*horizon),-math.expm1(-high*horizon)],
            horizon_minutes=horizon,model_version=self.version,
            evidence_ids=[s.evidence_id],data_age_seconds=age,
            assumption='homogeneous Poisson; no pressure, lineup, shot or score-state adjustment',
            calibration_status='not_validated',execution_enabled=False)

    def evaluate(self, cases, evaluated_at):
        """Score labelled replay only; labels must exist by evaluation time."""
        at=aware(evaluated_at); losses=[];briers=[];alarms=[];seen=set();fixtures=set()
        for case in cases:
            state=ReplayState.model_validate(case['state'])
            key=(state.fixture_id,state.as_of,case['horizon_minutes'])
            if key in seen:raise ValueError('duplicate_replay_evaluation')
            seen.add(key)
            result=self.predict(state,case['horizon_minutes'])
            if state.mode!='replay' or result.get('probability') is None:
                raise ValueError('unscorable_replay')
            label_time=aware(case['outcome_observed_at'])
            if label_time>at or label_time<state.as_of+timedelta(minutes=result['horizon_minutes']):
                raise ValueError('future_or_premature_replay_label')
            y=case['goal_in_horizon']
            if type(y) is not bool:raise ValueError('boolean_goal_label_required')
            p=result['probability'];briers.append((p-int(y))**2)
            losses.append(-math.log(max(p if y else 1-p,1e-15)))
            if p>=.5:alarms.append(not y)
            fixtures.add(state.fixture_id)
        if not losses:raise ValueError('empty_replay_evaluation')
        return dict(schema_version='1.0',mode='historical_replay',cases=len(losses),
            fixtures=len(fixtures),brier=sum(briers)/len(briers),log_loss=sum(losses)/len(losses),
            false_alarm_fraction=sum(alarms)/len(alarms) if alarms else None,
            alarm_threshold=.5,live_validation=False,execution_enabled=False)
