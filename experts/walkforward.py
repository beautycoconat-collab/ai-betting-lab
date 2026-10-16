"""Expanding-window, non-overlapping test folds; retrospective only."""
from datetime import date
from .football import ScoreEngine, Synthesizer, digest
from .portfolio import LearningAuditor


def evaluate(rows, folds, target='regulation90'):
    if not folds:
        raise ValueError('no_folds')
    reports, distributions, labels, used = [], [], [], set()
    for train_before, test_start, test_end in folds:
        dates = [date.fromisoformat(d) for d in (train_before, test_start, test_end)]
        if not dates[0] < dates[1] < dates[2]:
            raise ValueError('invalid_fold_dates')
        validation = [r for r in rows if train_before <= r['date'] < test_start]
        test = [r for r in rows if test_start <= r['date'] < test_end]
        if not test or any(r['id'] in used for r in test):
            raise ValueError('empty_or_overlapping_test_fold')
        if any(r['target'] != target for r in test):
            raise ValueError('test_target_mismatch')
        engine = ScoreEngine().fit(rows, train_before+'T00:00:00+00:00', target)
        synth = Synthesizer().fit(engine.models, validation)
        current = [synth.forecast({k: r[k] for k in ('date', 'home', 'away', 'neutral', 'target')}) for r in test]
        outcomes = [(r['home_goals'], r['away_goals']) for r in test]
        baseline = [engine.models['baseline'].predict(r['home'], r['away'], r['neutral']) for r in test]
        reports.append({'train_before': train_before, 'test_start': test_start, 'test_end_exclusive': test_end,
            'train_n': engine.models['baseline'].n_train, 'validation_n': len(validation), 'test_n': len(test),
            'training_hash': engine.dataset_hash, 'validation_hash': synth.validation_hash, 'test_hash': digest(test),
            'weights': synth.report()['weights'], 'ensemble': LearningAuditor().evaluate(current, outcomes),
            'baseline': LearningAuditor().evaluate(baseline, outcomes)})
        used.update(r['id'] for r in test)
        distributions.extend(current)
        labels.extend(outcomes)
    seasons = sorted({str(r.get('season','unknown')) for r in rows})
    return {'mode': 'retrospective', 'folds': reports, 'unique_test_matches': len(used),
            'seasons': seasons,
            'pooled_ensemble': LearningAuditor().evaluate(distributions, labels),
            'limitation': 'reconstructed historical observations; no live available-at-the-time guarantee'}
