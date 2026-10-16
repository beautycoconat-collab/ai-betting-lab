"""Research-only, fail-closed model -> Red Team -> Referee task chain.

No HTTP, external writes, hosted identity, odds, bets or pilot here. Existing
foundation Runtime/Dispatcher own leases and append-only outputs. The same
immutable time-locked input is bound separately to every task; each handler
checks its dependency output and fingerprint instead of trusting task names.
"""
from .contracts import Fixture, Claim, AuditContext, Finding
from .dispatcher import Dispatcher, TaskOutput
from .research import aware, DataValidator
from .football import digest
from .review import RedTeam, ScientificReferee
import numpy as np


KINDS = ('validate', 'model', 'red_team', 'referee')
ROLES = {'validate': 'data_validator', 'model': 'score_engine',
         'red_team': 'red_team', 'referee': 'scientific_referee'}


class ResearchWorkerPipeline:
    def __init__(self, runtime, engine, synthesizer, registry):
        if set(engine.models) != set(synthesizer.models) or any(
            engine.models[k].__dict__ != synthesizer.models[k].__dict__ for k in engine.models
        ):
            raise ValueError('ensemble_engine_version_mismatch')
        self.runtime, self.engine, self.synthesizer = runtime, engine, synthesizer
        self.registry = registry
        self.dispatcher = Dispatcher(runtime, {
            'validate': self._validate,
            'model': self._model,
            'red_team': self._red_team,
            'referee': self._referee,
        })

    def _input(self, job):
        body = self.dispatcher.load_input(job)
        fixture = Fixture.model_validate(body['fixture'])
        if str(fixture.id) != str(job.fixture_id):
            raise ValueError('fixture_identity_mismatch')
        at = aware(body['as_of'])
        if at >= fixture.kickoff_at or at > aware(self.runtime.clock()):
            raise ValueError('invalid_research_cutoff')
        if body['mode'] not in ('retrospective', 'prematch'):
            raise ValueError('invalid_mode')
        if body['mode'] == 'prematch' and (
            self.engine.mode != 'prematch'
            or self.synthesizer.validation_observed_end is None
            or self.synthesizer.validation_observed_end > at
        ):
            raise ValueError('model_not_validated_for_prospective_use')
        return body, fixture, at, digest(body)

    @staticmethod
    def _dependency(deps, kind, fingerprint):
        matches = [d for d in deps.values() if d.data.get('stage') == kind]
        if len(deps) != 1 or len(matches) != 1:
            raise ValueError('missing_or_ambiguous_dependency')
        d = matches[0]
        if d.status != 'ready' or d.data.get('input_hash') != fingerprint:
            raise ValueError('dependency_not_ready_or_input_mismatch')
        return d.data

    def plan(self, fixture, as_of, claims, snapshots, *, mode='retrospective'):
        f, at = Fixture.model_validate(fixture), aware(as_of)
        if at >= f.kickoff_at or at > aware(self.runtime.clock()):
            raise ValueError('invalid_research_cutoff')
        if mode not in ('retrospective', 'prematch'):
            raise ValueError('invalid_mode')
        if mode == 'prematch' and (
            self.engine.mode != 'prematch'
            or self.synthesizer.validation_observed_end is None
            or self.synthesizer.validation_observed_end > at
        ):
            raise ValueError('model_not_validated_for_prospective_use')
        normalized_claims = [Claim.model_validate(c).model_dump(mode='json') for c in claims]
        payload = dict(fixture=f.model_dump(mode='json'), as_of=at.isoformat(),
                       claims=normalized_claims, snapshots=snapshots, mode=mode)
        # Fail early on oversize inputs. No source fetching or inferred evidence.
        from foundation.runtime import canonical
        if len(canonical(payload).encode()) > 65536:
            raise ValueError('input_storage_limit')
        old = self.runtime.db.execute('SELECT * FROM f_fixtures WHERE id=?', (str(f.id),)).fetchone()
        if old:
            if (old['home'], old['away'], old['target'], aware(old['kickoff_at'])) != (
                f.home, f.away, f.target, f.kickoff_at
            ):
                raise ValueError('fixture_identity_conflict')
        else:
            self.runtime.fixture(str(f.id), f.kickoff_at.isoformat(), f.target, f.home, f.away)
        fingerprint = digest(payload)
        tasks, previous = {}, []
        for kind in KINDS:
            key = 'research-v1:' + digest([str(f.id), kind, fingerprint])
            task_id = self.runtime.enqueue(dict(schema_version='1.0', kind=kind,
                fixture_id=str(f.id), idempotency_key=key), depends_on=previous)
            self.dispatcher.bind_input(task_id, payload)
            tasks[kind] = task_id
            previous = [task_id]
        return tasks

    def _validate(self, job, dependencies):
        if dependencies:
            raise ValueError('unexpected_validation_dependencies')
        body, fixture, at, fingerprint = self._input(job)
        report = DataValidator(self.registry).validate(
            fixture, body['claims'], at, body['snapshots'])
        if report.status != 'ready':
            return TaskOutput(schema_version='1.0', status='blocked',
                reason='evidence_not_ready', data=dict(stage='validate', input_hash=fingerprint,
                    verification=report.model_dump(mode='json')))
        return TaskOutput(schema_version='1.0', status='ready', data=dict(
            stage='validate', input_hash=fingerprint,
            verification=report.model_dump(mode='json')))

    def _model(self, job, dependencies):
        body, fixture, at, fingerprint = self._input(job)
        verification = self._dependency(dependencies, 'validate', fingerprint)['verification']
        claims = [Claim.model_validate(c) for c in body['claims']]
        if not verification['accepted_ids'] or verification['quarantined']:
            raise ValueError('evidence_not_clean')
        accepted = set(verification['accepted_ids'])
        if not accepted <= {c.id for c in claims}:
            raise ValueError('accepted_evidence_mismatch')
        numerical = dict(home=fixture.home, away=fixture.away,
                         date=fixture.kickoff_at.date().isoformat(),
                         neutral=fixture.neutral, target=fixture.target)
        if any(m.target != fixture.target or m.training_end >= numerical['date']
               for m in self.engine.models.values()):
            raise ValueError('model_target_or_training_overlap')
        if numerical['date'] <= self.synthesizer.validation_end:
            raise ValueError('fixture_overlaps_validation')
        forecasts = self.engine.forecast(numerical)
        if any(v['unknown_teams'] for v in forecasts.values()):
            raise ValueError('unknown_teams_for_models')
        mixture = self.synthesizer.forecast(numerical)
        probabilities = [float(p) for p in mixture.outcome()]
        model_probs = np.asarray([p['distribution']['p_1x2'] for p in forecasts.values()])
        if not np.isfinite(probabilities).all() or min(probabilities) < 0 or abs(sum(probabilities)-1) > 1e-8:
            raise ValueError('invalid_probability_mass')
        model_versions = self.engine.versions
        prediction_id = digest([str(fixture.id), fingerprint, model_versions,
                                self.synthesizer.report()])
        return TaskOutput(schema_version='1.0', status='ready', data=dict(
            stage='model', input_hash=fingerprint, prediction_id=prediction_id,
            probabilities=probabilities,
            model_spread=float(np.ptp(model_probs, axis=0).max()),
            training_end=max(m.training_end for m in self.engine.models.values()),
            training_matches=min(m.n_train for m in self.engine.models.values()),
            versions=model_versions, validation_hash=self.synthesizer.validation_hash,
            mode=body['mode'], publishing_enabled=False))

    def _red_team(self, job, dependencies):
        body, fixture, at, fingerprint = self._input(job)
        model = self._dependency(dependencies, 'model', fingerprint)
        # Re-check evidence from the *same* immutable input, not a different task.
        verification = DataValidator(self.registry).validate(
            fixture, body['claims'], at, body['snapshots'])
        if verification.status != 'ready':
            raise ValueError('evidence_changed_after_validation')
        accepted = set(verification.accepted_ids)
        claims = [Claim.model_validate(c) for c in body['claims']]
        context = AuditContext(schema_version='1.0', fixture_id=fixture.id,
            as_of=at, kickoff_at=fixture.kickoff_at,
            training_end=model['training_end'], mode=body['mode'],
            observations={c.id: c.observed_at for c in claims},
            lineup_evidence_ids=[c.id for c in claims if c.id in accepted and c.topic == 'lineup'],
            upstream_groups=verification.independence_groups,
            training_matches=model['training_matches'],
            probabilities=tuple(model['probabilities']), model_spread=model['model_spread'],
            prediction_id=model['prediction_id'])
        findings = RedTeam().inspect(context)
        return TaskOutput(schema_version='1.0', status='ready', data=dict(
            stage='red_team', input_hash=fingerprint,
            prediction_id=model['prediction_id'],
            audit_context=context.model_dump(mode='json'),
            findings=[finding.model_dump(mode='json') for finding in findings],
            publishing_enabled=False))

    def _referee(self, job, dependencies):
        body, fixture, at, fingerprint = self._input(job)
        review = self._dependency(dependencies, 'red_team', fingerprint)
        context = AuditContext.model_validate(review['audit_context'])
        findings = [Finding.model_validate(v) for v in review['findings']]
        if context.fixture_id != fixture.id or context.as_of != at:
            raise ValueError('review_fixture_or_time_mismatch')
        # Findings and context are immutable; no actual fresh analysis occurs
        # between rounds. A second unresolved review must abstain, not approve.
        history = []
        for round_no in (1, 2):
            verdict = ScientificReferee().decide(context, findings, round_no)
            history.append(verdict.model_dump(mode='json'))
            if verdict.status != 'needs_reanalysis':
                break
        final = history[-1]
        return TaskOutput(schema_version='1.0', status='ready', data=dict(
            stage='referee', input_hash=fingerprint,
            prediction_id=review['prediction_id'],
            verdict=final, review_history=history,
            publishing_enabled=False,
            reason='research_only_no_forward_verified_market_or_portfolio'))
