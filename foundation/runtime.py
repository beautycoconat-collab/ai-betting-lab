"""Local deterministic foundation. SQLite file access is a trusted-process boundary.

Production authorization is implemented by PostgreSQL roles in migration 003.
The source Queue and its quota ledger are reused, never copied or reset.
"""
import json
import hashlib
from uuid import uuid4
from datetime import datetime, timedelta
from contextlib import contextmanager
from engine.queue import Queue
from .contracts import AgentMessage, Evidence, JobRequest, Role, ReviewDecision, utcnow

JOB_ROLES = {'collect':'source_hunter','validate':'data_validator','model':'score_engine',
             'red_team':'red_team','referee':'scientific_referee','reanalysis':'score_engine',
             'save_prediction':'score_engine','settle':'risk_manager'}

SCHEMA = '''
CREATE TABLE IF NOT EXISTS f_fixtures(id TEXT PRIMARY KEY,kickoff_at TEXT NOT NULL,target TEXT NOT NULL,home TEXT NOT NULL,away TEXT NOT NULL,CHECK(home<>away));
CREATE TABLE IF NOT EXISTS f_runs(id TEXT PRIMARY KEY,role TEXT NOT NULL,fixture_id TEXT NOT NULL REFERENCES f_fixtures,as_of TEXT NOT NULL,mode TEXT NOT NULL CHECK(mode IN ('prematch','retrospective')));
CREATE TABLE IF NOT EXISTS f_evidence(id TEXT PRIMARY KEY,fixture_id TEXT NOT NULL REFERENCES f_fixtures,snapshot_id TEXT NOT NULL REFERENCES v2_snapshots,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS f_model_versions(id TEXT PRIMARY KEY,model_hash TEXT NOT NULL UNIQUE,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS f_messages(id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES f_runs,fixture_id TEXT NOT NULL REFERENCES f_fixtures,model_version_id TEXT REFERENCES f_model_versions,body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS f_message_evidence(message_id TEXT REFERENCES f_messages,evidence_id TEXT REFERENCES f_evidence,PRIMARY KEY(message_id,evidence_id));
CREATE TABLE IF NOT EXISTS f_findings(id TEXT PRIMARY KEY,message_id TEXT UNIQUE NOT NULL REFERENCES f_messages,severity TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS f_review_state(fixture_id TEXT PRIMARY KEY REFERENCES f_fixtures,rounds INTEGER NOT NULL DEFAULT 0 CHECK(rounds BETWEEN 0 AND 2),status TEXT NOT NULL DEFAULT 'pending',risk_action TEXT NOT NULL DEFAULT 'wait');
CREATE TABLE IF NOT EXISTS f_decisions(id TEXT PRIMARY KEY,request_key TEXT UNIQUE NOT NULL,request_payload TEXT NOT NULL,finding_id TEXT NOT NULL REFERENCES f_findings,reviewer_run_id TEXT NOT NULL REFERENCES f_runs,round_no INTEGER NOT NULL CHECK(round_no BETWEEN 1 AND 2),status TEXT NOT NULL,risk_action TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS f_reanalysis(id TEXT PRIMARY KEY,decision_id TEXT UNIQUE NOT NULL REFERENCES f_decisions,fixture_id TEXT NOT NULL REFERENCES f_fixtures,status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS f_tasks(id TEXT PRIMARY KEY,request_key TEXT UNIQUE NOT NULL,body TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,max_attempts INTEGER NOT NULL,timeout INTEGER NOT NULL,not_before TEXT NOT NULL,lease_until TEXT,lease_token TEXT,worker_id TEXT,last_error TEXT);
CREATE TABLE IF NOT EXISTS f_task_dependencies(task_id TEXT REFERENCES f_tasks,depends_on TEXT REFERENCES f_tasks,PRIMARY KEY(task_id,depends_on),CHECK(task_id<>depends_on));
CREATE TABLE IF NOT EXISTS f_task_attempts(id INTEGER PRIMARY KEY,task_id TEXT NOT NULL REFERENCES f_tasks,token TEXT NOT NULL UNIQUE,worker_id TEXT NOT NULL,started_at TEXT NOT NULL,lease_until TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS f_prediction_revisions(id TEXT PRIMARY KEY,fixture_id TEXT NOT NULL REFERENCES f_fixtures,model_hash TEXT NOT NULL,model_version_id TEXT NOT NULL REFERENCES f_model_versions,revision INTEGER NOT NULL,previous_id TEXT REFERENCES f_prediction_revisions,created_at TEXT NOT NULL,body TEXT NOT NULL,UNIQUE(fixture_id,revision));
CREATE TABLE IF NOT EXISTS f_audit(seq INTEGER PRIMARY KEY,at TEXT NOT NULL,event TEXT NOT NULL,body TEXT NOT NULL,previous_hash TEXT NOT NULL,entry_hash TEXT NOT NULL UNIQUE);
'''

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

class Runtime:
    def __init__(self, path, *, clock=utcnow, registry=None):
        self.queue=Queue(path,registry);self.db=self.queue.db;self.clock=clock
        self.max_db_bytes=40_000_000
        self.db.executescript(SCHEMA)
        for table in ('f_runs','f_evidence','f_model_versions','f_messages','f_message_evidence','f_findings','f_decisions','f_reanalysis','f_task_attempts','f_prediction_revisions','f_audit'):
            for action in ('UPDATE','DELETE'):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append_only'); END")
        self.db.commit()

    @contextmanager
    def transaction(self):
        if self.queue.store.path.stat().st_size>self.max_db_bytes:
            raise ValueError('local_storage_budget')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def audit(self,event,body):
        old=self.db.execute('SELECT entry_hash FROM f_audit ORDER BY seq DESC LIMIT 1').fetchone()
        previous=old[0] if old else '0'*64;at=self.clock();payload=canonical(body)
        h=hashlib.sha256(canonical([previous,at,event,payload]).encode()).hexdigest()
        self.db.execute('INSERT INTO f_audit(at,event,body,previous_hash,entry_hash) VALUES(?,?,?,?,?)',(at,event,payload,previous,h))

    def verify_audit(self):
        previous='0'*64
        for r in self.db.execute('SELECT * FROM f_audit ORDER BY seq'):
            h=hashlib.sha256(canonical([previous,r['at'],r['event'],r['body']]).encode()).hexdigest()
            if previous!=r['previous_hash'] or h!=r['entry_hash']:return False
            previous=h
        return True

    def fixture(self,fixture_id,kickoff_at,target,home,away):
        from .contracts import Target
        from pydantic import TypeAdapter
        TypeAdapter(Target).validate_python(target)
        if datetime.fromisoformat(kickoff_at).tzinfo is None:raise ValueError('timezone_required')
        with self.transaction():
            self.db.execute('INSERT INTO f_fixtures VALUES(?,?,?,?,?)',(str(fixture_id),kickoff_at,target,home,away))
            self.db.execute('INSERT INTO f_review_state(fixture_id) VALUES(?)',(str(fixture_id),))
            self.audit('fixture_registered',{'id':str(fixture_id),'target':target})

    def start_run(self,role,fixture_id,mode='prematch',as_of=None):
        role=Role(role).value;fid=str(fixture_id);as_of=as_of or self.clock()
        fixture=self.db.execute('SELECT * FROM f_fixtures WHERE id=?',(fid,)).fetchone()
        if not fixture:raise ValueError('unknown_fixture')
        if datetime.fromisoformat(as_of)>datetime.fromisoformat(self.clock()):raise ValueError('future_run')
        if mode=='prematch' and datetime.fromisoformat(as_of)>=datetime.fromisoformat(fixture['kickoff_at']):raise ValueError('kickoff_passed')
        run=str(uuid4())
        with self.transaction():
            self.db.execute('INSERT INTO f_runs VALUES(?,?,?,?,?)',(run,role,fid,as_of,mode));self.audit('run_started',{'id':run,'role':role})
        return run

    def add_evidence(self,value):
        e=Evidence.model_validate(value);body=e.model_dump(mode='json');fid=str(e.fixture_id)
        snapshot=self.db.execute('SELECT * FROM v2_snapshots WHERE id=?',(e.snapshot_id,)).fetchone()
        fixture=self.db.execute('SELECT * FROM f_fixtures WHERE id=?',(fid,)).fetchone()
        if not snapshot or snapshot['source']!=e.source_id or snapshot['url']!=e.source_url:raise ValueError('missing_or_mismatched_provenance')
        if e.observed_at!=datetime.fromisoformat(snapshot['observed_at']):raise ValueError('observation_time_mismatch')
        if not fixture or fixture['target']!=e.score_target:raise ValueError('target_mismatch')
        if e.observed_at>datetime.fromisoformat(self.clock()):raise ValueError('future_evidence')
        policy=self.queue.registry.get(e.source_id,{})
        if policy.get('status')!='approved' or self.clock()[:10]>policy.get('review_expires',''):raise ValueError('source_not_approved')
        with self.transaction():
            self.db.execute('INSERT INTO f_evidence VALUES(?,?,?,?)',(str(e.evidence_id),fid,e.snapshot_id,canonical(body)))
            self.audit('evidence_added',body)
        return str(e.evidence_id)

    def message(self,value):
        m=AgentMessage.model_validate(value);body=canonical(m.model_dump(mode='json'));mid=str(m.message_id)
        if len(body.encode())>16384:raise ValueError('message_storage_limit')
        with self.transaction():
            prior=self.db.execute('SELECT body FROM f_messages WHERE id=?',(mid,)).fetchone()
            if prior:
                if prior[0]!=body:raise ValueError('idempotency_conflict')
                return mid
            run=self.db.execute('SELECT * FROM f_runs WHERE id=?',(str(m.agent_run_id),)).fetchone()
            if not run or run['role']!=m.agent_role.value or run['fixture_id']!=str(m.fixture_id):raise ValueError('role_or_fixture_mismatch')
            if m.created_at>datetime.fromisoformat(self.clock()) or m.created_at<datetime.fromisoformat(run['as_of']):raise ValueError('message_time_mismatch')
            evidence=[]
            for eid in m.evidence_ids:
                row=self.db.execute('SELECT * FROM f_evidence WHERE id=?',(str(eid),)).fetchone()
                if not row or row['fixture_id']!=str(m.fixture_id):raise ValueError('missing_or_wrong_fixture_evidence')
                e=Evidence.model_validate_json(row['body'])
                if run['mode']=='prematch' and e.observed_at>datetime.fromisoformat(run['as_of']):raise ValueError('future_features')
                evidence.append(e)
            if set(m.input_snapshot_ids)!={e.snapshot_id for e in evidence}:raise ValueError('snapshot_evidence_mismatch')
            if m.model_version_id and not self.db.execute('SELECT 1 FROM f_model_versions WHERE id=?',(str(m.model_version_id),)).fetchone():raise ValueError('unknown_model_version')
            self.db.execute('INSERT INTO f_messages VALUES(?,?,?,?,?)',(mid,str(m.agent_run_id),str(m.fixture_id),str(m.model_version_id) if m.model_version_id else None,body))
            for e in evidence:self.db.execute('INSERT INTO f_message_evidence VALUES(?,?)',(mid,str(e.evidence_id)))
            if m.agent_role in (Role.red_team,Role.data_validator):
                self.db.execute('INSERT INTO f_findings VALUES(?,?,?)',(mid,mid,m.severity))
            self.audit('message_accepted',m.model_dump(mode='json'))
        return mid

    def review(self,finding_id,reviewer_run_id,key,*,resolution_evidence_ids=()):
        """Fail closed: high/critical findings require new verified evidence.
        At most two decisions per fixture; unresolved second review abstains/skips.
        """
        payload=canonical({'finding':finding_id,'run':reviewer_run_id,'evidence':sorted(resolution_evidence_ids)})
        with self.transaction():
            old=self.db.execute('SELECT * FROM f_decisions WHERE request_key=?',(key,)).fetchone()
            if old:
                if old['request_payload']!=payload:raise ValueError('idempotency_conflict')
                return self.review_record(old)
            f=self.db.execute('SELECT f.*,m.fixture_id,m.body FROM f_findings f JOIN f_messages m ON m.id=f.message_id WHERE f.id=?',(finding_id,)).fetchone()
            run=self.db.execute('SELECT * FROM f_runs WHERE id=?',(reviewer_run_id,)).fetchone()
            if not f or not run or run['role']!='scientific_referee' or run['fixture_id']!=f['fixture_id']:raise ValueError('referee_permission')
            state=self.db.execute('SELECT * FROM f_review_state WHERE fixture_id=?',(f['fixture_id'],)).fetchone()
            if state['rounds']>=2 or state['risk_action']=='skip':raise ValueError('review_limit')
            original=json.loads(f['body']);resolved=bool(resolution_evidence_ids)
            for eid in resolution_evidence_ids:
                row=self.db.execute('SELECT body FROM f_evidence WHERE id=? AND fixture_id=?',(eid,f['fixture_id'])).fetchone()
                if not row:raise ValueError('resolution_evidence_missing')
                e=Evidence.model_validate_json(row[0])
                if e.quality!='verified' or eid in original['evidence_ids'] or e.observed_at>datetime.fromisoformat(run['as_of']):raise ValueError('resolution_not_verified')
            number=state['rounds']+1
            status='approved' if resolved else ('abstain' if number==2 else 'needs_reanalysis')
            action='wait' if resolved or number==1 else 'skip'
            did=str(uuid4());reason='new_verified_evidence' if resolved else 'unresolved_evidence'
            self.db.execute('INSERT INTO f_decisions VALUES(?,?,?,?,?,?,?,?,?,?)',(did,key,payload,finding_id,reviewer_run_id,number,status,action,reason,self.clock()))
            self.db.execute('UPDATE f_review_state SET rounds=?,status=?,risk_action=? WHERE fixture_id=?',(number,status,action,f['fixture_id']))
            if status=='needs_reanalysis':self.db.execute('INSERT INTO f_reanalysis(id,decision_id,fixture_id) VALUES(?,?,?)',(str(uuid4()),did,f['fixture_id']))
            self.audit('review_decided',{'id':did,'fixture':f['fixture_id'],'round':number,'status':status,'risk_action':action})
            return self.review_record(self.db.execute('SELECT * FROM f_decisions WHERE id=?',(did,)).fetchone())

    def review_record(self,row):
        fid=self.db.execute('SELECT fixture_id FROM f_runs WHERE id=?',(row['reviewer_run_id'],)).fetchone()[0]
        return ReviewDecision(schema_version='1.0',decision_id=row['id'],agent_run_id=row['reviewer_run_id'],fixture_id=fid,
                              agent_role='scientific_referee',created_at=row['created_at'],finding_id=row['finding_id'],round_no=row['round_no'],
                              status=row['status'],reason=row['reason'],risk_action=row['risk_action'],numeric_override=None).model_dump(mode='json')

    def enqueue(self,value,depends_on=()):
        j=JobRequest.model_validate(value);body=canonical(j.model_dump(mode='json'))
        with self.transaction():
            old=self.db.execute('SELECT * FROM f_tasks WHERE request_key=?',(j.idempotency_key,)).fetchone()
            if old:
                deps={r[0] for r in self.db.execute('SELECT depends_on FROM f_task_dependencies WHERE task_id=?',(old['id'],))}
                if old['body']!=body or deps!=set(depends_on):raise ValueError('idempotency_conflict')
                return old['id']
            if j.fixture_id and not self.db.execute('SELECT 1 FROM f_fixtures WHERE id=?',(str(j.fixture_id),)).fetchone():raise ValueError('unknown_fixture')
            tid=str(uuid4())
            self.db.execute('INSERT INTO f_tasks(id,request_key,body,kind,max_attempts,timeout,not_before) VALUES(?,?,?,?,?,?,?)',(tid,j.idempotency_key,body,j.kind,j.max_attempts,j.timeout_seconds,self.clock()))
            for dep in set(depends_on):self.db.execute('INSERT INTO f_task_dependencies VALUES(?,?)',(tid,dep))
            self.audit('task_enqueued',{'id':tid,'request':json.loads(body)})
            return tid

    def claim(self,worker_id,role):
        role=Role(role).value;now=self.clock()
        with self.transaction():
            self.db.execute("UPDATE f_tasks SET status='failed',lease_token=NULL,lease_until=NULL,last_error='lease_expired_max_attempts' WHERE status='running' AND lease_until<=? AND attempts>=max_attempts",(now,))
            self.db.execute("UPDATE f_tasks SET status='blocked',last_error='dependency_failed' WHERE status='pending' AND EXISTS(SELECT 1 FROM f_task_dependencies d JOIN f_tasks p ON p.id=d.depends_on WHERE d.task_id=f_tasks.id AND p.status IN ('failed','blocked'))")
            rows=self.db.execute("SELECT * FROM f_tasks t WHERE ((status='pending' AND not_before<=?) OR (status='running' AND lease_until<=?)) AND attempts<max_attempts AND NOT EXISTS(SELECT 1 FROM f_task_dependencies d JOIN f_tasks p ON p.id=d.depends_on WHERE d.task_id=t.id AND p.status<>'done') ORDER BY not_before,id",(now,now)).fetchall()
            row=next((r for r in rows if JOB_ROLES[r['kind']]==role),None)
            if not row:return None
            token=str(uuid4());until=(datetime.fromisoformat(now)+timedelta(seconds=row['timeout'])).isoformat()
            self.db.execute("UPDATE f_tasks SET status='running',attempts=attempts+1,lease_token=?,lease_until=?,worker_id=? WHERE id=?",(token,until,worker_id,row['id']))
            self.db.execute('INSERT INTO f_task_attempts(task_id,token,worker_id,started_at,lease_until) VALUES(?,?,?,?,?)',(row['id'],token,worker_id,now,until))
            self.audit('task_claimed',{'id':row['id'],'token':token,'worker':worker_id})
            return dict(self.db.execute('SELECT * FROM f_tasks WHERE id=?',(row['id'],)).fetchone())

    def finish(self,task_id,token,worker_id,*,error=None):
        with self.transaction():
            row=self.db.execute("SELECT * FROM f_tasks WHERE id=? AND status='running' AND lease_token=? AND worker_id=? AND lease_until>?",(task_id,token,worker_id,self.clock())).fetchone()
            if not row:return False
            status='done' if error is None else ('failed' if row['attempts']>=row['max_attempts'] else 'pending')
            due=(datetime.fromisoformat(self.clock())+timedelta(seconds=30*2**row['attempts'])).isoformat()
            self.db.execute('UPDATE f_tasks SET status=?,lease_until=NULL,lease_token=NULL,last_error=?,not_before=? WHERE id=?',(status,error,due,task_id))
            self.audit('task_finished',{'id':task_id,'status':status,'error':error})
            return True

    def predict(self,run_id,model,fixture,*,evidence_ids):
        """Only the score role calls the existing numerical model, never an LLM override."""
        from engine.predict import predict
        run=self.db.execute('SELECT * FROM f_runs WHERE id=?',(run_id,)).fetchone()
        if not run or run['role']!='score_engine':raise ValueError('prediction_permission')
        f=self.db.execute('SELECT * FROM f_fixtures WHERE id=?',(run['fixture_id'],)).fetchone()
        if fixture.get('id')!=f['id'] or fixture['target']!=f['target'] or fixture['date']!=f['kickoff_at'][:10] or fixture['home']!=f['home'] or fixture['away']!=f['away']:raise ValueError('fixture_or_target_mismatch')
        if not evidence_ids:raise ValueError('evidence_required')
        for eid in evidence_ids:
            r=self.db.execute('SELECT body FROM f_evidence WHERE id=? AND fixture_id=?',(eid,f['id'])).fetchone()
            if not r:raise ValueError('missing_evidence')
            e=Evidence.model_validate_json(r[0])
            if e.quality!='verified':raise ValueError('unverified_prediction_input')
            if run['mode']=='prematch' and e.observed_at>datetime.fromisoformat(run['as_of']):raise ValueError('future_features')
        result=predict(model,fixture);result.update(mode=run['mode'],evidence_ids=evidence_ids,agent_run_id=run_id)
        h=hashlib.sha256(canonical(model.__dict__).encode()).hexdigest();pid=str(uuid4())
        with self.transaction():
            existing=self.db.execute('SELECT id FROM f_model_versions WHERE model_hash=?',(h,)).fetchone()
            model_id=existing[0] if existing else str(uuid4())
            if not existing:self.db.execute('INSERT INTO f_model_versions VALUES(?,?,?)',(model_id,h,canonical(model.__dict__)))
            result['model_version_id']=model_id
            old=self.db.execute('SELECT id,revision FROM f_prediction_revisions WHERE fixture_id=? ORDER BY revision DESC LIMIT 1',(f['id'],)).fetchone()
            self.db.execute('INSERT INTO f_prediction_revisions VALUES(?,?,?,?,?,?,?,?)',(pid,f['id'],h,model_id,old['revision']+1 if old else 1,old['id'] if old else None,self.clock(),canonical(result)))
            self.audit('prediction_recorded',{'id':pid,'model_hash':h})
        return pid

    def close(self):
        self.queue.close()
