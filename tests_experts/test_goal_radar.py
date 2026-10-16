"""Synthetic interval replay boundary tests, not live radar accuracy."""
import unittest
from experts.goal_radar import GoalRadar


def intervals():
    return [dict(schema_version='1.0',fixture_id='training-'+str(i),start_minute=0,
        end_minute=90,goals=2,ended_at='2025-01-01T14:00:00+00:00',
        observed_at='2025-01-01T14:01:00+00:00',evidence_id='synthetic-'+str(i),target='regulation90') for i in range(30)]


def state(**changes):
    return dict(schema_version='1.0',fixture_id='heldout',minute=85,home_goals=1,
        away_goals=0,red_cards=0,observed_at='2025-02-01T14:00:00+00:00',
        as_of='2025-02-01T14:00:10+00:00',evidence_id='synthetic-live-state',mode='replay')|changes


class RadarTests(unittest.TestCase):
    def setUp(self):self.model=GoalRadar().fit(intervals(),'2025-01-02T00:00:00+00:00')
    def test_live_always_blocked(self):
        self.assertEqual(self.model.predict(state(mode='live'))['status'],'BLOCKED')
    def test_replay_probability_tail_and_bounds(self):
        result=self.model.predict(state())
        self.assertEqual(result['horizon_minutes'],5)
        low,high=result['parameter_interval_95']
        self.assertLess(low,result['probability']);self.assertGreater(high,result['probability'])
        self.assertFalse(result['execution_enabled'])
    def test_stale_and_unmodelled_cards_abstain(self):
        self.assertIsNone(self.model.predict(state(red_cards=1))['probability'])
        self.assertIsNone(self.model.predict(state(as_of='2025-02-01T14:01:00+00:00'))['probability'])
    def test_future_and_training_overlap_rejected(self):
        for s in (state(fixture_id='training-1'),state(observed_at='2025-03-01T14:00:00+00:00')):
            with self.assertRaises(ValueError):self.model.predict(s)
    def test_future_labels_rejected(self):
        with self.assertRaises(ValueError):GoalRadar().fit(intervals(),'2024-12-01T00:00:00+00:00')
    def test_duplicate_intervals_rejected(self):
        with self.assertRaises(ValueError):GoalRadar().fit(intervals()+[intervals()[0]],'2025-01-02T00:00:00+00:00')
    def test_replay_metrics_and_future_label(self):
        case=dict(state=state(),horizon_minutes=5,goal_in_horizon=False,
                  outcome_observed_at='2025-02-01T14:06:00+00:00')
        report=self.model.evaluate([case],'2025-02-01T15:00:00+00:00')
        self.assertEqual(report['cases'],1)
        self.assertFalse(report['live_validation'])
        with self.assertRaises(ValueError):self.model.evaluate([case],'2025-02-01T14:01:00+00:00')
