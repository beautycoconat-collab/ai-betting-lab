"""Bounded display contract; neither publication consent nor source verification."""
from typing import Annotated
from pydantic import Field, model_validator
from foundation.contracts import Contract

Probability = Annotated[float, Field(ge=0, le=1, strict=True)]

class ScoreLine(Contract):
    score: str = Field(pattern=r'^\d{1,2}-\d{1,2}$')
    probability: Probability

class ModelSummary(Contract):
    p_1x2: tuple[Probability, Probability, Probability]
    top_scores: list[ScoreLine] = Field(min_length=1, max_length=5)
    outside_grid_probability: Probability
    training_end: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    model_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def mass(self):
        from datetime import date
        date.fromisoformat(self.training_end)
        if abs(sum(self.p_1x2)-1) > 1e-8:
            raise ValueError('invalid_outcome_mass')
        if len({s.score for s in self.top_scores}) != len(self.top_scores):
            raise ValueError('duplicate_score')
        if sum(s.probability for s in self.top_scores) > 1+1e-8:
            raise ValueError('invalid_score_mass')
        return self


def summarize(distribution, training_end, version):
    """Keep only display fields; grids/raw source bodies stay out of the feed."""
    d = distribution
    return ModelSummary(schema_version='1.0', p_1x2=d['p_1x2'],
        top_scores=[ScoreLine(schema_version='1.0', **s) for s in d['top_scores']],
        outside_grid_probability=d['outside_grid_probability'],
        training_end=training_end, model_sha256=version).model_dump(mode='json')
