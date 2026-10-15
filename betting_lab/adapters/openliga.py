from betting_lab.domain import Match, aware, identifier, name, goals
from datetime import datetime
from zoneinfo import ZoneInfo

class OpenLiga:
    def url(self, season):
        return f'https://api.openligadb.de/getmatchdata/bl1/{season}'
    def rows(self, payload):
        if not isinstance(payload, list):
            raise ValueError('expected_list')
        return payload
    def parse(self, row, season):
        if row.get('leagueShortcut') != 'bl1' or row.get('leagueSeason') != season:
            raise ValueError('wrong_competition_or_season')
        h, a = row['team1'], row['team2']
        kickoff = aware(row['matchDateTimeUTC']) if row.get('matchDateTimeUTC') else None
        if kickoff:
            day = datetime.fromisoformat(kickoff).astimezone(ZoneInfo('Europe/Berlin')).date().isoformat()
        else:
            day = row['matchDateTime'][:10]
        finished = row.get('matchIsFinished')
        if type(finished) is not bool:
            raise ValueError('invalid_finished_flag')
        scores = [r for r in row.get('matchResults', []) if r.get('resultTypeKind') == 'After90Minutes' or (r.get('resultTypeKind') is None and r.get('resultTypeID') == 2)]
        if finished and len(scores) != 1:
            raise ValueError('ambiguous_or_missing_fulltime')
        hg = goals(scores[0]['pointsTeam1']) if finished else None
        ag = goals(scores[0]['pointsTeam2']) if finished else None
        # lastUpdateDateTime lacks an offset; retain raw, never invent UTC.
        raw_update = row.get('lastUpdateDateTime')
        try:
            update = aware(raw_update) if raw_update else None
        except ValueError:
            update = None
        return Match('openliga', identifier(row['matchID']), 'DE-BL1', season,
                     identifier(h['teamId']), identifier(a['teamId']), name(h['teamName']), name(a['teamName']),
                     day, kickoff, 'finished' if finished else 'unknown', hg, ag, update, raw_update)
