import json
import unittest
from datetime import datetime, timedelta, timezone
from dashboard.daily_quality import report


class DailyQualityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 19, 18, tzinfo=timezone.utc)

    def fixture(self, **changes):
        data = {'id': 'match-1', 'observed_at': (self.now-timedelta(hours=2)).isoformat(),
                'prediction_status': 'conditional_scenarios',
                'scenarios': [{'reviews': [{'status': 'abstain'}]},
                              {'reviews': [{'status': 'approved'}]}]}
        return data | changes

    def test_fresh_conditional_is_not_executable(self):
        result = report([self.fixture()], self.now, {'status': 'done', 'secret': 'SECRET'})
        self.assertTrue(result['data_ready'])
        self.assertEqual(result['conditional_venue_fixtures'], 1)
        self.assertEqual(result['review_approved_scenarios'], 1)
        self.assertEqual(result['review_abstain_scenarios'], 1)
        self.assertFalse(result['execution_enabled'])
        self.assertFalse(result['pilot_enabled'])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_stale_and_future_are_not_fresh(self):
        rows = [self.fixture(observed_at=(self.now-timedelta(hours=25)).isoformat()),
                self.fixture(id='match-2', observed_at=(self.now+timedelta(seconds=1)).isoformat())]
        result = report(rows, self.now)
        self.assertEqual(result['fresh_fixtures'], 0)
        self.assertFalse(result['data_ready'])

    def test_duplicate_id_blocks_data_ready(self):
        result = report([self.fixture(), self.fixture()], self.now)
        self.assertEqual(result['duplicate_fixture_ids'], 1)
        self.assertFalse(result['data_ready'])

    def test_malformed_values_fail_closed(self):
        result = report([{}, None, self.fixture(id='', observed_at='not a date', scenarios=[None, {}])], self.now)
        self.assertEqual(result['stale_or_unverifiable_fixtures'], 3)
        self.assertEqual(result['review_other_scenarios'], 2)
        self.assertFalse(result['data_ready'])

    def test_unrecognized_collection_status_not_leaked(self):
        result = report([], self.now, {'status': 'PRIVATE_STACK_TRACE'})
        self.assertEqual(result['collection_status'], 'not_verified')
        self.assertFalse(result['data_ready'])

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            report([], datetime(2026, 10, 19))
