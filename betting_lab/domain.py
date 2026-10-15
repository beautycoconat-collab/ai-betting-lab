from dataclasses import dataclass, asdict
from datetime import datetime, timezone, date
import hashlib
import json

UTC = timezone.utc

def utcnow():
    return datetime.now(UTC).isoformat()

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def aware(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timezone_missing')
    return dt.astimezone(UTC).isoformat()

def identifier(value):
    if type(value) not in (int, str) or not str(value).strip():
        raise ValueError('invalid_id')
    return str(value)

def name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing_team_name')
    return value.strip()

def goals(value):
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError('invalid_score')
    return value

@dataclass(frozen=True)
class Match:
    source: str
    source_match_id: str
    competition: str
    season: int
    home_key: str
    away_key: str
    home_name: str
    away_name: str
    match_date: str
    kickoff_at: str | None
    status: str
    home_goals: int | None
    away_goals: int | None
    source_updated_at: str | None
    source_updated_raw: str | None
    def __post_init__(self):
        date.fromisoformat(self.match_date)
        if self.home_key == self.away_key:
            raise ValueError('same_team')
        if self.kickoff_at:
            aware(self.kickoff_at)
        if self.status not in ('finished', 'scheduled', 'unknown'):
            raise ValueError('invalid_status')
        if (self.home_goals is None) != (self.away_goals is None):
            raise ValueError('partial_score')
        if self.status == 'finished' and self.home_goals is None:
            raise ValueError('finished_without_score')
        if self.home_goals is not None:
            goals(self.home_goals); goals(self.away_goals)
    def to_dict(self):
        return asdict(self)
