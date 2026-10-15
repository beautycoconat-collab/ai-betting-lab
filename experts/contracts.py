"""Versioned expert inputs. Source evidence still requires semantic verification."""
from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, model_validator
from foundation.contracts import Contract, Target, Quality


class Fixture(Contract):
    id: UUID
    home: str = Field(min_length=1)
    away: str = Field(min_length=1)
    competition: str = Field(min_length=1)
    season: str = Field(min_length=1)
    kickoff_at: AwareDatetime
    target: Target
    neutral: bool = Field(strict=True)

    @model_validator(mode='after')
    def teams_differ(self):
        if self.home == self.away:
            raise ValueError('same_team')
        return self


class Claim(Contract):
    id: str = Field(min_length=1)
    fixture_id: UUID
    source_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    source_url: str = Field(pattern=r'^https://')
    observed_at: AwareDatetime
    published_at: AwareDatetime | None
    target: Target
    quality: Quality
    topic: Literal['lineup', 'injury', 'suspension', 'tactics', 'rest', 'weather', 'fixture']
    subject: str = Field(min_length=1)
    value: str = Field(min_length=1, max_length=2000)
    upstream: str | None = None


class ResearchResult(Contract):
    status: Literal['ready', 'partial', 'blocked']
    accepted_ids: list[str]
    quarantined: dict[str, str]
    independence_groups: dict[str, list[str]]
    missing_topics: list[str] = Field(default_factory=list)
    numeric_override: None = None


class Finding(Contract):
    issue_type: Literal['data_leakage', 'lineup_uncertainty', 'low_sample', 'model_disagreement', 'shared_upstream', 'overconfidence', 'source_conflict', 'identity_error']
    severity: Literal['medium', 'high', 'critical']
    evidence_ids: list[str] = Field(min_length=1)
    requested_action: Literal['review', 'recalculate', 'abstain']
    numeric_override: None = None


class AuditContext(Contract):
    fixture_id: UUID
    as_of: AwareDatetime
    kickoff_at: AwareDatetime
    training_end: date
    mode: Literal['prematch', 'retrospective']
    observations: dict[str, AwareDatetime]
    lineup_evidence_ids: list[str]
    upstream_groups: dict[str, list[str]]
    training_matches: int = Field(ge=1, strict=True)
    probabilities: tuple[float, float, float]
    model_spread: float = Field(ge=0, le=1)
    prediction_id: str = Field(min_length=1)

    @model_validator(mode='after')
    def references_and_mass(self):
        if min(self.probabilities) < 0 or abs(sum(self.probabilities)-1) > 1e-8:
            raise ValueError('invalid_probability_mass')
        references = self.lineup_evidence_ids + [i for g in self.upstream_groups.values() for i in g]
        if not set(references) <= set(self.observations):
            raise ValueError('unknown_evidence')
        return self


class Verdict(Contract):
    status: Literal['approved', 'needs_reanalysis', 'insufficient_evidence', 'rejected', 'abstain']
    risk_action: Literal['wait', 'skip']
    round_no: int = Field(ge=1, le=2, strict=True)
    reasons: list[str]
    numeric_override: None = None


class Odds(Contract):
    fixture_id: UUID
    source_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    observed_at: AwareDatetime
    published_at: AwareDatetime
    target: Target
    market: Literal['1X2']
    prices: tuple[float, float, float]

    @model_validator(mode='after')
    def valid_prices(self):
        if min(self.prices) <= 1 or self.published_at > self.observed_at:
            raise ValueError('invalid_odds')
        return self
