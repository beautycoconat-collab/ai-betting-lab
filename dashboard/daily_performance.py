"""Read-only forward-prediction quality report from verified immutable grades.

The input journal's provenance and referee requirements are enforced by
OutcomeJournal. Historical model backtests must never be mixed into this report.
"""
import json
import math
from datetime import datetime, timedelta, timezone


def _aware(value):
    dt = datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('timestamp_timezone_required')
    return dt.astimezone(timezone.utc)


def _mass(raw):
    values = json.loads(raw)
    if (not isinstance(values,list) or len(values)!=3 or
            any(type(x) not in (int,float) or not math.isfinite(x) or x<0 or x>1 for x in values) or
            abs(sum(values)-1)>1e-8):
        raise ValueError('invalid_locked_probability_mass')
    return values


def forward_metrics(db, now=None, windows=(7,30,90,180), bins=10):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('timezone_required')
    now = now.astimezone(timezone.utc)
    if type(bins) is not int or not 2 <= bins <= 20:
        raise ValueError('invalid_calibration_bins')
    names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {'lab_locked_predictions','lab_prediction_grades','lab_verified_results'}
    if not required <= names:
        return {'schema_version':'1.0','status':'not_available', 'as_of':now.isoformat(),
                'windows':{},'pilot_enabled':False,'roi':None,'clv':None}
    rows = list(db.execute('''SELECT p.prediction_id,p.captured_at,p.probabilities,
        g.recorded_at,g.log_loss,g.brier,r.result_body
        FROM lab_locked_predictions p
        LEFT JOIN lab_prediction_grades g ON g.prediction_id=p.prediction_id
        LEFT JOIN lab_verified_results r ON r.fixture_id=p.fixture_id
        ORDER BY p.captured_at,p.prediction_id'''))
    output = {}
    for days in windows:
        if type(days) is not int or not 1<=days<=3650:
            raise ValueError('invalid_window')
        since = now-timedelta(days=days)
        eligible = [r for r in rows if since <= _aware(r['captured_at']) <= now]
        graded = [r for r in eligible if r['recorded_at'] is not None and
                  since <= _aware(r['recorded_at']) <= now and r['result_body'] is not None]
        calibration = [{'count':0,'mean_confidence':None,'empirical_accuracy':None}
                       for _ in range(bins)]
        sums = [[0.0,0.0] for _ in range(bins)]
        briers, losses = [], []
        for r in graded:
            p = _mass(r['probabilities'])
            result = json.loads(r['result_body'])
            if result.get('status')!='final' or result.get('target')!='regulation90':
                raise ValueError('unverified_result_target')
            h, a = result.get('home'),result.get('away')
            if type(h) is not int or type(a) is not int or h<0 or a<0:
                raise ValueError('invalid_result_score')
            label = 0 if h>a else 1 if h==a else 2
            predicted = max(range(3),key=lambda i:p[i])
            conf = p[predicted]
            bucket = min(bins-1,int(conf*bins))
            calibration[bucket]['count']+=1
            sums[bucket][0]+=conf
            sums[bucket][1]+=int(predicted==label)
            if not all(math.isfinite(r[k]) and r[k]>=0 for k in ('brier','log_loss')):
                raise ValueError('invalid_grade')
            briers.append(r['brier']);losses.append(r['log_loss'])
        for i,entry in enumerate(calibration):
            if entry['count']:
                entry['mean_confidence']=sums[i][0]/entry['count']
                entry['empirical_accuracy']=sums[i][1]/entry['count']
        n=len(graded)
        output[str(days)]={'locked_predictions':len(eligible),'graded_predictions':n,
                           'pending_predictions':len(eligible)-n,
                           'coverage':n/len(eligible) if eligible else None,
                           'brier':sum(briers)/n if n else None,
                           'log_loss':sum(losses)/n if n else None,
                           'calibration':calibration,
                           'small_sample':n<30}
    return {'schema_version':'1.0','status':'verified_local_journal_only',
            'as_of':now.isoformat(),'windows':output,
            'pilot_enabled':False,'roi':None,'clv':None}
