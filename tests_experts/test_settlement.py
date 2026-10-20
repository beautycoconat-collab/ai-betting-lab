import unittest
from experts.settlement import Pick, settle_pick

def final(h,a,target='regulation90'):
    return dict(schema_version='1.0', status='final', home=h, away=a, target=target)

def bet(market,selection=None,line=None):
    return dict(schema_version='1.0',market=market,selection=selection,line=line,score_target='regulation90')

class SettlementTests(unittest.TestCase):
    def test_1x2_all_results(self):
        for score,outcome in [((2,1),'1'),((1,1),'X'),((0,3),'2')]:
            for selection in '1X2':
                with self.subTest(score=score,selection=selection):
                    s=settle_pick(bet('1X2',selection),final(*score))
                    self.assertEqual(s['status'],'won' if selection==outcome else 'lost')

    def test_totals_push(self):
        self.assertEqual(settle_pick(bet('over',line=3),final(2,1))['status'],'push')
        self.assertEqual(settle_pick(bet('under',line=3),final(2,1))['status'],'push')

    def test_half_line_no_push(self):
        self.assertEqual(settle_pick(bet('over',line=2.5),final(2,1))['status'],'won')
        self.assertEqual(settle_pick(bet('under',line=2.5),final(2,1))['status'],'lost')

    def test_team_totals_push(self):
        self.assertEqual(settle_pick(bet('home_over',line=2),final(2,0))['status'],'push')
        self.assertEqual(settle_pick(bet('away_under',line=0.5),final(2,0))['status'],'won')
        self.assertEqual(settle_pick(bet('home_under',line=2.5),final(3,0))['status'],'lost')

    def test_btts_yes_no(self):
        self.assertEqual(settle_pick(bet('btts_yes'),final(1,1))['status'],'won')
        self.assertEqual(settle_pick(bet('btts_yes'),final(1,0))['status'],'lost')
        self.assertEqual(settle_pick(bet('btts_no'),final(1,0))['status'],'won')

    def test_handicap_push(self):
        self.assertEqual(settle_pick(bet('home_handicap',line=-1),final(2,1))['status'],'push')
        self.assertEqual(settle_pick(bet('home_handicap',line=-0.5),final(2,1))['status'],'won')
        self.assertEqual(settle_pick(bet('home_handicap',line=0.5),final(1,2))['status'],'lost')

    def test_score_target_conflict_blocks(self):
        x=settle_pick(bet('over',line=2.5),final(2,1,'final_including_extra_time'))
        self.assertEqual(x['status'],'blocked')

    def test_wait_for_final(self):
        for status in ('pending','postponed'):
            x=settle_pick(bet('over',line=2.5),
                dict(schema_version='1.0',status=status,target='regulation90'))
            self.assertEqual(x['status'],'pending')

    def test_cancelled_and_abandoned_do_not_guess_void(self):
        for status in ('cancelled','abandoned'):
            x=settle_pick(bet('1X2','1'),
                dict(schema_version='1.0',status=status,target='regulation90'))
            self.assertEqual(x['reason'],'provider_void_rules_required')

    def test_unverified_final_rejected(self):
        with self.assertRaises(ValueError):
            settle_pick(bet('1X2','1'),dict(schema_version='1.0',status='final',
                                  home=2,target='regulation90'))

    def test_quarter_handicap_rejected(self):
        with self.assertRaises(ValueError):
            Pick.model_validate(bet('home_handicap',line=-.25))

    def test_unsupported_first_half_rejected(self):
        with self.assertRaises(ValueError):
            Pick.model_validate(bet('half1',line=0.5))

if __name__=='__main__': unittest.main()
