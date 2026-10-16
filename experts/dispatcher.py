"""Local trusted-process dispatcher; no hosted credentials or portfolio execution.

Handlers must be pure or independently idempotent: leases fence database output,
not external side effects. A process crash leaves the existing lease recoverable.
"""
from typing import Literal
from pydantic import Field
from foundation.contracts import Contract, JobRequest
from foundation.runtime import JOB_ROLES, canonical


class TaskOutput(Contract):
    status: Literal['ready', 'blocked']
    data: dict = Field(default_factory=dict)
    reason: str | None = None
    numeric_override: None = None


class Dispatcher:
    def __init__(self, runtime, handlers):
        if set(handlers) - set(JOB_ROLES):
            raise ValueError('unknown_handler_kind')
        self.runtime, self.handlers = runtime, dict(handlers)
        runtime.db.executescript('''
        CREATE TABLE IF NOT EXISTS expert_task_outputs(
          task_id TEXT PRIMARY KEY REFERENCES f_tasks(id),
          lease_token TEXT NOT NULL, body TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS expert_output_update BEFORE UPDATE ON expert_task_outputs
          BEGIN SELECT RAISE(ABORT,'append_only'); END;
        CREATE TRIGGER IF NOT EXISTS expert_output_delete BEFORE DELETE ON expert_task_outputs
          BEGIN SELECT RAISE(ABORT,'append_only'); END;
        ''')

    def work_one(self, worker_id, role):
        r = self.runtime
        task = r.claim(worker_id, role)
        if task is None:
            return None
        try:
            handler = self.handlers.get(task['kind'])
            if handler is None:
                output = TaskOutput(schema_version='1.0', status='blocked', reason='handler_unavailable')
            else:
                dependencies = {}
                for row in r.db.execute('''SELECT d.depends_on,o.body FROM f_task_dependencies d
                    LEFT JOIN expert_task_outputs o ON o.task_id=d.depends_on WHERE d.task_id=?''', (task['id'],)):
                    if row['body'] is None:
                        raise ValueError('dependency_output_missing')
                    dependencies[row['depends_on']] = TaskOutput.model_validate_json(row['body'])
                output = TaskOutput.model_validate(handler(JobRequest.model_validate_json(task['body']), dependencies))
            body = canonical(output.model_dump(mode='json'))
            if len(body.encode()) > 65536:
                raise ValueError('output_storage_limit')
            with r.transaction():
                valid = r.db.execute('''SELECT 1 FROM f_tasks WHERE id=? AND status='running'
                    AND lease_token=? AND worker_id=? AND lease_until>?''',
                    (task['id'], task['lease_token'], worker_id, r.clock())).fetchone()
                if not valid:
                    return {'task_id': task['id'], 'status': 'lease_lost'}
                r.db.execute('INSERT INTO expert_task_outputs VALUES(?,?,?)', (task['id'], task['lease_token'], body))
                status = 'done' if output.status == 'ready' else 'blocked'
                r.db.execute('''UPDATE f_tasks SET status=?,lease_token=NULL,lease_until=NULL,
                    last_error=? WHERE id=?''', (status, output.reason, task['id']))
                r.audit('expert_task_completed', {'task_id': task['id'], 'status': status})
            return {'task_id': task['id'], 'status': status}
        except Exception as exc:
            # Do not persist exception messages: remote errors can contain secrets.
            accepted = r.finish(task['id'], task['lease_token'], worker_id, error=type(exc).__name__)
            return {'task_id': task['id'], 'status': 'retry_or_failed' if accepted else 'lease_lost'}

    def cancel(self, task_id):
        with self.runtime.transaction():
            changed = self.runtime.db.execute("""UPDATE f_tasks SET status='blocked',
                last_error='cancelled',lease_token=NULL,lease_until=NULL
                WHERE id=? AND status IN ('pending','running')""", (task_id,)).rowcount
            if changed:
                self.runtime.audit('expert_task_cancelled', {'task_id': task_id})
            return bool(changed)


def validation_handler(registry, load_input):
    """Bind the existing validator to trusted, versioned input storage.

    load_input receives the job; it must return the immutable fixture, claims,
    as_of and snapshots. Missing or quarantined evidence never releases models.
    """
    from .research import DataValidator
    validator = DataValidator(registry)

    def execute(job, dependencies):
        payload = load_input(job)
        if str(payload['fixture']['id']) != str(job.fixture_id):
            raise ValueError('fixture_identity_mismatch')
        result = validator.validate(payload['fixture'], payload['claims'],
                                    payload['as_of'], payload['snapshots'])
        return TaskOutput(schema_version='1.0',
            status='ready' if result.status == 'ready' else 'blocked',
            data=result.model_dump(mode='json'),
            reason=None if result.status == 'ready' else 'evidence_not_ready')
    return execute
