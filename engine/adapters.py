"""Central adapter contract. Pure normalization and discovery, no network side effects."""
import csv,io,json,re,zipfile
from dataclasses import dataclass,asdict
from datetime import date,datetime,timezone
from typing import Protocol
from betting_lab.domain import digest,goals,name,aware

@dataclass(frozen=True)
class Result:
    source: str
    native_id: str
    competition: str
    season: str
    date: str
    home: str
    away: str
    home_goals: int | None
    away_goals: int | None
    target: str
    neutral: bool | None
    kickoff_at: str | None = None
    def __post_init__(self):
        date.fromisoformat(self.date)
        name(self.home);name(self.away)
        if self.home==self.away:raise ValueError('same_team')
        if (self.home_goals is None)!=(self.away_goals is None):raise ValueError('partial_score')
        if self.home_goals is not None:goals(self.home_goals);goals(self.away_goals)
        if self.target not in ('regulation90','final_including_extra_time','provider_final_unknown'):raise ValueError('invalid_target')
        if self.neutral is not None and type(self.neutral) is not bool:raise ValueError('invalid_neutral')
    def dict(self):return asdict(self)

class Adapter(Protocol):
    def url(self,kind:str,params:dict)->str: ...
    def decode(self,body:bytes,kind:str): ...
    def catalog(self,payload)->list[dict]: ...
    def rows(self,payload)->list: ...
    def parse(self,row:dict,params:dict)->Result: ...

def token(s,pattern=r'[a-zA-Z0-9_.-]+'):
    if not isinstance(s,str) or not re.fullmatch(pattern,s):raise ValueError('invalid_parameter')
    return s

class OpenFootball:
    def url(self,kind,p):
        if kind=='discover':return 'https://api.github.com/repos/openfootball/football.json/git/trees/master?recursive=1'
        season=token(p['season'],r'20\d{2}(?:-\d{2})?');league=token(p['league'],r'[a-z]{2,3}\.\d+')
        return f'https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{league}.json'
    def decode(self,b,kind):return json.loads(b)
    def catalog(self,payload):
        if payload.get('truncated'):raise ValueError('truncated_catalog')
        out=[]
        for f in payload['tree']:
            m=re.fullmatch(r'(20\d{2}(?:-\d{2})?)/([a-z]{2,3}\.\d+)\.json',f['path'])
            if m and f['type']=='blob':out.append({'season':m[1],'league':m[2],'git_blob_sha':f['sha']})
        return out
    def rows(self,payload):
        if isinstance(payload.get('matches'),list):return payload['matches']
        if isinstance(payload.get('rounds'),list):return [dict(m,round=r['name']) for r in payload['rounds'] for m in r['matches']]
        raise ValueError('unsupported_envelope')
    def parse(self,r,p):
        h,a=name(r['team1']),name(r['team2']); score=r.get('score')
        # Both provider JSON encodings occur in the same domestic-league feed.
        # The two-element legacy array is the full-time score; never infer a
        # score from time, round, half-time or missing fields.
        if score is None:ft=None
        elif isinstance(score,list):ft=score
        elif isinstance(score,dict):ft=score.get('ft')
        else:raise ValueError('bad_score_envelope')
        if ft is not None and (not isinstance(ft,list) or len(ft)!=2):raise ValueError('bad_score')
        hg,ag=(goals(ft[0]),goals(ft[1])) if ft is not None else (None,None)
        return Result('openfootball',digest([p['league'],p['season'],h,a,r.get('round') or r['date']]),p['league'],p['season'],r['date'],h,a,hg,ag,'regulation90',False)

class OpenLiga:
    def url(self,kind,p):
        if kind=='discover':return 'https://api.openligadb.de/getavailableleagues'
        return 'https://api.openligadb.de/getmatchdata/'+token(p['league'])+'/'+token(str(p['season']),r'\d{4}')
    def decode(self,b,kind):return json.loads(b)
    def catalog(self,payload):
        out=[]
        for r in payload:
            shortcut=r.get('leagueShortcut','');sport=r.get('sport',{}) or {}
            if shortcut in ('bl1','bl2','bl3') or sport.get('sportName') in ('Fußball','Football','Soccer'):
                out.append({'league':shortcut,'season':str(r['leagueSeason']),'name':r.get('leagueName'),'league_id':r.get('leagueId')})
        return out
    def rows(self,payload):
        if not isinstance(payload,list):raise ValueError('expected_list')
        return payload
    def parse(self,r,p):
        if r['leagueShortcut']!=p['league'] or str(r['leagueSeason'])!=str(p['season']):raise ValueError('wrong_scope')
        final=[s for s in r.get('matchResults',[]) if s.get('resultTypeKind')=='After90Minutes' or (s.get('resultTypeKind') is None and s.get('resultTypeID')==2 and p['league'] in ('bl1','bl2','bl3'))]
        hg=ag=None
        if r.get('matchIsFinished'):
            if len(final)!=1:raise ValueError('90_minute_result_missing_or_ambiguous')
            hg,ag=goals(final[0]['pointsTeam1']),goals(final[0]['pointsTeam2'])
        kickoff=aware(r['matchDateTimeUTC']) if r.get('matchDateTimeUTC') else None
        return Result('openliga',str(r['matchID']),p['league'],str(p['season']),r['matchDateTime'][:10],name(r['team1']['teamName']),name(r['team2']['teamName']),hg,ag,'regulation90',None,kickoff)

class International:
    def url(self,kind,p):
        if kind!='collect':raise ValueError('bulk_dataset_has_embedded_catalog')
        return 'https://codeload.github.com/martj42/international_results/zip/refs/heads/master'
    def decode(self,b,kind):
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            member='international_results-master/results.csv'; info=z.getinfo(member)
            if info.file_size>10_000_000 or info.file_size/max(1,info.compress_size)>100:raise ValueError('archive_expansion_limit')
            return list(csv.DictReader(io.StringIO(z.read(member).decode('utf-8-sig'))))
    def rows(self,payload):return payload
    def catalog(self,payload):return sorted([{'competition':a,'season':b} for a,b in {(r['tournament'],r['date'][:4]) for r in payload}],key=lambda r:(r['season'],r['competition']))
    def parse(self,r,p):
        neutral=r['neutral'].lower()
        if neutral not in ('true','false'):raise ValueError('unknown_neutral')
        hg,ag=r['home_score'],r['away_score']
        if not hg or not ag:raise ValueError('missing_result')
        return Result('international',digest([r['date'],r['home_team'],r['away_team'],r['tournament']]),r['tournament'],r['date'][:4],r['date'],name(r['home_team']),name(r['away_team']),goals(int(hg)),goals(int(ag)),'final_including_extra_time',neutral=='true')

class SportsDB:
    def url(self,kind,p):
        # Public educational example key documented by provider, NOT a private credential.
        base='https://www.thesportsdb.com/api/v1/json/123/'
        if kind=='discover':return base+'all_leagues.php'
        return base+'eventsseason.php?id='+token(str(p['league']),r'\d+')+'&s='+token(p['season'],r'\d{4}(?:-\d{4})?')
    def decode(self,b,kind):return json.loads(b)
    def catalog(self,payload):return [{'league':r['idLeague'],'name':r['strLeague']} for r in payload['leagues'] if r['strSport']=='Soccer']
    def rows(self,payload):return payload.get('events') or []
    def parse(self,r,p):
        if r.get('strSport')!='Soccer' or str(r['idLeague'])!=str(p['league']):raise ValueError('wrong_scope')
        if r.get('strSeason')!=p['season']:raise ValueError('wrong_season')
        hg=ag=None
        if r.get('strStatus') in ('Match Finished','FT') and r.get('intHomeScore') is not None and r.get('intAwayScore') is not None:
            hg,ag=goals(int(r['intHomeScore'])),goals(int(r['intAwayScore']))
        return Result('thesportsdb',str(r['idEvent']),str(p['league']),p['season'],r['dateEvent'],name(r['strHomeTeam']),name(r['strAwayTeam']),hg,ag,'provider_final_unknown',None)

ADAPTERS={'openfootball':OpenFootball(),'openliga':OpenLiga(),'international':International(),'thesportsdb':SportsDB()}

class Fjelstul:
    def url(self,kind,p):
        if kind!='collect':raise ValueError('bulk_catalog')
        return 'https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv/matches.csv'
    def decode(self,b,kind):return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
    def rows(self,payload):return payload
    def catalog(self,payload):return [{'tournament_id':x} for x in sorted({r['tournament_id'] for r in payload})]
    def parse(self,r,p):
        # Provider explicit final score, not assumed regulation-time score.
        return Result('fjelstul',r['match_id'],r['tournament_id'],r['match_date'][:4],r['match_date'],name(r['home_team_name']),name(r['away_team_name']),goals(int(r['home_team_score'])),goals(int(r['away_team_score'])),'final_including_extra_time',None)

class WorldCup:
    def url(self,kind,p):
        if kind=='discover':return 'https://api.github.com/repos/openfootball/worldcup.json/git/trees/master?recursive=1'
        return 'https://raw.githubusercontent.com/openfootball/worldcup.json/master/'+token(str(p['season']),r'20\d{2}')+'/worldcup.json'
    def decode(self,b,kind):return json.loads(b)
    def catalog(self,payload):
        if payload.get('truncated'):raise ValueError('truncated_catalog')
        return [{'season':m[1]} for r in payload['tree'] if (m:=re.fullmatch(r'(20\d{2})/worldcup.json',r['path']))]
    def rows(self,payload):
        if 'matches' in payload:return payload['matches']
        return [m for r in payload['rounds'] for m in r['matches']]
    def parse(self,r,p):
        def team(x):return name(x['name']) if isinstance(x,dict) else name(x)
        h,a=team(r['team1']),team(r['team2']);day=r['date'][:10]
        # Different historical formats must preserve explicit score semantics.
        if 'score' in r:
            score=r['score'].get('ft');target='regulation90'
        else:
            score=[r.get('score1'),r.get('score2')];target='provider_final_unknown'
        hg=ag=None
        if score is not None and all(v is not None for v in score):hg,ag=goals(score[0]),goals(score[1])
        return Result('worldcup',str(r.get('num') or digest([day,h,a])), 'FIFA-WC-MEN',str(p['season']),day,h,a,hg,ag,target,None)

ADAPTERS.update({'fjelstul':Fjelstul(),'worldcup':WorldCup()})

class FootballCSV:
    def url(self,kind,p):
        if kind=='discover':return 'https://api.github.com/repos/footballcsv/england/git/trees/master?recursive=1'
        season=token(p['season'],r'20\d{2}-\d{2}');league=token(p['league'],r'eng\.\d+')
        decade=str(int(season[:4])//10*10)+'s'
        return f'https://raw.githubusercontent.com/footballcsv/england/master/{decade}/{season}/{league}.csv'
    def decode(self,b,kind):
        if kind=='discover':return json.loads(b)
        return [{k.strip():v.strip() for k,v in r.items()} for r in csv.DictReader(io.StringIO(b.decode('utf-8-sig')),skipinitialspace=True)]
    def catalog(self,payload):
        if payload.get('truncated'):raise ValueError('truncated_catalog')
        return [{'season':m[1],'league':m[2]} for r in payload['tree'] if (m:=re.fullmatch(r'\d{4}s/(20\d{2}-\d{2})/(eng\.\d+)\.csv',r['path']))]
    def rows(self,payload):return payload
    def parse(self,r,p):
        day=datetime.strptime(r['Date'],'%a %b %d %Y').date().isoformat();h,a=name(r['Team 1']),name(r['Team 2']);score=r['FT']
        hg=ag=None
        if score:
            m=re.fullmatch(r'(\d+)-(\d+)',score)
            if not m:raise ValueError('unsupported_score')
            hg,ag=goals(int(m[1])),goals(int(m[2]))
        return Result('footballcsv',digest([p['season'],p['league'],day,h,a]),p['league'],p['season'],day,h,a,hg,ag,'regulation90',False)
ADAPTERS['footballcsv']=FootballCSV()
