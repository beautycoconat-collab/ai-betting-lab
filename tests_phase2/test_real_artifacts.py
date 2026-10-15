"""Read-only acceptance checks against shipped REAL historical evidence."""
import unittest,json,hashlib,tempfile
from pathlib import Path
import numpy as np
from engine.models import Base
from engine.dataset import split,manifest
from engine.predict import predict
from engine.queue import Queue
from engine.bootstrap import restore
ROOT=Path(__file__).resolve().parents[1]
class RealEvidence(unittest.TestCase):
 def test_original_raw_hashes(self):
  for r in json.loads((ROOT/'evidence/phase2/snapshot-index.json').read_text()):self.assertEqual(hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
 def test_fold_hashes_and_no_overlap(self):
  for name,cuts in [('international',('2020-01-01','2022-01-01','2024-01-01')),('bundesliga',('2025-01-01','2025-03-01','2025-06-01'))]:
   directory=ROOT/'reports/phase2'/name;rows=json.loads((directory/'dataset.json').read_text());report=json.loads((directory/'evaluation.json').read_text());parts=split(rows,*cuts)
   for key,part in zip(('train','validation','test'),parts):self.assertEqual(manifest(part)['sha256'],report['splits'][key]['sha256'])
   sets=[{r['id'] for r in part} for part in parts];self.assertFalse(sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
 def test_real_predictions_replay_from_saved_model(self):
  for name in ('international','bundesliga'):
   directory=ROOT/'reports/phase2'/name
   for kind in ('baseline','elo','poisson','dixon_coles'):
    model=Base.load(directory/(kind+'.model.json'));preds=json.loads((directory/(kind+'.predictions.json')).read_text())
    for r in [preds[0],preds[len(preds)//2],preds[-1]]:
     self.assertNotIn('home_goals',r);self.assertNotIn('away_goals',r);self.assertLess(model.training_end,r['date'])
     expected=model.predict(r['home'],r['away'],r['neutral']).export();np.testing.assert_allclose(expected['grid'],r['distribution']['grid'],atol=0,rtol=1e-15)
     self.assertAlmostEqual(np.sum(r['distribution']['grid'])+r['distribution']['outside_grid_probability'],1,places=11)
 def test_selection_uses_validation_only(self):
  for name in ('international','bundesliga'):
   r=json.loads((ROOT/'reports/phase2'/name/'evaluation.json').read_text());self.assertEqual(r['validation_selected_model'],min(r['models'],key=lambda k:r['models'][k]['validation']['score_log_loss']))
 def test_offline_restore_idempotent_and_budget_preserving(self):
  with tempfile.TemporaryDirectory() as temp:
   q=Queue(Path(temp)/'db.sqlite')
   try:
    before=q.db.execute('select count(*) from requests').fetchone()[0];first=restore(q);counts1=q.db.execute('select count(*) from v2_results').fetchone()[0];second=restore(q);counts2=q.db.execute('select count(*) from v2_results').fetchone()[0]
    self.assertEqual(counts1,counts2);self.assertEqual(counts1,49943+306+64);self.assertEqual(q.db.execute('select count(*) from requests').fetchone()[0],before);self.assertTrue(all(r['network_requests']==0 for r in second))
   finally:q.close()
