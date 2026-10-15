"""Motor C: independent deterministic checks; no probability override."""
import json
from .contracts import AuditContext, Finding, Verdict


class RedTeam:
    def inspect(self, context):
        c = AuditContext.model_validate(context)
        findings = []

        def add(issue, severity, ids, action='review'):
            findings.append(Finding(schema_version='1.0', issue_type=issue,
                severity=severity, evidence_ids=ids, requested_action=action))

        future = [i for i, at in c.observations.items() if at > c.as_of]
        if c.mode == 'prematch' and future:
            add('data_leakage', 'critical', future, 'recalculate')
        if c.training_end >= c.kickoff_at.date():
            add('data_leakage', 'critical', [c.prediction_id], 'recalculate')
        if not c.lineup_evidence_ids:
            add('lineup_uncertainty', 'high', [c.prediction_id])
        if c.training_matches < 100:
            add('low_sample', 'high', [c.prediction_id])
        if c.model_spread > .2:
            add('model_disagreement', 'high', [c.prediction_id], 'recalculate')
        if max(c.probabilities) > .95:
            add('overconfidence', 'high', [c.prediction_id])
        for group in c.upstream_groups.values():
            if len(group) > 1:
                add('shared_upstream', 'medium', group)
        return findings


class ScientificReferee:
    def decide(self, context, findings, round_no):
        c = AuditContext.model_validate(context)
        findings = [Finding.model_validate(f) for f in findings]
        if type(round_no) is not int or round_no not in (1, 2):
            raise ValueError('review_limit')
        known = set(c.observations) | {c.prediction_id}
        if any(not set(f.evidence_ids) <= known for f in findings):
            return Verdict(schema_version='1.0', status='rejected', risk_action='skip',
                           round_no=round_no, reasons=['unknown_evidence'])
        # Independently inspect the context even if the Red Team omits a finding.
        reasons = []
        if c.as_of >= c.kickoff_at:
            reasons.append('kickoff_passed')
        if c.training_end >= c.kickoff_at.date():
            reasons.append('training_overlap')
        if c.mode == 'prematch' and any(t > c.as_of for t in c.observations.values()):
            reasons.append('future_observation')
        if not c.lineup_evidence_ids:
            reasons.append('lineup_unverified')
        if c.training_matches < 100:
            reasons.append('low_sample')
        if c.model_spread > .2:
            reasons.append('model_disagreement')
        if max(c.probabilities) > .95:
            reasons.append('overconfidence')
        # An externally raised high/critical issue cannot be cleared just by omission.
        reasons += [f.issue_type for f in findings if f.severity in ('high', 'critical')]
        status = ('abstain' if round_no == 2 else 'needs_reanalysis') if reasons else 'approved'
        return Verdict(schema_version='1.0', status=status, risk_action='skip' if status == 'abstain' else 'wait',
                       round_no=round_no, reasons=sorted(set(reasons)))


class ReviewSession:
    """Two rounds across process restarts, persisted in the existing append-only audit."""
    def __init__(self, runtime):
        self.runtime = runtime

    def decide(self, context, findings, key):
        c = AuditContext.model_validate(context)
        fs = [Finding.model_validate(f) for f in findings]
        payload = {'context': c.model_dump(mode='json'), 'findings': [f.model_dump(mode='json') for f in fs]}
        with self.runtime.transaction():
            records = [json.loads(r[0]) for r in self.runtime.db.execute("SELECT body FROM f_audit WHERE event='expert_review'")]
            prior = next((r for r in records if r['key'] == key), None)
            if prior:
                if prior['payload'] != payload:
                    raise ValueError('idempotency_conflict')
                return Verdict.model_validate(prior['verdict'])
            rounds = sum(r['payload']['context']['fixture_id'] == str(c.fixture_id) for r in records)
            verdict = ScientificReferee().decide(c, fs, rounds+1)
            self.runtime.audit('expert_review', {'key': key, 'payload': payload, 'verdict': verdict.model_dump(mode='json')})
            return verdict
