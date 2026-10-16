"""Offline walk-forward from the preserved archive and verified source DB.

No fetching, quotas, wallet or promotion. Inputs retain source snapshot hashes;
today's archive observations are explicitly retrospective, never live history.
"""
import argparse
import json
from pathlib import Path
from engine.queue import Queue
from engine.dataset import build, manifest
from engine.adapters import ADAPTERS
from engine.normalization import normalize
from betting_lab.domain import digest
from .walkforward import evaluate


def snapshot_rows(raw_path='evidence/phase2/raw/openfootball-2025-26.json',
                  metadata_path='reports/experts/source_acceptance_20261016.json'):
    raw=Path(raw_path).read_bytes(); meta=json.loads(Path(metadata_path).read_text())
    if digest(raw)!=meta['raw_sha256']:
        raise ValueError('snapshot_hash_mismatch')
    params={'league':'de.1','season':'2025-26'}; adapter=ADAPTERS['openfootball']
    if meta['source_url']!=adapter.url('collect',params):
        raise ValueError('source_scope_mismatch')
    rows,bad=normalize(adapter,adapter.decode(raw,'collect'),params)
    for r in rows:
        r.update(id=digest(['openfootball',r['competition'],r['date'],r['home'],r['away'],r['target']]),
            observed_at=meta['observed_at'],snapshot_sha256=meta['raw_sha256'],
            snapshot_id=meta['snapshot_id'],source_url=meta['source_url'])
    return rows,{'rejected':len(bad)}


def run(archive, source_db=None):
    historical = json.loads(Path(archive).read_text())
    if source_db:
        q = Queue(Path(source_db))
        try:
            fresh, excluded = build(q.db,'openfootball','de.1',start='2025-07-01',end='2026-07-01')
        finally:q.close()
    else:
        fresh,excluded=snapshot_rows()
    if not fresh:
        raise ValueError('verified_second_season_required')
    rows = historical + fresh
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('duplicate_multiseason_fixture')
    if any(r['target']!='regulation90' or r['competition']!='de.1' for r in rows):
        raise ValueError('competition_or_target_mismatch')
    seasons=sorted({r['season'] for r in rows})
    if len(seasons)<2:
        raise ValueError('multiple_seasons_required')
    rows.sort(key=lambda r:(r['date'],r['id']))
    report=evaluate(rows,[('2025-01-01','2025-03-01','2025-06-01'),
                          ('2025-08-01','2025-11-01','2026-02-01'),
                          ('2025-11-01','2026-02-01','2026-06-01')])
    return dict(schema_version='1.0',dataset=manifest(rows),seasons=seasons,
                excluded=excluded,source_urls=sorted({r['source_url'] for r in rows}),
                walk_forward=report,live_performance=False,champion_promotion=False,
                limitation='Two seasons of one league; retrospective observations, no odds or profitability evidence.')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',default='reports/phase2/bundesliga/dataset.json')
    p.add_argument('--source-db')
    p.add_argument('--out',required=True)
    a=p.parse_args(); report=run(a.archive,a.source_db)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'seasons':report['seasons'],'matches':report['dataset']['count'],
                      'test_matches':report['walk_forward']['unique_test_matches']}))


if __name__=='__main__':main()
