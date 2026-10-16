"""Motor A: wrappers reuse the existing persistent queue and collection budget."""
from datetime import datetime
from zoneinfo import ZoneInfo
from engine.adapters import ADAPTERS
from .contracts import Fixture, Claim, ResearchResult


def aware(value):
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timezone_required')
    return value


def approved(policy, at):
    day = aware(at).date().isoformat()
    return (policy.get('status') == 'approved'
            and policy.get('reviewed_at', '9999') <= day <= policy.get('review_expires', '')
            and bool(policy.get('license')) and bool(policy.get('terms_url')))


class Coordinator:
    def __init__(self, runtime):
        self.runtime = runtime

    def plan(self, fixtures, day, evidence_ready=()):
        fixtures = [Fixture.model_validate(f) for f in fixtures]
        if len({f.id for f in fixtures}) != len(fixtures):
            raise ValueError('duplicate_fixture')
        now = aware(self.runtime.clock())
        tasks, deferred = {}, {}
        ready = {str(x) for x in evidence_ready}
        for f in sorted(fixtures, key=lambda f: f.kickoff_at):
            fid = str(f.id)
            if f.kickoff_at.astimezone(ZoneInfo('Europe/Istanbul')).date() != day:
                continue
            if now >= f.kickoff_at:
                deferred[fid] = 'kickoff_passed'
                continue
            old = self.runtime.db.execute('SELECT * FROM f_fixtures WHERE id=?', (fid,)).fetchone()
            if old:
                if (aware(old['kickoff_at']), old['target'], old['home'], old['away']) != (f.kickoff_at, f.target, f.home, f.away):
                    raise ValueError('fixture_identity_conflict')
            else:
                self.runtime.fixture(fid, f.kickoff_at.isoformat(), f.target, f.home, f.away)
            kinds = ['collect', 'validate']
            if fid in ready:
                kinds += ['model', 'red_team', 'referee', 'save_prediction']
            else:
                deferred[fid] = 'evidence_not_ready'
            previous = []
            tasks[fid] = {}
            for kind in kinds:
                task = self.runtime.enqueue(dict(schema_version='1.0', fixture_id=fid, kind=kind,
                    idempotency_key=f'{day}:{fid}:{kind}'), depends_on=previous)
                tasks[fid][kind] = task
                previous = [task]
        return {'schema_version': '1.0', 'task_ids': tasks, 'deferred': deferred}


class SourceHunter:
    def __init__(self, queue):
        self.queue = queue

    def inspect(self, at):
        return {sid: {'status': 'ready' if approved(p, at) and sid in ADAPTERS else 'blocked',
            'adapter_available': sid in ADAPTERS, 'license': p.get('license'),
            'terms_url': p.get('terms_url'), 'coverage': p.get('coverage'),
            'quota_basis': p.get('quota_basis'), 'review_expires': p.get('review_expires')}
            for sid, p in self.queue.registry.items()}

    def schedule(self, source, kind, params, at, cycle=None):
        if self.inspect(at).get(source, {}).get('status') != 'ready':
            raise ValueError('source_not_approved_or_no_adapter')
        return self.queue.enqueue(source, kind, params, now=aware(at).isoformat(), cycle=cycle)

    def collect_one(self, **kwargs):
        return self.queue.work_one(**kwargs)


class DataValidator:
    def __init__(self, registry):
        self.registry = registry

    def validate(self, fixture, claims, as_of, snapshots):
        f, at = Fixture.model_validate(fixture), aware(as_of)
        if at >= f.kickoff_at:
            raise ValueError('kickoff_passed')
        claims = [Claim.model_validate(c) for c in claims]
        if len({c.id for c in claims}) != len(claims):
            raise ValueError('duplicate_claim')
        good, bad = {}, {}
        for c in claims:
            s = snapshots.get(c.snapshot_id, {})
            try:
                snapshot_time = aware(s['observed_at'])
            except (ValueError, TypeError, AttributeError, KeyError):
                snapshot_time = None
            reason = None
            if c.fixture_id != f.id or c.target != f.target:
                reason = 'identity_or_target_mismatch'
            elif not approved(self.registry.get(c.source_id, {}), at):
                reason = 'source_not_approved'
            elif (s.get('source_id'), s.get('source_url')) != (c.source_id, c.source_url) or not s.get('observed_at'):
                reason = 'missing_or_mismatched_provenance'
            elif snapshot_time != c.observed_at:
                reason = 'observation_time_mismatch'
            elif c.observed_at > at or (c.published_at and c.published_at > c.observed_at):
                reason = 'future_information'
            elif c.quality != 'verified' or c.published_at is None:
                reason = c.quality if c.quality != 'verified' else 'unverified_publication'
            if reason:
                bad[c.id] = reason
            else:
                good[c.id] = c
        groups = {}
        for c in good.values():
            groups.setdefault((c.topic, c.subject), []).append(c)
        for group in groups.values():
            if len({c.value for c in group}) > 1:
                for c in group:
                    bad[c.id] = 'conflicting'
                    good.pop(c.id)
        independent = {}
        for c in good.values():
            independent.setdefault(c.upstream or 'unknown_upstream', []).append(c.id)
        return ResearchResult(schema_version='1.0', status='ready' if good and not bad else 'partial' if good else 'blocked',
            accepted_ids=sorted(good), quarantined=bad, independence_groups=independent)


class LineupResearcher:
    required_topics = {'lineup', 'injury', 'suspension', 'tactics', 'rest'}

    def __init__(self, registry):
        self.validator = DataValidator(registry)

    def research(self, fixture, claims, as_of, snapshots):
        claims = [Claim.model_validate(c) for c in claims]
        result = self.validator.validate(fixture, claims, as_of, snapshots)
        topics = {c.topic for c in claims if c.id in result.accepted_ids}
        body = result.model_dump()
        body['missing_topics'] = sorted(self.required_topics-topics)
        if body['missing_topics'] and result.status == 'ready':
            body['status'] = 'partial'
        return ResearchResult.model_validate(body)


class ExternalResearcher:
    def __init__(self, queue):
        self.queue = queue

    def availability(self, at):
        permitted = [s for s, p in self.queue.registry.items()
                     if approved(p, at) and p.get('external_predictions_allowed')]
        return {'status': 'partial' if permitted else 'blocked', 'permitted_sources': permitted,
                'ensemble_weight': 0, 'live_adapter_verified': False}

    def ingest(self, source, payload, **kwargs):
        from engine.external import ingest
        from foundation.contracts import utcnow
        clock = kwargs.get('clock', utcnow)
        if not approved(self.queue.registry.get(source, {}), clock()) or not payload.get('published_at'):
            raise ValueError('external_publication_or_permission_unverified')
        return ingest(self.queue.db, source, payload, self.queue.registry, **kwargs)
