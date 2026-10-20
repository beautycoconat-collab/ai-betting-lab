"""Evidence-bound, offline deployment readiness assessment.

This never asserts hosted JWT/RLS correctness from local tests or boolean flags.
The operator must provide independently verified evidence identifiers; the
script only validates the manifest's shape and freshness. It does not connect
or authorize a deployment.
"""
import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

REQUIRED = (
    'hosted_jwt_verified', 'hosted_rls_verified',
    'worker_least_privilege_verified', 'durable_quota_ledger_verified',
    'hosted_idempotency_verified', 'source_license_current',
    'dashboard_publication_verified',
)
_SHA = re.compile(r'^[0-9a-f]{64}$')


def inspect(manifest, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('aware_clock_required')
    now = now.astimezone(timezone.utc)
    failures = []
    if not isinstance(manifest, dict) or manifest.get('schema_version') != '1.0':
        return {'status': 'blocked', 'missing': list(REQUIRED), 'errors': ['invalid_manifest'],
                'schedule_enabled': False, 'portfolio_enabled': False}
    records = manifest.get('checks')
    if not isinstance(records, dict):
        records = {}
    for name in REQUIRED:
        entry = records.get(name)
        if not isinstance(entry, dict) or entry.get('passed') is not True:
            failures.append(name)
            continue
        try:
            checked = datetime.fromisoformat(entry['verified_at'].replace('Z', '+00:00'))
            if checked.tzinfo is None or checked.utcoffset() is None:
                raise ValueError('naive')
            checked = checked.astimezone(timezone.utc)
            if checked > now or now - checked > timedelta(days=7):
                raise ValueError('stale')
            if not _SHA.fullmatch(entry['evidence_sha256']):
                raise ValueError('hash')
            if not isinstance(entry.get('reviewer'), str) or not 2 <= len(entry['reviewer']) <= 120:
                raise ValueError('reviewer')
        except (ValueError, TypeError, KeyError, AttributeError):
            failures.append(name)
    # Explicit owner approval is independent of the seven technical checks.
    approved = manifest.get('owner_approved') is True
    if not approved:
        failures.append('owner_approval')
    return {'status': 'review_ready' if not failures else 'blocked',
            'missing': failures, 'errors': [],
            # Deliberately never turn on scheduling on the basis of a file.
            'schedule_enabled': False, 'portfolio_enabled': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', default='config/hosted-acceptance.json')
    args = parser.parse_args()
    path = Path(args.manifest)
    # Do not print manifest content: it may contain operator notes.
    try:
        result = inspect(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError, UnicodeError):
        result = inspect({})
    print(json.dumps(result, sort_keys=True))
    if result['status'] != 'review_ready':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
