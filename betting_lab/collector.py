import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from betting_lab.domain import utcnow
from betting_lab.store import StopCollection
from betting_lab.adapters import ADAPTERS

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent':'AI-Betting-Lab/0.1 (personal research; low frequency)', 'Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as r:
        body = r.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError('response_too_large')
        if r.status != 200:
            raise ValueError('unexpected_http_status')
        return body, {k:r.headers[k] for k in ('ETag','Last-Modified','Content-Type') if k in r.headers}

def collect(store, source, policy, season, fetcher=fetch, clock=utcnow):
    started = clock()
    result = {'source':source, 'data_kind':'real', 'accepted':0, 'rejected':0}
    try:
        if policy.get('status') != 'approved':
            raise StopCollection('source_not_approved')
        if datetime.fromisoformat(started).date().isoformat() > policy['review_expires']:
            raise StopCollection('source_review_expired')
        adapter = ADAPTERS[source]
        url = adapter.url(season)
        if store.fresh(source,url,started,policy['cache_seconds']):
            raise StopCollection('cached')
        store.reserve(source,policy,started)
        body, headers = fetcher(url)
        observed = clock()  # available_at is after receipt, never kickoff or source update.
        payload = json.loads(body)
        matches, rejected, seen = [], [], set()
        for i, row in enumerate(adapter.rows(payload)):
            try:
                m = adapter.parse(row,season)
                if m.source_match_id in seen:
                    raise ValueError('duplicate_source_match_id')
                seen.add(m.source_match_id)
                matches.append(m)
            except (KeyError, TypeError, ValueError, AttributeError) as e:
                rejected.append((i,type(e).__name__+':'+str(e)[:120]))
        result.update(status='ok' if matches and not rejected else 'partial' if matches else 'invalid', accepted=len(matches),rejected=len(rejected))
        result['snapshot_id'] = store.save(source,url,observed,body,headers,matches,rejected)
    except StopCollection as e:
        result.update(status='skipped', reason=str(e))
    except urllib.error.HTTPError as e:
        result.update(status='error', reason=f'http_{e.code}')
        if e.code in (401,403,429):
            # No retry loop. Respect longer Retry-After values too.
            until = datetime.fromisoformat(started) + timedelta(hours=24)
            retry = e.headers.get('Retry-After') if e.headers else None
            if retry:
                try:
                    from email.utils import parsedate_to_datetime
                    candidate = datetime.fromisoformat(started)+timedelta(seconds=int(retry)) if retry.isdigit() else parsedate_to_datetime(retry)
                    until = max(until,candidate)
                except (ValueError,TypeError,OverflowError):
                    pass
            store.cooldown(source,until.isoformat())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as e:
        # No URLs, credentials, response bodies or arbitrary exception strings in logs.
        result.update(status='error', reason=type(e).__name__)
    store.run(source,started,result['status'],result)
    return result
