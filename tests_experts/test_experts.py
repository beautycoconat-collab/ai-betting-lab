"""Synthetic boundary fixtures; Football tests use the real archived Bundesliga rows."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
import numpy as np
from foundation.runtime import Runtime
from experts.contracts import Fixture, Claim, AuditContext, Finding, Odds
from experts.research import Coordinator, SourceHunter, DataValidator, LineupResearcher, ExternalResearcher
from experts.football import ScoreEngine, Synthesizer, TeamStrength, Mixture, MarketSpecialist, training_rows
from experts.review import RedTeam, ScientificReferee, ReviewSession
from experts.portfolio import OddsAnalyst, RiskState, RiskManager, PortfolioJournal, LearningAuditor

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
FID = UUID(int=1)
REGISTRY = json.loads((ROOT/'config/source_registry_v2.json').read_text())


def fixture(**overrides):
    return Fixture.model_validate(dict(schema_version='1.0', id=FID, home='A', away='B',
        competition='synthetic', season='test', kickoff_at=NOW+timedelta(hours=6),
        target='regulation90', neutral=False) | overrides)


def claim(**overrides):
    return Claim.model_validate(dict(schema_version='1.0', id='e1', fixture_id=FID,
        source_id='openfootball', snapshot_id='snapshot', source_url='https://example.invalid/synthetic',
        observed_at=NOW-timedelta(minutes=1), published_at=NOW-timedelta(minutes=2),
        target='regulation90', quality='verified', topic='lineup', subject='A', value='test lineup') | overrides)


def snapshot(c):
    return {c.snapshot_id: dict(source_id=c.source_id, source_url=c.source_url, observed_at=c.observed_at.isoformat())}


def context(**overrides):
    return AuditContext.model_validate(dict(schema_version='1.0', fixture_id=FID, as_of=NOW,
        kickoff_at=fixture().kickoff_at, training_end='2026-10-01', mode='prematch',
        observations={'e1': NOW-timedelta(minutes=1)}, lineup_evidence_ids=['e1'],
        upstream_groups={'source': ['e1']}, training_matches=200, probabilities=(.4, .3, .3),
        model_spread=.05, prediction_id='prediction-version-1') | overrides)


def odds(**overrides):
    return Odds.model_validate(dict(schema_version='1.0', fixture_id=FID, source_id='test_odds',
        snapshot_id='synthetic', observed_at=NOW, published_at=NOW, target='regulation90',
        market='1X2', prices=(2., 3., 4.)) | overrides)


class LocalCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name)/'test.db', clock=lambda: NOW.isoformat())

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()


class ResearchTests(LocalCase):
    def test_plan_idempotent_dag(self):
        c = Coordinator(self.runtime)
        a = c.plan([fixture()], NOW.date(), [FID])
        self.assertEqual(a, c.plan([fixture()], NOW.date(), [FID]))
        self.assertEqual(len(a['task_ids'][str(FID)]), 6)
        self.assertEqual(self.runtime.db.execute('SELECT count(*) FROM f_task_dependencies').fetchone()[0], 5)

    def test_missing_evidence_defers_model(self):
        p = Coordinator(self.runtime).plan([fixture()], NOW.date())
        self.assertEqual(set(p['task_ids'][str(FID)]), {'collect', 'validate'})

    def test_identity_conflict(self):
        c = Coordinator(self.runtime)
        c.plan([fixture()], NOW.date())
        with self.assertRaises(ValueError):
            c.plan([fixture(home='C')], NOW.date())

    def test_duplicate_fixture(self):
        with self.assertRaises(ValueError):
            Coordinator(self.runtime).plan([fixture(), fixture()], NOW.date())

    def test_source_registry_and_block(self):
        hunter = SourceHunter(self.runtime.queue)
        self.assertEqual(hunter.inspect(NOW)['openfootball']['status'], 'ready')
        with self.assertRaises(ValueError):
            hunter.schedule('unknown', 'discover', {}, NOW)
        with self.assertRaises(ValueError):
            hunter.schedule('openfootball', 'discover', {}, NOW+timedelta(days=60))

    def test_source_job_idempotent(self):
        h = SourceHunter(self.runtime.queue)
        self.assertEqual(h.schedule('openfootball', 'discover', {}, NOW), h.schedule('openfootball', 'discover', {}, NOW))

    def test_valid_provenance(self):
        c = claim()
        result = DataValidator(REGISTRY).validate(fixture(), [c], NOW, snapshot(c))
        self.assertEqual(result.accepted_ids, ['e1'])

    def test_invalid_evidence_quarantined(self):
        for change in ({'observed_at': NOW+timedelta(seconds=1)}, {'quality': 'unknown'},
                       {'published_at': None}, {'target': 'provider_final_unknown'}, {'fixture_id': UUID(int=2)},
                       {'published_at': NOW+timedelta(seconds=1)}):
            with self.subTest(change=change):
                c = claim(**change)
                result = DataValidator(REGISTRY).validate(fixture(), [c], NOW, snapshot(c))
                self.assertEqual(result.status, 'blocked')

    def test_missing_snapshot(self):
        result = DataValidator(REGISTRY).validate(fixture(), [claim()], NOW, {})
        self.assertEqual(result.status, 'blocked')

    def test_corrupt_snapshot_time_is_quarantined(self):
        c = claim()
        snapshots = snapshot(c)
        snapshots[c.snapshot_id]['observed_at'] = 'not-a-timestamp'
        self.assertEqual(DataValidator(REGISTRY).validate(fixture(), [c], NOW, snapshots).status, 'blocked')

    def test_conflicts_not_forced(self):
        a, b = claim(), claim(id='e2', value='conflicting lineup')
        r = DataValidator(REGISTRY).validate(fixture(), [a, b], NOW, snapshot(a))
        self.assertEqual(r.quarantined, {'e1': 'conflicting', 'e2': 'conflicting'})

    def test_duplicate_evidence(self):
        with self.assertRaises(ValueError):
            DataValidator(REGISTRY).validate(fixture(), [claim(), claim()], NOW, snapshot(claim()))

    def test_lineup_partial_no_invented_injuries(self):
        c = claim()
        r = LineupResearcher(REGISTRY).research(fixture(), [c], NOW, snapshot(c))
        self.assertEqual(r.status, 'partial')
        self.assertIn('injury', r.missing_topics)
        self.assertIsNone(r.numeric_override)

    def test_external_disabled_zero_weight(self):
        r = ExternalResearcher(self.runtime.queue).availability(NOW)
        self.assertEqual(r['ensemble_weight'], 0)
        with self.assertRaises(ValueError):
            ExternalResearcher(self.runtime.queue).ingest('openfootball', {}, clock=lambda: NOW.isoformat())

    def test_contract_rejects_unknown_fields_and_versions(self):
        for change in ({'schema_version': '2.0'}, {'numeric_override': .5}, {'neutral': 'false'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                fixture(**change)


class FootballTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((ROOT/'reports/phase2/bundesliga/dataset.json').read_text())
        cls.engine = ScoreEngine().fit(cls.rows, '2025-01-01T00:00:00+00:00', 'regulation90')
        cls.validation = [r for r in cls.rows if '2025-01-01' <= r['date'] < '2025-03-01']
        cls.test_rows = [r for r in cls.rows if r['date'] >= '2025-03-01']
        cls.synth = Synthesizer().fit(cls.engine.models, cls.validation)
        cls.f = {k: cls.test_rows[0][k] for k in ('date', 'home', 'away', 'neutral', 'target')}

    def test_real_data_provenance(self):
        self.assertEqual(len(self.rows), 306)
        self.assertTrue(all(r['source_url'].startswith('https://') and len(r['snapshot_sha256']) == 64 for r in self.rows))

    def test_cutoff_training(self):
        self.assertTrue(all(m.training_end < '2025-01-01' for m in self.engine.models.values()))

    def test_backfilled_data_not_prematch(self):
        with self.assertRaises(ValueError):
            training_rows(self.rows, '2025-01-01T00:00:00+00:00', 'regulation90', 'prematch')

    def test_model_versions(self):
        forecasts = self.engine.forecast(self.f)
        self.assertEqual(set(forecasts), {'baseline', 'elo', 'poisson', 'dixon_coles'})
        self.assertTrue(all(len(f['model_version']) == 64 for f in forecasts.values()))

    def test_score_matrix_mass_and_tail(self):
        for m in self.engine.models.values():
            d = m.predict(self.f['home'], self.f['away'])
            g, t = d.grid(3)
            self.assertGreater(t, 0)
            self.assertAlmostEqual(float(g.sum()+t), 1, places=10)

    def test_ensemble_mass(self):
        d = self.synth.forecast(self.f)
        g, tail = d.grid(5)
        self.assertAlmostEqual(float(g.sum()+tail), 1, places=10)
        self.assertAlmostEqual(float(d.outcome().sum()), 1)

    def test_training_validation_overlap(self):
        with self.assertRaises(ValueError):
            Synthesizer().fit(self.engine.models, self.rows)

    def test_validation_test_overlap(self):
        with self.assertRaises(ValueError):
            self.synth.forecast(self.f | {'date': self.validation[-1]['date']})

    def test_label_leakage_and_target(self):
        for change in ({'home_goals': 0}, {'target': 'final_including_extra_time'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.synth.forecast(self.f | change)

    def test_duplicate_models_share_group(self):
        m = self.engine.models['baseline']
        s = Synthesizer().fit({'a': m, 'b': m}, self.validation)
        self.assertEqual(s.groups, [[0, 1]])
        np.testing.assert_allclose(s.weights, [.5, .5])

    def test_markets_consistent(self):
        d, expert = self.synth.forecast(self.f), MarketSpecialist()
        over, under = expert.calculate(d, 'over', 2.5), expert.calculate(d, 'under', 2.5)
        self.assertAlmostEqual(over['win']+under['win'], 1)
        self.assertEqual(expert.calculate(d, 'half1')['status'], 'insufficient_data')
        self.assertGreater(expert.calculate(d, 'btts')['probability'], 0)
        handicap = expert.calculate(d, 'home_handicap', 0)
        self.assertAlmostEqual(handicap['push'], float(d.outcome()[1]))

    def test_quarter_handicap_not_misrepresented(self):
        with self.assertRaises(ValueError):
            MarketSpecialist().calculate(self.synth.forecast(self.f), 'home_handicap', .25)

    def test_invalid_weights(self):
        with self.assertRaises(ValueError):
            Mixture([self.engine.models['baseline'].predict('A', 'B')], [float('nan')])

    def test_strength_missing_xg(self):
        r = TeamStrength().analyze(self.rows, '2025-01-01T00:00:00+00:00', 'regulation90')
        self.assertEqual(len(r['teams']), 18)
        self.assertTrue(all(t['xg'] is None for t in r['teams'].values()))

    def test_held_out_metrics(self):
        ds = [self.synth.forecast({k: r[k] for k in self.f}) for r in self.test_rows]
        report = LearningAuditor().evaluate(ds, [(r['home_goals'], r['away_goals']) for r in self.test_rows])
        self.assertEqual(report['n'], len(self.test_rows))
        self.assertTrue(np.isfinite(report['score_logloss']))


class ReviewTests(LocalCase):
    def test_clean_approval_is_not_bet_permission(self):
        self.assertEqual(RedTeam().inspect(context()), [])
        v = ScientificReferee().decide(context(), [], 1)
        self.assertEqual((v.status, v.risk_action), ('approved', 'wait'))

    def test_two_round_abstain(self):
        c = context(lineup_evidence_ids=[])
        fs = RedTeam().inspect(c)
        self.assertEqual(ScientificReferee().decide(c, fs, 1).status, 'needs_reanalysis')
        self.assertEqual(ScientificReferee().decide(c, fs, 2).risk_action, 'skip')

    def test_referee_independent_checks(self):
        for change in ({'observations': {'e1': NOW+timedelta(seconds=1)}},
                       {'training_matches': 2}, {'model_spread': .5}, {'probabilities': (.98, .01, .01)},
                       {'training_end': '2026-10-15'}):
            with self.subTest(change=change):
                self.assertEqual(ScientificReferee().decide(context(**change), [], 2).status, 'abstain')

    def test_unknown_evidence_rejected(self):
        finding = Finding(schema_version='1.0', issue_type='low_sample', severity='high', evidence_ids=['missing'], requested_action='review')
        self.assertEqual(ScientificReferee().decide(context(), [finding], 1).status, 'rejected')

    def test_numeric_override_forbidden(self):
        with self.assertRaises(ValueError):
            Finding(schema_version='1.0', issue_type='low_sample', severity='high', evidence_ids=['e1'], requested_action='review', numeric_override=.49)

    def test_round_three_rejected(self):
        with self.assertRaises(ValueError):
            ScientificReferee().decide(context(), [], 3)

    def test_persistent_idempotent_reviews(self):
        c = context(lineup_evidence_ids=[])
        session = ReviewSession(self.runtime)
        a = session.decide(c, [], 'r1')
        self.assertEqual(a, session.decide(c, [], 'r1'))
        self.assertEqual(ReviewSession(self.runtime).decide(c, [], 'r2').status, 'abstain')
        with self.assertRaises(ValueError):
            session.decide(c, [], 'r3')
        with self.assertRaises(ValueError):
            session.decide(context(), [], 'r1')
        self.assertTrue(self.runtime.verify_audit())

    def test_shared_upstream_flag(self):
        c = context(observations={'e1': NOW, 'e2': NOW}, upstream_groups={'unknown': ['e1', 'e2']})
        self.assertIn('shared_upstream', [f.issue_type for f in RedTeam().inspect(c)])


class PortfolioTests(LocalCase):
    def setUp(self):
        super().setUp()
        self.policy = {'test_odds': REGISTRY['openfootball'] | {'odds_allowed': True}}
        self.verdict = ScientificReferee().decide(context(), [], 1)
        self.state = RiskState(schema_version='1.0', balance_kurus=100000, spent_today_kurus=0, open_risk_kurus=0)

    def test_odds_math(self):
        r = OddsAnalyst().analyze(fixture(), odds(), [.5, .25, .25], NOW, self.policy)
        self.assertAlmostEqual(r['overround'], 1/12)
        self.assertAlmostEqual(sum(r['no_vig_probabilities']), 1)

    def test_odds_staleness(self):
        for change in ({'published_at': NOW-timedelta(hours=1)}, {'observed_at': NOW+timedelta(seconds=1)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                OddsAnalyst().analyze(fixture(), odds(**change), [.5, .25, .25], NOW, self.policy)

    def test_odds_permission(self):
        with self.assertRaises(ValueError):
            OddsAnalyst().analyze(fixture(), odds(), [.5, .25, .25], NOW, {})

    def test_clv_requires_closing(self):
        self.assertIsNone(OddsAnalyst().clv(odds(), None, fixture().kickoff_at)['price_clv'])

    def test_clv_math_and_time(self):
        closing = odds(observed_at=fixture().kickoff_at-timedelta(seconds=60),
                       published_at=fixture().kickoff_at-timedelta(seconds=60), prices=(1.8, 3., 4.))
        result = OddsAnalyst().clv(odds(), closing, fixture().kickoff_at)
        self.assertAlmostEqual(result['price_clv'][0], 2/1.8-1)
        with self.assertRaises(ValueError):
            OddsAnalyst().clv(odds(), closing, NOW)

    def test_minimum_conflicts_with_balanced_risk(self):
        d = RiskManager().decide(self.state, self.verdict, .1, .1)
        self.assertEqual(d.action, 'skip')
        self.assertEqual(d.reason, 'minimum_exceeds_risk_limit')

    def test_daily_limit_and_no_execution(self):
        for spent in (0, 10000, 20000):
            s = self.state.model_dump() | {'spent_today_kurus': spent, 'minimum_coupon_kurus': 0}
            d = RiskManager().decide(s, self.verdict, .1, .1)
            self.assertFalse(d.execution_enabled)
            self.assertEqual(d.stake_kurus, 0)

    def test_unresolved_review_skip(self):
        v = ScientificReferee().decide(context(lineup_evidence_ids=[]), [], 2)
        self.assertEqual(RiskManager().decide(self.state, v).action, 'skip')

    def test_journal_idempotent_and_auditable(self):
        j = PortfolioJournal(self.runtime)
        d = RiskManager().decide(self.state, self.verdict)
        a = j.record(fixture(), d, 'decision1', NOW, 'prospective')
        self.assertEqual(a, j.record(fixture(), d, 'decision1', NOW, 'prospective'))
        self.assertTrue(self.runtime.verify_audit())
        self.assertEqual(self.runtime.db.execute("SELECT count(*) FROM f_audit WHERE event='portfolio_decision'").fetchone()[0], 1)

    def test_journal_refuses_historical_and_stale(self):
        j = PortfolioJournal(self.runtime)
        d = RiskManager().decide(self.state, self.verdict)
        with self.assertRaises(ValueError):
            j.record(fixture(), d, 'history', NOW, 'historical')
        with self.assertRaises(ValueError):
            j.record(fixture(), d, 'stale', NOW-timedelta(minutes=1), 'prospective')

    def test_roi_modes_and_drawdown(self):
        rows = [dict(id='a', mode='historical', stake_kurus=1000, payout_kurus=0, settled_at=NOW.isoformat())]
        r = LearningAuditor().portfolio(rows, 'historical')
        self.assertEqual(r['realized_roi'], -1)
        self.assertAlmostEqual(r['max_settled_equity_drawdown'], .01)
        with self.assertRaises(ValueError):
            LearningAuditor().portfolio(rows, 'prospective')
        with self.assertRaises(ValueError):
            LearningAuditor().portfolio(rows*2, 'historical')

    def test_windows_no_future(self):
        self.assertEqual(LearningAuditor().windows([{'created_at': NOW.isoformat()}], NOW)[7], 1)
        with self.assertRaises(ValueError):
            LearningAuditor().windows([{'created_at': (NOW+timedelta(seconds=1)).isoformat()}], NOW)

    def test_challenger_reproducible_no_auto_promotion(self):
        a = LearningAuditor().compare([1.]*100, [.9]*100)
        self.assertEqual(a, LearningAuditor().compare([1.]*100, [.9]*100))
        self.assertFalse(a['auto_promote'])
        with self.assertRaises(ValueError):
            LearningAuditor().compare([1.], [1., 2.])


if __name__ == '__main__':
    unittest.main()
