import unittest
from engine.adapters import OpenFootball


class FeedFormats(unittest.TestCase):
    def test_legacy_and_nested_scores_agree(self):
        a=OpenFootball(); p={'league':'de.1','season':'2025-26'}
        row=dict(team1='Alpha',team2='Beta',date='2025-08-24')
        nested=a.parse(row|{'score':{'ft':[0,0]}},p)
        legacy=a.parse(row|{'score':[0,0]},p)
        self.assertEqual(nested.dict(),legacy.dict())

    def test_invalid_and_half_time_only_do_not_invent_final(self):
        a=OpenFootball(); p={'league':'de.1','season':'2025-26'}
        row=dict(team1='Alpha',team2='Beta',date='2025-08-24')
        for score in ([1],[True,0],'1-0'):
            with self.assertRaises(ValueError):a.parse(row|{'score':score},p)
        self.assertIsNone(a.parse(row|{'score':{'ht':[1,0]}},p).home_goals)
