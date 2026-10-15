"""Conservative, reviewed cross-source identities. No fuzzy automatic merge."""
from collections import defaultdict

def deduplicate(rows,aliases):
    """aliases maps (source, competition, name) to reviewed canonical team ID.
    Unmapped records are quarantined, not silently guessed. Competition IDs must
    already be canonical. Same-date conflicting scores are all quarantined.
    """
    groups=defaultdict(list);unresolved=[];conflicts=[];out=[]
    for r in rows:
        h=aliases.get((r['source'],r['competition'],r['home']));a=aliases.get((r['source'],r['competition'],r['away']))
        if not h or not a or h==a:unresolved.append(r);continue
        groups[(r['competition'],r['date'],h,a,r['target'])].append(r)
    for key,group in groups.items():
        if len({(r['home_goals'],r['away_goals']) for r in group})>1:conflicts.extend(group);continue
        # Keep every provenance pointer, count the match only once.
        out.append({'identity':key,'result':group[0],'provenance':group})
    return out,{'unresolved':unresolved,'conflicts':conflicts}
