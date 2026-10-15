"""Only explicit aliases. No fuzzy auto-merge; ambiguity blocks matching."""
from betting_lab.domain import digest

def reconcile(rows, aliases):
    grouped, unresolved = {}, []
    for row in rows:
        scope = f"{row['source']}:{row['competition']}:"
        home = aliases.get(scope+row['home_key'])
        away = aliases.get(scope+row['away_key'])
        if not home or not away:
            unresolved.append({'source':row['source'],'source_match_id':row['source_match_id'],'reason':'unmapped_team'})
            continue
        # Date is a candidate grouping key, NOT a durable canonical match ID.
        key = digest([row['competition'],row['season'],home,away,row['match_date']])
        grouped.setdefault(key,[]).append(row)
    candidates = []
    for key, group in grouped.items():
        sources = [r['source'] for r in group]
        scores = {(r['home_goals'],r['away_goals']) for r in group if r['status']=='finished'}
        candidates.append({'candidate_id':key,'source_refs':[[r['source'],r['source_match_id']] for r in group],
                           'status':'conflict' if len(sources)!=len(set(sources)) or len(scores)>1 else 'candidate' if len(set(sources))>1 else 'single_source',
                           'requires_review':True})
    return {'candidates':candidates,'unresolved':unresolved}
