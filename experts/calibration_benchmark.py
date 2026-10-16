"""Standalone, reproducible retrospective challenger report (never promotes)."""
import argparse
import json
from pathlib import Path
from .calibration import ForecastObservation, evaluate_calibration_challenger
from .football import ScoreEngine, digest


def run(rows):
    # Pre-2025 training; Jan/Feb 2025 calibration; Mar+ 2025 untouched test.
    train_before = '2025-01-01T00:00:00+00:00'
    model = ScoreEngine().fit(rows, train_before, 'regulation90').models['poisson']
    cal = [r for r in rows if '2025-01-01' <= r['date'] < '2025-03-01']
    test = [r for r in rows if r['date'] >= '2025-03-01']
    if len(cal) < 30 or not test:
        raise ValueError('dataset_does_not_support_required_holdout')

    def predictions(partition):
        results = []
        for row in sorted(partition, key=lambda r: (r['date'],r['id'])):
            if row['target'] != 'regulation90':
                raise ValueError('score_target_mismatch')
            probabilities = model.predict(row['home'],row['away'],row['neutral']).outcome()
            h,a = row['home_goals'], row['away_goals']
            results.append(ForecastObservation(row['id'],row['date'],
                tuple(float(v) for v in probabilities), 0 if h>a else 1 if h==a else 2))
        return results
    report = evaluate_calibration_challenger(predictions(cal),predictions(test))
    report.update(dataset_sha256=digest(rows), train_before=train_before,
        model='poisson', model_training_matches=model.n_train,
        caveats=['Archive observed in 2026, forecasts reconstructed for 2025; NOT live odds or forward predictions.',
                 'Source archive single Bundesliga season; may not generalize.',
                 'Calibration fits on chronologically separated January/February forecasts; tested on March onward.',
                 'Model was trained only on scores before January 2025.',
                 'No forward pilot, no automatic model promotion, no betting profitability inference.'])
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset', default='reports/phase2/bundesliga/dataset.json')
    parser.add_argument('--out', default='reports/experts/calibration_challenger.json')
    args=parser.parse_args()
    report=run(json.loads(Path(args.dataset).read_text()))
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('calibration_n','test_n','temperature','baseline','challenger')},indent=2))


if __name__=='__main__':main()
