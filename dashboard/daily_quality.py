"""Public, read-only quality gates for a daily football research projection.

Never interprets a conditional venue forecast as an approved selection. All
counts are based on the published fixtures, not a claimed background job.
"""
from datetime import datetime, timedelta, timezone


def _parse_time(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, AttributeError):
        return None


def report(fixtures, now=None, collection=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('timezone_required')
    now = now.astimezone(timezone.utc)
    if not isinstance(fixtures, list):
        raise TypeError('fixtures_must_be_list')
    result = {'schema_version': '1.0', 'as_of': now.isoformat(),
              'total_fixtures': len(fixtures), 'fresh_fixtures': 0,
              'stale_or_unverifiable_fixtures': 0,
              'conditional_venue_fixtures': 0, 'calculated_fixtures': 0,
              'insufficient_data_fixtures': 0, 'other_status_fixtures': 0,
              'review_approved_scenarios': 0, 'review_abstain_scenarios': 0,
              'review_other_scenarios': 0, 'duplicate_fixture_ids': 0,
              'research_only': True, 'pilot_enabled': False,
              'live_schedule_verified': False, 'collection_status': 'not_verified'}
    if isinstance(collection, dict):
        # Never serialize raw errors, URLs, params, or arbitrary provider strings.
        status = collection.get('status')
        if status in {'done', 'failed', 'blocked', 'not_requested', 'empty'}:
            result['collection_status'] = status
    seen = set()
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            result['other_status_fixtures'] += 1
            result['stale_or_unverifiable_fixtures'] += 1
            continue
        identifier = fixture.get('id')
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            result['duplicate_fixture_ids'] += 1
        else:
            seen.add(identifier)
        observed = _parse_time(fixture.get('observed_at'))
        if observed is not None and timedelta(0) <= now - observed <= timedelta(hours=24):
            result['fresh_fixtures'] += 1
        else:
            result['stale_or_unverifiable_fixtures'] += 1
        status = fixture.get('prediction_status')
        status_key = {'conditional_scenarios': 'conditional_venue_fixtures',
                      'calculated': 'calculated_fixtures',
                      'insufficient_data': 'insufficient_data_fixtures'}.get(
                          status, 'other_status_fixtures')
        result[status_key] += 1
        cases = fixture.get('scenarios')
        if not isinstance(cases, list):
            continue
        for case in cases:
            if not isinstance(case, dict):
                result['review_other_scenarios'] += 1
                continue
            reviews = case.get('reviews')
            last = reviews[-1] if isinstance(reviews, list) and reviews else None
            verdict = last.get('status') if isinstance(last, dict) else None
            if verdict == 'approved':
                result['review_approved_scenarios'] += 1
            elif verdict == 'abstain':
                result['review_abstain_scenarios'] += 1
            else:
                result['review_other_scenarios'] += 1
    result['data_ready'] = (result['total_fixtures'] > 0 and
                            result['fresh_fixtures'] == result['total_fixtures'] and
                            result['duplicate_fixture_ids'] == 0)
    result['publication_status'] = ('fresh_research_snapshot' if result['data_ready']
                                    else 'unverified_or_stale_research')
    # No model approvals or collection status can enable an execution gate.
    result['execution_enabled'] = False
    return result
