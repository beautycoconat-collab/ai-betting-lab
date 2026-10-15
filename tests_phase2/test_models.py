"""Synthetic mathematical/unit tests; no fabricated rows in evaluation reports."""
import unittest,tempfile,json,math
from pathlib import Path
import numpy as np
from engine.models import *
from engine.dataset import split
from engine.predict import predict
from engine.evaluate import reliability,evaluate

# Fixed deterministic synthetic fixture, not represented as real football.
def training():
 return [{'id':str(i),'date':f'2019-{i//28+1:02d}-{i%28+1:02d}','home':['A','B','C'][i%3],'away':['B','C','A'][i%3],'home_goals':i%4,'away_goals':(i*3)%3,'neutral':i%2==0,'target':'regulation90','observed_at':'2026-10-14T00:00:00+00:00'} for i in range(84)]
class Mathematics(unittest.TestCase):
 def test_mass_and_positive_tail(self):
  for l,m,rho in [(1.7,.8,-.08),(8,8,.015),(.02,.02,-.12)]:
   d=ScoreDistribution(l,m,rho);grid,tail=d.grid(20);self.assertAlmostEqual(grid.sum()+tail,1,places=12);self.assertTrue(np.all(grid>=0));self.assertGreater(tail,0)
 def test_outcomes_match_score_sum(self):
  d=ScoreDistribution(2,1,-.1);g,t=d.grid(40);expected=[np.tril(g,-1).sum(),np.trace(g),np.triu(g,1).sum()];np.testing.assert_allclose(d.outcome(),expected,atol=1e-12)
 def test_tail_not_renormalized(self):
  d=ScoreDistribution(8,8);g,t=d.grid(1);self.assertGreater(t,.99);self.assertAlmostEqual(g[0,0],d.probability(0,0))
 def test_infinite_score_support(self):self.assertTrue(math.isfinite(ScoreDistribution(2,1).log_probability(100,100)))
 def test_invalid_inputs(self):
  for rates_ in [(0,1,0),(9,1,0),(1,1,2),(float('nan'),1,0)]:
   with self.assertRaises(ValueError):ScoreDistribution(*rates_)
 def test_invalid_scores(self):
  for h in (-1,1.5,True):
   with self.assertRaises(ValueError):ScoreDistribution(1,1).probability(h,0)
 def test_reliability_known(self):self.assertAlmostEqual(reliability([.2,.2],[0,1])['ece'],.3)
 def test_brier_definition(self):
  m=ConstantPoisson().fit(training());row=training()[:1];metrics,_=evaluate(m,row);p=m.predict('A','B',True).outcome();self.assertAlmostEqual(metrics['brier_1x2'],sum((p-np.array([0,1,0]))**2))
class Models(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows=training();cls.models={k:v().fit(cls.rows) for k,v in MODELS.items()}
 def test_all_converge(self):
  for m in self.models.values():self.assertTrue(m.fit_info['converged'])
 def test_all_valid_score_pmf(self):
  for m in self.models.values():
   d=m.predict('A','B',False);g,t=d.grid();self.assertAlmostEqual(float(g.sum()+t),1,places=12)
 def test_unknown_team_fallback(self):
  for m in self.models.values():self.assertTrue(np.isfinite(m.predict('NEW','B',False).outcome()).all())
 def test_serialization(self):
  with tempfile.TemporaryDirectory() as t:
   for k,m in self.models.items():
    p=Path(t)/'m.json';m.save(p);np.testing.assert_allclose(Base.load(p).predict('A','B',True).outcome(),m.predict('A','B',True).outcome(),atol=0,rtol=0)
 def test_repeatability_and_input_sorting(self):
  for k,m in self.models.items():np.testing.assert_allclose(MODELS[k]().fit(list(reversed(self.rows))).predict('A','B',False).outcome(),m.predict('A','B',False).outcome(),atol=1e-12)
 def test_elo_same_day_batched_updates(self):
  rows=[dict(r,date='2019-01-01') for r in self.rows];a=EloGoals().fit(rows);b=EloGoals().fit([dict(r,id=str(1000-int(r['id']))) for r in reversed(rows)])
  for k in a.ratings:self.assertAlmostEqual(a.ratings[k],b.ratings[k])
 def test_target_mixture_rejected(self):
  rows=self.rows.copy();rows[0]=dict(rows[0],target='final_including_extra_time')
  with self.assertRaises(ValueError):TeamPoisson().fit(rows)
 def test_missing_neutral_rejected(self):
  with self.assertRaises(ValueError):EloGoals().fit([dict(self.rows[0],neutral=None)])
 def test_duplicate_training_rejected(self):
  with self.assertRaises(ValueError):ConstantPoisson().fit(self.rows+[self.rows[0]])
 def test_forecast_rejects_outcomes(self):
  with self.assertRaises(ValueError):predict(self.models['elo'],{'score':'1-0'})
 def test_forecast_rejects_historical_training_date(self):
  with self.assertRaises(ValueError):predict(self.models['elo'],{'date':'2018-01-01'})
 def test_forecast_rejects_target_mismatch(self):
  with self.assertRaises(ValueError):predict(self.models['elo'],{'date':'2022-01-01','target':'provider_final_unknown'})
 def test_split_and_future_label_isolation(self):
  tr,v,te=split(self.rows,'2019-02-01','2019-03-01','2020-01-01');m=EloGoals().fit(tr);a=m.predict('A','B').outcome()
  for r in te:r['home_goals']=99
  np.testing.assert_allclose(EloGoals().fit(tr).predict('A','B').outcome(),a,atol=0,rtol=0)
 def test_downloaded_archive_not_point_in_time(self):
  with self.assertRaises(ValueError):split(self.rows,'2019-02-01','2019-03-01','2020-01-01','point_in_time')
 def test_no_same_day_split(self):
  tr,v,te=split(self.rows,'2019-02-01','2019-03-01','2020-01-01');self.assertLess(max(r['date'] for r in tr),min(r['date'] for r in v));self.assertLess(max(r['date'] for r in v),min(r['date'] for r in te))
