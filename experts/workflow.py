"""Three separate execution surfaces: research, historical experiments, journal.

The synchronous research workflow does not impersonate queue workers or debit a
wallet. Runtime task scheduling remains separate from numerical computation.
"""
from zoneinfo import ZoneInfo
import numpy as np
from .contracts import Fixture, Claim, AuditContext, Finding
from .research import aware, Coordinator, DataValidator, LineupResearcher, SourceHunter, ExternalResearcher
from .football import digest, MarketSpecialist
from .review import RedTeam, ScientificReferee, ReviewSession
from .portfolio import RiskManager, RiskState, OddsAnalyst, LearningAuditor


class ResearchLab:
    def __init__(self, engine, synthesizer, registry, runtime=None):
        if set(engine.models) != set(synthesizer.models) or any(
                engine.models[k].__dict__ != synthesizer.models[k].__dict__ for k in engine.models):
            raise ValueError('ensemble_engine_version_mismatch')
        self.engine, self.synthesizer, self.registry, self.runtime = engine, synthesizer, registry, runtime

    def run(self, fixture, as_of, claims, snapshots, mode='retrospective', odds=None):
        f, at = Fixture.model_validate(fixture), aware(as_of)
        if mode not in ('prematch', 'retrospective'):
            raise ValueError('invalid_mode')
        if at >= f.kickoff_at:
            raise ValueError('kickoff_passed')
        if mode == 'prematch' and (self.engine.mode != 'prematch'
                or self.synthesizer.validation_observed_end is None
                or self.synthesizer.validation_observed_end > at):
            raise ValueError('model_not_validated_for_prospective_use')
        claims = [Claim.model_validate(c) for c in claims]
        validation = DataValidator(self.registry).validate(f, claims, at, snapshots)
        lineup = LineupResearcher(self.registry).research(f, claims, at, snapshots)
        numerical_fixture = dict(date=f.kickoff_at.date().isoformat(), home=f.home, away=f.away,
                                 neutral=f.neutral, target=f.target)
        forecasts = self.engine.forecast(numerical_fixture)
        mixture = self.synthesizer.forecast(numerical_fixture)
        probabilities = mixture.outcome()
        model_probabilities = np.array([p['distribution']['p_1x2'] for p in forecasts.values()])
        prediction_id = digest([numerical_fixture, self.engine.versions, self.synthesizer.report(), at.isoformat()])
        accepted = [c for c in claims if c.id in validation.accepted_ids]
        context = AuditContext(schema_version='1.0', fixture_id=f.id, as_of=at, kickoff_at=f.kickoff_at,
            training_end=max(m.training_end for m in self.engine.models.values()), mode=mode,
            observations={c.id: c.observed_at for c in claims},
            lineup_evidence_ids=[c.id for c in accepted if c.topic == 'lineup'],
            upstream_groups=validation.independence_groups,
            training_matches=min(m.n_train for m in self.engine.models.values()),
            probabilities=tuple(probabilities), model_spread=float(np.ptp(model_probabilities, axis=0).max()),
            prediction_id=prediction_id)
        findings = RedTeam().inspect(context)
        if any(p['unknown_teams'] for p in forecasts.values()):
            findings.append(Finding(schema_version='1.0', issue_type='low_sample', severity='high',
                evidence_ids=[prediction_id], requested_action='review'))
        for claim_id, reason in validation.quarantined.items():
            issue = 'data_leakage' if reason == 'future_information' else 'identity_error' if reason == 'identity_or_target_mismatch' else 'source_conflict'
            findings.append(Finding(schema_version='1.0', issue_type=issue, severity='critical',
                evidence_ids=[claim_id], requested_action='recalculate'))
        reviews = []
        # No invented resolution: a second unchanged review must abstain.
        for round_no in (1, 2):
            verdict = (ReviewSession(self.runtime).decide(context, findings, f'{prediction_id}:{round_no}')
                if self.runtime else ScientificReferee().decide(context, findings, round_no))
            reviews.append(verdict.model_dump(mode='json'))
            if verdict.status != 'needs_reanalysis':
                break
        odds_report = {'status': 'blocked', 'reason': 'real_odds_missing', 'clv': None}
        edge = None
        if odds is not None:
            odds_report = OddsAnalyst().analyze(f, odds, probabilities, at, self.registry) | {'clv': None}
            edge = max(odds_report['expected_return'])
        # Reference preview only; actual portfolio requires its own wallet state.
        risk = RiskManager().decide(RiskState(schema_version='1.0', balance_kurus=100000,
            spent_today_kurus=0, open_risk_kurus=0), verdict, edge,
            uncertainty=1.0)  # No validated uncertainty estimator yet.
        output = {'schema_version': '1.0', 'mode': mode, 'prediction_id': prediction_id,
            'fixture': f.model_dump(mode='json'), 'validation': validation.model_dump(mode='json'),
            'lineup': lineup.model_dump(mode='json'), 'models': forecasts, 'ensemble': mixture.export(),
            'ensemble_validation': self.synthesizer.report(),
            'markets': {m: MarketSpecialist().calculate(mixture, m) for m in ('1X2', 'btts', 'half1')},
            'findings': [x.model_dump(mode='json') for x in findings], 'reviews': reviews,
            'odds': odds_report, 'risk_preview': risk.model_dump(mode='json'),
            'risk_state_origin': 'reference preview, not a wallet balance', 'execution_enabled': False}
        if self.runtime:
            output['plan'] = Coordinator(self.runtime).plan([f], f.kickoff_at.astimezone(ZoneInfo('Europe/Istanbul')).date())
            output['sources'] = SourceHunter(self.runtime.queue).inspect(at)
            output['external'] = ExternalResearcher(self.runtime.queue).availability(at)
            with self.runtime.transaction():
                import json
                prior = [json.loads(r[0]) for r in self.runtime.db.execute("SELECT body FROM f_audit WHERE event='research_completed'")]
                prior = next((r for r in prior if r['prediction_id'] == prediction_id), None)
                if prior and prior['output_hash'] != digest(output):
                    raise ValueError('prediction_revision_conflict')
                if not prior:
                    self.runtime.audit('research_completed', {'prediction_id': prediction_id, 'output_hash': digest(output),
                        'mode': mode, 'model_versions': self.engine.versions, 'output': output})
        return output


class StrategyExperiments:
    def evaluate(self, synthesizer, rows):
        if len({r['id'] for r in rows}) != len(rows):
            raise ValueError('duplicate_experiment_fixture')
        distributions = [synthesizer.forecast({k: r[k] for k in ('home', 'away', 'date', 'target', 'neutral')}) for r in rows]
        result = LearningAuditor().evaluate(distributions, [(r['home_goals'], r['away_goals']) for r in rows])
        return {'mode': 'historical', 'test_dataset_hash': digest(rows), 'metrics': result,
                'roi': None, 'clv': None, 'stored_coupons': 0, 'reason': 'no verified historical odds supplied'}
