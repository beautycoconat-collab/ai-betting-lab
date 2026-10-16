import json
import math
import unittest
from dataclasses import replace
from pathlib import Path
from experts.calibration import (ForecastObservation, temperature_scale,
                                 evaluate_calibration_challenger)
from tests_experts.test_experts import FootballTests


def obs(index, day, probs=(.6,.22,.18), label=0):
    return ForecastObservation(f'{index}',day,probs,label)


class CalibrationContractTests(unittest.TestCase):
    def setUp(self):
        self.train = [obs(i, f'2025-01-{i+1:02d}',label=i%3) for i in range(30)]
        self.test = [obs(i+100, f'2025-02-{i+1:02d}',label=(i+1)%3) for i in range(15)]

    def test_identity_at_one_and_probability_conservation(self):
        p=(.6,.2,.2)
        for temp in (.25,1,2,4):
            scaled=temperature_scale(p,temp)
            self.assertAlmostEqual(sum(scaled),1)
            self.assertTrue(all(0<x<1 for x in scaled))
        for x,y in zip(temperature_scale(p,1),p):
            self.assertAlmostEqual(x,y)

    def test_overconfidence_flattens_with_temperature(self):
        p=(.90,.05,.05)
        self.assertLess(temperature_scale(p,2)[0],p[0])

    def test_invalid_probability_rejected(self):
        for p in ((.5,.5,0),(-.1,.8,.3),(.1,.2,.2),(math.nan,.5,.5)):
            with self.subTest(p=p),self.assertRaises(ValueError):
                temperature_scale(p,1)

    def test_negative_or_invalid_temperature_rejected(self):
        for t in (0,-1,math.inf,math.nan):
            with self.subTest(t=t),self.assertRaises(ValueError):
                temperature_scale((.5,.3,.2),t)

    def test_challenger_is_not_auto_promoted(self):
        result=evaluate_calibration_challenger(self.train,self.test)
        self.assertTrue(result['not_auto_promoted'])
        self.assertEqual(result['test_n'],15)
        self.assertEqual(result['baseline']['n'],15)
        self.assertEqual(len(result['test_sha256']),64)
        self.assertEqual(result,evaluate_calibration_challenger(self.train,self.test))

    def test_train_test_overlap_dates_rejected(self):
        with self.assertRaisesRegex(ValueError,'calibration_overlaps_test'):
            evaluate_calibration_challenger(self.train,self.train)

    def test_duplicate_fixture_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate_fixture'):
            evaluate_calibration_challenger(self.train + [self.train[-1]],self.test)

    def test_out_of_order_rows_rejected(self):
        with self.assertRaisesRegex(ValueError,'not_chronological'):
            evaluate_calibration_challenger(self.train[::-1],self.test)

    def test_insufficient_sample_rejected(self):
        with self.assertRaisesRegex(ValueError,'insufficient_calibration_sample'):
            evaluate_calibration_challenger(self.train[:15],self.test)

    def test_same_fixture_id_different_dates_rejected(self):
        bad=[replace(self.test[0],fixture_id=self.train[0].fixture_id)] + self.test[1:]
        with self.assertRaisesRegex(ValueError,'calibration_fixture_overlap'):
            evaluate_calibration_challenger(self.train,bad)

    def test_empty_test_rejected(self):
        with self.assertRaisesRegex(ValueError,'calibration_data_empty'):
            evaluate_calibration_challenger(self.train,[])


class BundesligaCalibrationAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FootballTests.setUpClass()

    def test_real_retrospective_heldout_challenger(self):
        model=FootballTests.engine.models['poisson']
        def make(rows):
            output=[]
            for row in sorted(rows,key=lambda x:(x['date'],x['id'])):
                # The model was fit strictly before both periods.
                probs=model.predict(row['home'],row['away'],row['neutral']).outcome()
                y=0 if row['home_goals']>row['away_goals'] else 1 if row['home_goals']==row['away_goals'] else 2
                output.append(ForecastObservation(row['id'],row['date'],tuple(float(x) for x in probs),y))
            return output
        result=evaluate_calibration_challenger(make(FootballTests.validation),make(FootballTests.test_rows))
        self.assertEqual(result['calibration_n'],73)
        self.assertEqual(result['test_n'],98)
        self.assertLess(result['baseline']['log_loss_1x2'],5)
        self.assertLess(result['challenger']['log_loss_1x2'],5)
        self.assertEqual(result['mode'],'retrospective_challenger_only')

if __name__=='__main__':unittest.main()
