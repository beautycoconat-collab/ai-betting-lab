"""Motor B: chronological fitting, validation-only stacking, conserved score mass."""
import hashlib
import json
import math
from datetime import date
import numpy as np
from scipy.optimize import minimize
from engine.models import MODELS, ordered
from engine.predict import predict
from .research import aware


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def training_rows(rows, cutoff, target, mode='retrospective'):
    cutoff = aware(cutoff)
    if mode not in ('retrospective', 'prematch'):
        raise ValueError('invalid_mode')
    selected = ordered([r for r in rows if date.fromisoformat(r['date']) < cutoff.date()])
    if selected[0]['target'] != target:
        raise ValueError('score_target_mismatch')
    if mode == 'prematch':
        for row in selected:
            if not row.get('observed_at') or aware(row['observed_at']) > cutoff:
                raise ValueError('training_not_available_at_cutoff')
    return selected


class TeamStrength:
    def analyze(self, rows, cutoff, target, mode='retrospective'):
        rows = training_rows(rows, cutoff, target, mode)
        elo, poisson = MODELS['elo']().fit(rows), MODELS['poisson']().fit(rows)
        teams = {}
        for team in sorted(elo.ratings):
            recent = [r for r in rows if team in (r['home'], r['away'])][-10:]
            points = []
            for r in recent:
                own, other = (r['home_goals'], r['away_goals']) if r['home'] == team else (r['away_goals'], r['home_goals'])
                points.append(3 if own > other else 1 if own == other else 0)
            teams[team] = {'elo': elo.ratings[team], 'attack': poisson.attack[team],
                'defence': poisson.defence[team], 'recent_matches': len(recent),
                'descriptive_points_per_game': sum(points)/len(points),
                'days_since_last_match': (aware(cutoff).date()-date.fromisoformat(recent[-1]['date'])).days,
                'xg': None, 'xga': None, 'xg_status': 'insufficient_data'}
        return {'schema_version': '1.0', 'teams': teams, 'dataset_hash': digest(rows),
                'training_end': elo.training_end, 'mode': mode,
                'form_note': 'PPG is descriptive; opponent correction is in fitted Elo/attack/defence.'}


class ScoreEngine:
    def fit(self, rows, cutoff, target, mode='retrospective'):
        rows = training_rows(rows, cutoff, target, mode)
        self.models = {name: cls().fit(rows) for name, cls in MODELS.items()}
        self.dataset_hash, self.mode = digest(rows), mode
        self.versions = {name: digest([name, model.__dict__, self.dataset_hash]) for name, model in self.models.items()}
        return self

    def forecast(self, fixture):
        return {name: predict(model, fixture) | {'model_version': self.versions[name],
                    'dataset_hash': self.dataset_hash, 'mode': self.mode}
                for name, model in self.models.items()}


class Mixture:
    def __init__(self, distributions, weights):
        self.distributions, self.weights = list(distributions), np.asarray(weights, dtype=float)
        if (not self.distributions or self.weights.shape != (len(self.distributions),)
            or not np.isfinite(self.weights).all() or np.any(self.weights < 0)
            or abs(self.weights.sum()-1) > 1e-8):
            raise ValueError('invalid_mixture_weights')

    def probability(self, h, a):
        return float(sum(w*d.probability(h, a) for w, d in zip(self.weights, self.distributions)))

    def outcome(self):
        return sum(w*d.outcome() for w, d in zip(self.weights, self.distributions))

    def grid(self, max_goals=20):
        pairs = [d.grid(max_goals) for d in self.distributions]
        return (sum(w*g for w, (g, _) in zip(self.weights, pairs)),
                float(sum(w*t for w, (_, t) in zip(self.weights, pairs))))

    def export(self, max_goals=20):
        grid, tail = self.grid(max_goals)
        top = sorted(((float(grid[h, a]), h, a) for h, a in np.ndindex(grid.shape)), reverse=True)[:5]
        return {'grid': grid.tolist(), 'outside_grid_probability': tail, 'p_1x2': self.outcome().tolist(),
                'weights': self.weights.tolist(), 'components': [d.export(max_goals) for d in self.distributions],
                'top_scores': [{'score': f'{h}-{a}', 'probability': p} for p, h, a in top]}


class Synthesizer:
    def fit(self, models, validation):
        validation = ordered(validation)
        self.models = dict(models)
        if not self.models:
            raise ValueError('no_models')
        for model in self.models.values():
            if model.training_end >= validation[0]['date'] or model.target != validation[0]['target']:
                raise ValueError('validation_leakage_or_target')
        columns = np.array([[m.predict(r['home'], r['away'], r['neutral']).probability(r['home_goals'], r['away_goals'])
                             for r in validation] for m in self.models.values()]).T
        groups = []
        for i in range(columns.shape[1]):
            group = next((g for g in groups if np.array_equal(columns[:, i], columns[:, g[0]])), None)
            if group is None:
                groups.append([i])
            else:
                group.append(i)
        reduced = columns[:, [g[0] for g in groups]]
        fit = minimize(lambda w: -np.log(np.maximum(reduced @ w, 1e-300)).mean(),
                       np.full(len(groups), 1/len(groups)), method='SLSQP',
                       bounds=[(0, 1)]*len(groups), constraints=[{'type': 'eq', 'fun': lambda w: w.sum()-1}],
                       options={'ftol': 1e-12, 'maxiter': 500})
        if not fit.success or not math.isfinite(fit.fun):
            raise ValueError('ensemble_fit_failed')
        self.weights = np.zeros(len(self.models))
        for weight, group in zip(fit.x, groups):
            self.weights[group] = weight/len(group)
        self.validation_end = validation[-1]['date']
        self.validation_hash = digest(validation)
        self.validation_observed_end = max(aware(r['observed_at']) for r in validation) if all(r.get('observed_at') for r in validation) else None
        self.groups = groups
        return self

    def forecast(self, fixture):
        if fixture['date'] <= self.validation_end:
            raise ValueError('fixture_overlaps_validation')
        for model in self.models.values():
            predict(model, fixture)
        return Mixture([m.predict(fixture['home'], fixture['away'], fixture['neutral']) for m in self.models.values()], self.weights)

    def report(self):
        return {'weights': dict(zip(self.models, self.weights.tolist())), 'duplicate_groups': self.groups,
                'validation_end': self.validation_end, 'validation_hash': self.validation_hash,
                'dependence': 'shared training data; not independent evidence',
                'calibration_status': 'requires held-out evaluation; stacking does not prove calibration'}


class MarketSpecialist:
    def calculate(self, distribution, market, line=None):
        if market.startswith('half'):
            return {'status': 'insufficient_data', 'probability': None}
        if market == '1X2':
            return {'status': 'supported', 'probabilities': distribution.outcome().tolist()}
        if market not in ('over', 'under', 'btts', 'home_handicap'):
            return {'status': 'unsupported', 'probability': None}
        grid, tail = distribution.grid(100)
        h, a = np.indices(grid.shape)
        if market == 'btts':
            return {'status': 'supported', 'probability': float(grid[(h > 0) & (a > 0)].sum()),
                    'absolute_error_bound': tail}
        if line is None or not math.isfinite(line) or line*2 != int(line*2) or abs(line) > 20:
            raise ValueError('unsupported_line')
        margin = h-a+line if market == 'home_handicap' else h+a-line
        if market == 'under':
            margin = -margin
        return {'status': 'supported', 'win': float(grid[margin > 0].sum()),
                'push': float(grid[margin == 0].sum()), 'lose': float(grid[margin < 0].sum()),
                'absolute_error_bound': tail}
