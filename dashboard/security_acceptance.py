"""Conservative gate for hosted scheduling; local success is never hosted proof."""
REQUIRED = ('hosted_jwt_verified','hosted_rls_verified','worker_least_privilege_verified',
            'durable_quota_ledger_verified','hosted_idempotency_verified',
            'source_license_current','dashboard_publication_verified')


def assess(evidence):
    if not isinstance(evidence,dict):
        raise TypeError('evidence_dict_required')
    # Strict booleans only. A self-declared flag is not proof; callers must
    # independently validate evidence and record an acceptance approval.
    missing=[name for name in REQUIRED if evidence.get(name) is not True]
    return {'status':'not_accepted' if missing else 'requires_human_approval',
            'missing':missing,'cron_enabled':False,'portfolio_enabled':False,
            'real_money_enabled':False,'hosted_verified':False}
