"""Build an explicitly public, bounded projection of existing engine artifacts.

No raw audit bodies, DB credentials, tasks, or arbitrary evidence text are copied.
A runtime database is opened read-only; missing data stays missing.
"""
import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from foundation.roles import registry
from engine.models import Base
from engine.predict import predict
from experts.football import MarketSpecialist

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def artifact(path, root):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(raw).hexdigest()}


def build(root=ROOT, database=None, now=None, include_research=False):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('timezone_required')
    output = {'schema_version': '1.0', 'generated_at': now.isoformat(),
        'timezone': 'Europe/Istanbul', 'execution_enabled': False, 'pilot_enabled': False,
        'connection': 'published_artifact', 'fixtures': [], 'history': [], 'performance': None,
        'portfolio': {'status': 'blocked', 'balance': None, 'roi': None, 'clv': None,
                      'reason': 'İleriye dönük portföy bağlantısı ve güvenlik kabulü tamamlanmadı.'},
        'roles': [{k: r[k] for k in ('id', 'ordinal', 'name', 'engine')} | {'status': 'no_run'} for r in registry()],
        'research': {'status':'not_requested','records':[], 'rejected_records':0},
        'provenance': [], 'warnings': ['Pilot kapalı. Panel salt okunur.',
            'Arşiv tahminleri bugün yeniden hesaplanan tarihsel araştırmadır; canlı başarı değildir.']}
    folder = root / 'reports/phase2/bundesliga'
    if (folder/'dataset.json').exists():
        rows = read(folder/'dataset.json')
        models = {n: Base.load(folder/f'{n}.model.json') for n in ('baseline', 'elo', 'poisson', 'dixon_coles')}
        test = [r for r in rows if r['date'] >= '2025-03-01']
        for row in test[:18]:
            f = {k: row[k] for k in ('date', 'home', 'away', 'neutral', 'target')}
            forecasts = {}
            for name, model in models.items():
                p = predict(model, f)
                d = p['distribution']
                forecasts[name] = {'p_1x2': d['p_1x2'], 'top_scores': d['top_scores'],
                    'outside_grid_probability': d['outside_grid_probability'],
                    'training_end': p['training_end'], 'model_sha256': artifact(folder/f'{name}.model.json', root)['sha256']}
            dist = models['poisson'].predict(f['home'], f['away'], f['neutral'])
            markets = {f'{kind}_{line}': MarketSpecialist().calculate(dist, kind, line)
                for kind in ('over', 'under', 'home_over', 'away_over') for line in (0.5, 1.5, 2.5, 3.5, 4.5, 5.5)}
            markets['btts'] = MarketSpecialist().calculate(dist, 'btts')
            markets['half1'] = {'status': 'insufficient_data', 'probability': None}
            output['history'].append({'id': row['id'], **f, 'competition': 'Bundesliga', 'season': '2024–25',
                'mode': 'retrospective', 'kickoff_at': None, 'source_url': row['source_url'],
                'observed_at': row['observed_at'], 'snapshot_sha256': row['snapshot_sha256'],
                'models': forecasts, 'markets': markets, 'market_model': 'poisson',
                'result': {'home': row['home_goals'], 'away': row['away_goals']},
                'findings': [], 'reviews': [], 'review_status': 'no_record', 'roles': [],
                'reliability': 'Canlı kalibrasyon doğrulanmadı. Kesinlik puanı üretilmez.'})
        output['provenance'] += [artifact(folder/'dataset.json', root)]
        output['provenance'] += [artifact(folder/f'{n}.model.json', root) for n in models]
    report = root/'reports/experts/benchmark.json'
    if report.exists():
        b = read(report)
        output['performance'] = {'mode': 'retrospective', 'n': b['test_n'],
            'training_end': b['training_end'], 'test_start': b['test_start'],
            'metrics': b['metrics'], 'limitations': b['limitations']}
        output['provenance'].append(artifact(report, root))
    if database:
        # URI mode=ro cannot silently create a DB or mutate existing state.
        db = sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        try:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'f_fixtures' in tables:
                for row in db.execute('SELECT id,home,away,kickoff_at,target FROM f_fixtures ORDER BY kickoff_at LIMIT 500'):
                    f = dict(row)
                    datetime.fromisoformat(f['kickoff_at'])  # never invent a kickoff
                    output['fixtures'].append(f | {'mode': 'unverified', 'models': {}, 'markets': {},
                        'roles': [], 'findings': [], 'reviews': [], 'review_status': 'no_record',
                        'reliability': 'Fikstür kaydı mevcut; yayımlanabilir tahmin ve kaynak doğrulaması yok.'})
            # Only fixture identity is projected. Audit/free-text payloads need an explicit publication contract.
            if include_research:
                from dashboard.research_feed import read_research
                output['research'] = read_research(db, now)
            output['connection'] = 'local_readonly_projection'
        finally:
            db.close()
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--include-research', action='store_true', help='Explicitly opt in to public research display; no raw input bodies.'); p.add_argument('--database'); p.add_argument('--out', default='public/data/dashboard.json')
    a = p.parse_args()
    data = build(database=a.database, include_research=a.include_research)
    path = Path(a.out); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n')
    print(json.dumps({'output': str(path), 'fixtures': len(data['fixtures']), 'historical': len(data['history'])}))


if __name__ == '__main__':
    main()
