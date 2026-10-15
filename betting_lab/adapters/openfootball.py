from betting_lab.domain import Match, digest, name, goals

class OpenFootball:
    def url(self, season):
        return f'https://raw.githubusercontent.com/openfootball/football.json/master/{season}-{str(season+1)[-2:]}/de.1.json'
    def rows(self, payload):
        if not isinstance(payload, dict) or not isinstance(payload.get('matches'), list):
            raise ValueError('expected_matches_array')
        return payload['matches']
    def parse(self, row, season):
        h, a = name(row['team1']), name(row['team2'])
        ft = row.get('score', {}).get('ft')
        if ft is not None and (not isinstance(ft, list) or len(ft) != 2):
            raise ValueError('invalid_fulltime')
        hg, ag = (goals(ft[0]), goals(ft[1])) if ft is not None else (None, None)
        # No native IDs: home/away/round scope is stable across date corrections.
        # Without round, date fallback is explicitly a source-local identity only.
        key = digest([season, h, a, row.get('round') or row['date']])
        # Time has no documented offset in this payload; kickoff intentionally NULL.
        return Match('openfootball', key, 'DE-BL1', season, h, a, h, a,
                     row['date'], None, 'finished' if ft is not None else 'unknown', hg, ag, None, None)
