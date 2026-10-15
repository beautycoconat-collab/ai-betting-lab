"""Permission-gated external forecasts; isolated from labels and internal models."""
import json
from datetime import datetime
from betting_lab.domain import aware,digest,utcnow
SCHEMA='''CREATE TABLE IF NOT EXISTS v2_external(id TEXT PRIMARY KEY,source TEXT NOT NULL,match_ref TEXT NOT NULL,observed_at TEXT NOT NULL,published_at TEXT,kickoff_at TEXT NOT NULL,raw_sha256 TEXT NOT NULL,payload TEXT NOT NULL,prematch_verified INTEGER NOT NULL,ensemble_weight REAL NOT NULL DEFAULT 0 CHECK(ensemble_weight=0));'''

def ingest(db,source,payload,registry,clock=utcnow):
    policy=registry[source]
    now=aware(clock())
    if policy.get('status')!='approved' or not policy.get('external_predictions_allowed') or now[:10]>policy['review_expires']:raise ValueError('external_permission_not_verified')
    # A single exact-score selection is not a probability distribution.
    if not payload.get('score_selection') and not payload.get('score_probabilities'):raise ValueError('missing_forecast')
    probabilities=payload.get('score_probabilities')
    if probabilities is not None:
        import math,re
        if not isinstance(probabilities,dict) or not probabilities:raise ValueError('invalid_probability_map')
        if any(not re.fullmatch(r'(0|[1-9]\d*)-(0|[1-9]\d*)',k) or type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for k,v in probabilities.items()):raise ValueError('invalid_probability_map')
        tail=payload.get('other_scores_probability')
        if type(tail) not in (int,float) or not math.isfinite(tail) or tail<0 or abs(sum(probabilities.values())+tail-1)>1e-8:raise ValueError('probability_mass_unknown')
    selection=payload.get('score_selection')
    if selection:
        import re
        if not isinstance(selection,str) or not re.fullmatch(r'(0|[1-9]\d*)-(0|[1-9]\d*)',selection):raise ValueError('invalid_score_selection')
    kickoff=aware(payload['kickoff_at']);published=aware(payload['published_at']) if payload.get('published_at') else None
    if published and published>now:raise ValueError('future_publication')
    if not isinstance(payload.get('source_url'),str) or not payload['source_url'].startswith('https://'):raise ValueError('missing_provenance')
    raw=digest(payload);key=digest([source,payload['match_ref'],raw]);verified=int(now<kickoff and (published is None or published<kickoff))
    db.executescript(SCHEMA)
    with db:db.execute('INSERT OR IGNORE INTO v2_external VALUES(?,?,?,?,?,?,?,?,?,0)',(key,source,payload['match_ref'],now,published,kickoff,raw,json.dumps(payload),verified))
    stored=db.execute('SELECT prematch_verified FROM v2_external WHERE id=?',(key,)).fetchone()
    return {'id':key,'prematch_verified':bool(stored[0]),'ensemble_weight':0.0}
