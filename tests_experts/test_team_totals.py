import unittest
from experts.football import MarketSpecialist
from tests_experts.test_experts import FootballTests

class TeamTotalsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FootballTests.setUpClass()
        cls.d = FootballTests.synth.forecast(FootballTests.f)
        cls.m = MarketSpecialist()

    def test_over_under_partition(self):
        for side in ('home', 'away'):
            for line in (.5, 1.5, 2.5, 5.5):
                with self.subTest(side=side, line=line):
                    over = self.m.calculate(self.d, side+'_over', line)
                    under = self.m.calculate(self.d, side+'_under', line)
                    self.assertAlmostEqual(over['win']+under['win'], 1, places=9)
                    self.assertAlmostEqual(over['push']+under['push'], 0, places=10)

    def test_integer_lines_push(self):
        for market in ('home_over', 'away_over'):
            r=self.m.calculate(self.d,market,2)
            self.assertGreater(r['push'],0)
            self.assertAlmostEqual(r['win']+r['push']+r['lose'],1,places=9)

    def test_rejects_quarter_line(self):
        with self.assertRaises(ValueError):
            self.m.calculate(self.d,'home_over',1.25)

    def test_first_half_remains_unsupported(self):
        self.assertEqual(self.m.calculate(self.d,'half1')['status'],'insufficient_data')

if __name__=='__main__':unittest.main()
