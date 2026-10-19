"""Opt-in projection of persisted worker output, never a live publication gate.

Reads only. All 4 immutable inputs, dependency edges, versions, fixture and cutoff
must agree. Legacy output without display fields remains an explicit empty state.
Research evidence is NOT promoted to network-verified or real-time performance.
"""
import json
from datetime import datetime, timezone
from pydantic import ValidationError
from dashboard.contracts import ModelSummary
from experts.contracts import Fixture, Finding
from experts.dispatcher import TaskOutput
from experts.football import digest
from experts.research import aware
from experts.worker_pipeline import ROLES
from foundation.contracts import JobRequest


def _chain(db, terminal, now):
    chain = []
    task_id = terminal
    for expected in ('referee', 'red_team', 'model', 'validate'):
        r = db.execute('''SELECT t.id,t.kind,t.status,t.body request,i.body input,o.body output
            FROM f_tasks t JOIN expert_task_inputs i ON i.task_id=t.id
            JOIN expert_task_outputs o ON o.task_id=t.id WHERE t.id=?''', (task_id,)).fetchone()
        if not r or r['kind'] != expected or r['status'] != 'done':
            raise ValueError('incomplete_worker_chain')
        job = JobRequest.model_validate_json(r['request'])
        out = TaskOutput.model_validate_json(r['output'])
        body = json.loads(r['input'])
        fixture = Fixture.model_validate(body['fixture'])
        cutoff = aware(body['as_of'])
        if (job.kind != expected or body.get('mode') not in ('retrospective','prematch')
            or out.status != 'ready' or out.data.get('stage') != expected
            or out.data.get('input_hash') != digest(body)
            or str(job.fixture_id) != str(fixture.id)
            or not cutoff < fixture.kickoff_at or cutoff > now):
            raise ValueError('worker_provenance_mismatch')
        chain.append((r, out.data, body, fixture))
        edges = [x[0] for x in db.execute('SELECT depends_on FROM f_task_dependencies WHERE task_id=?', (task_id,))]
        if expected == 'validate':
            if edges: raise ValueError('unexpected_validator_dependency')
        elif len(edges) != 1:
            raise ValueError('ambiguous_worker_dependency')
        else:
            task_id = edges[0]
    if len({digest(c[2]) for c in chain}) != 1:
        raise ValueError('mixed_worker_inputs')
    ref, red, mod, val = [x[1] for x in chain]
    if not (ref.get('prediction_id') == red.get('prediction_id') == mod.get('prediction_id')):
        raise ValueError('mixed_prediction_versions')
    if val.get('verification', {}).get('status') != 'ready':
        raise ValueError('validation_not_ready')
    fixture = chain[0][3]
    models = {}
    for name, model in mod.get('models', {}).items():
        if name not in ('baseline', 'elo', 'poisson', 'dixon_coles', 'ensemble'):
            raise ValueError('unknown_model')
        parsed = ModelSummary.model_validate(model)
        if parsed.training_end >= fixture.kickoff_at.date().isoformat():
            raise ValueError('training_time_leakage')
        if name != 'ensemble' and parsed.model_sha256 != mod['versions'].get(name):
            raise ValueError('model_version_mismatch')
        models[name] = parsed.model_dump(mode='json')
    if models:
        if mod.get('display_schema_version') != '1.0' or 'ensemble' not in models:
            raise ValueError('invalid_display_schema')
        if any(abs(a-b)>1e-8 for a,b in zip(models['ensemble']['p_1x2'],mod['probabilities'])):
            raise ValueError('display_probability_mismatch')
    findings = [Finding.model_validate(x).model_dump(mode='json') for x in red.get('findings', [])]
    # Only fixed verdict fields. Arbitrary reasons, source/news bodies never exported.
    reviews = []
    for v in ref.get('review_history', []):
        if v.get('status') not in ('approved','needs_reanalysis','insufficient_evidence','rejected','abstain') or v.get('round_no') not in (1,2):
            raise ValueError('invalid_review')
        if v.get('risk_action') not in ('wait','skip'):
            raise ValueError('invalid_review_risk_action')
        reviews.append({k:v[k] for k in ('status','round_no','risk_action')})
    if len(reviews) > 2: raise ValueError('review_round_limit')
    if reviews and (reviews[-1]['status'] != ref.get('verdict',{}).get('status')
        or [r['round_no'] for r in reviews] != list(range(1,len(reviews)+1))):
        raise ValueError('review_history_mismatch')
    # Do not copy unvalidated market dictionaries from worker storage.
    # Markets are shown only through the validated numeric output allowlist.
    markets = {}
    for name, value in mod.get('markets', {}).items():
        if name not in {'btts','half1'} | {f'{k}_{l}' for k in ('over','under','home_over','away_over') for l in (0.5,1.5,2.5,3.5,4.5,5.5)}:
            raise ValueError('unknown_market')
        status = value.get('status')
        if status not in ('supported','insufficient_data','unsupported'):
            raise ValueError('invalid_market_status')
        clean = {'status':status}
        for k in ('probability','win','push','lose','absolute_error_bound'):
            if k in value and value[k] is not None:
                n = value[k]
                if type(n) not in (int,float) or not 0 <= n <= 1:
                    raise ValueError('invalid_market_probability')
                clean[k]=n
        if status == 'supported' and all(k in clean for k in ('win','push','lose')) and abs(sum(clean[k] for k in ('win','push','lose'))-1) > 1e-8:
            raise ValueError('invalid_market_mass')
        markets[name]=clean
    return dict(id=mod['prediction_id'], fixture_id=str(fixture.id),
        home=fixture.home, away=fixture.away, kickoff_at=fixture.kickoff_at.isoformat(),
        date=fixture.kickoff_at.date().isoformat(), target=fixture.target,
        competition=fixture.competition, season=fixture.season, mode='recorded_research',
        origin_mode=chain[0][2]['mode'], as_of=chain[0][2]['as_of'],
        evidence_status='local_record_unverified', models=models, markets=markets,
        market_model='ensemble' if models else None,
        findings=findings, reviews=reviews, review_status=ref.get('verdict',{}).get('status','no_record'),
        roles=[{'id':ROLES[x[0]['kind']], 'status':'done', 'task_id':x[0]['id']} for x in reversed(chain)],
        reliability='Yerel worker kaydı. Kaynakların canlı kabulü ve maç öncesi yayın kanıtı ayrıca doğrulanmalıdır.',
        execution_enabled=False)


def read_research(db, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('timezone_required')
    required = {'f_tasks','expert_task_inputs','expert_task_outputs','f_task_dependencies'}
    if not required <= {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
        return {'status':'insufficient_data','records':[], 'rejected_records':0}
    records, rejected = [], 0
    for row in db.execute("SELECT id FROM f_tasks WHERE kind='referee' AND status='done' ORDER BY id LIMIT 100"):
        try:
            records.append(_chain(db,row[0],now))
        except (ValueError,KeyError,TypeError,ValidationError):
            rejected += 1  # No exception text: it can contain input values.
    return {'status':'available' if records else 'insufficient_data',
            'records':records,'rejected_records':rejected}
