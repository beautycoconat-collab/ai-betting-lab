"""Strict wire contracts. Syntax validation never substitutes for evidence checks."""
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator

class Role(str, Enum):
    coordinator='coordinator'
    source_hunter='source_hunter'
    data_validator='data_validator'
    lineup_researcher='lineup_researcher'
    external_researcher='external_researcher'
    team_strength='team_strength'
    score_engine='score_engine'
    market_specialist='market_specialist'
    synthesizer='synthesizer'
    red_team='red_team'
    scientific_referee='scientific_referee'
    odds_analyst='odds_analyst'
    risk_manager='risk_manager'
    learning_auditor='learning_auditor'

Target = Literal['regulation90','final_including_extra_time','provider_final_unknown']
Quality = Literal['verified','unknown','conflicting','unverified']
SourceStatus = Literal['approved','conditional','blocked','pending_review','disabled']

class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    schema_version: Literal['1.0']

class AgentMessage(Contract):
    message_id: UUID
    agent_run_id: UUID
    fixture_id: UUID
    agent_role: Role
    created_at: AwareDatetime
    input_snapshot_ids: list[str] = Field(min_length=1, max_length=100)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=100)
    model_version_id: UUID | None = None
    issue_type: Literal['lineup_uncertainty','source_conflict','data_leakage','identity_error','low_sample','model_disagreement','overconfidence','shared_upstream','coupon_dependency','validation']
    severity: Literal['low','medium','high','critical']
    requested_action: Literal['review','scenario_analysis','recalculate','quarantine','abstain']
    status: Literal['pending_review']
    numeric_override: None
    note: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def unique_references(self):
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or len(set(self.input_snapshot_ids)) != len(self.input_snapshot_ids):
            raise ValueError('duplicate_reference')
        return self

class Evidence(Contract):
    evidence_id: UUID
    fixture_id: UUID
    snapshot_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128)
    source_url: str = Field(pattern=r'^https://', max_length=2000)
    observed_at: AwareDatetime
    published_at: AwareDatetime | None = None
    quality: Quality
    score_target: Target
    claim: str = Field(min_length=1, max_length=2000)

    @model_validator(mode='after')
    def publication_time(self):
        if self.published_at and self.published_at > self.observed_at:
            raise ValueError('future_publication')
        return self

class ReviewDecision(Contract):
    decision_id: UUID
    agent_run_id: UUID
    fixture_id: UUID
    agent_role: Literal['scientific_referee']
    created_at: AwareDatetime
    finding_id: UUID
    round_no: int = Field(ge=1, le=2, strict=True)
    status: Literal['approved','needs_reanalysis','insufficient_evidence','rejected','abstain']
    reason: str = Field(min_length=1, max_length=2000)
    risk_action: Literal['wait','skip']
    numeric_override: None

class JobRequest(Contract):
    idempotency_key: str = Field(min_length=8, max_length=200)
    kind: Literal['collect','validate','model','red_team','referee','reanalysis','save_prediction','settle']
    fixture_id: UUID | None = None
    max_attempts: int = Field(default=3, ge=1, le=5, strict=True)
    timeout_seconds: int = Field(default=300, ge=1, le=3600, strict=True)

class UnsupportedMarket(Contract):
    market: str
    status: Literal['unsupported','insufficient_data']
    probability: None
    reason: str

def normalized_status(old_status: str) -> str:
    if old_status in ('approved','conditional','blocked','pending_review','disabled'):
        return old_status
    if old_status == 'pending' or old_status.startswith('pending_'):
        return 'pending_review'
    return 'disabled'

def utcnow():
    return datetime.now(timezone.utc).isoformat()
