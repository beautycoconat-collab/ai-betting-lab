"""Reproducible chronological real-data benchmark; never claims live performance."""
import argparse
import json
from pathlib import Path
from .football import ScoreEngine, Synthesizer, TeamStrength, digest
from .portfolio import LearningAuditor
from .workflow import StrategyExperiments
from .walkforward import evaluate as walk_forward


def run(dataset):
    rows = json.loads(Path(dataset).read_text())
    train_end = '2025-01-01T00:00:00+00:00'
    engine = ScoreEngine().fit(rows, train_end, 'regulation90')
    validation = [r for r in rows if '2025-01-01' <= r['date'] < '2025-03-01']
    test = [r for r in rows if r['date'] >= '2025-03-01']
    synthesizer = Synthesizer().fit(engine.models, validation)
    metrics = {}
    labels = [(r['home_goals'], r['away_goals']) for r in test]
    for name, model in engine.models.items():
        metrics[name] = LearningAuditor().evaluate([model.predict(r['home'], r['away'], r['neutral']) for r in test], labels)
    experiment = StrategyExperiments().evaluate(synthesizer, test)
    first = {k: test[0][k] for k in ('date', 'home', 'away', 'neutral', 'target')}
    return {'mode': 'retrospective', 'dataset_sha256': digest(rows),
        'source_urls': sorted({r['source_url'] for r in rows}),
        'source_snapshot_hashes': sorted({r['snapshot_sha256'] for r in rows}),
        'observed_at': sorted({r['observed_at'] for r in rows}),
        'train_n': next(iter(engine.models.values())).n_train, 'validation_n': len(validation), 'test_n': len(test),
        'training_end': max(m.training_end for m in engine.models.values()),
        'validation_end': synthesizer.validation_end, 'test_start': test[0]['date'],
        'model_versions': engine.versions, 'metrics': metrics | {'ensemble': experiment['metrics']},
        'ensemble_validation': synthesizer.report(),
        'team_strength': TeamStrength().analyze(rows, train_end, 'regulation90'),
        'held_out_example': {'fixture': first, 'prediction': synthesizer.forecast(first).export(),
            'observed_result_separate': {'home_goals': test[0]['home_goals'], 'away_goals': test[0]['away_goals']}},
        'walk_forward': walk_forward(rows, [('2025-01-01', '2025-02-01', '2025-03-01'),
            ('2025-02-01', '2025-03-01', '2025-04-01'), ('2025-03-01', '2025-04-01', '2025-06-01')]),
        'limitations': ['single season holdout and expanding-window walk-forward, not independent multi-season validation',
            'archive observed in 2026, predictions reconstructed retrospectively',
            'no exact historical kickoff time supplied or invented',
            'no verified odds; no ROI or CLV', 'no proof of profitability or calibrated live performance']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='reports/phase2/bundesliga/dataset.json')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    report = run(args.dataset)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    print(json.dumps({'train': report['train_n'], 'validation': report['validation_n'], 'test': report['test_n'],
        'logloss': {k: v['score_logloss'] for k, v in report['metrics'].items()}}))


if __name__ == '__main__':
    main()
