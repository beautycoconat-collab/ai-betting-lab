"""SYNTHETIC fixtures only; live evidence is in reports/phase2/."""
import unittest,json,io,zipfile
from engine.adapters import *
from engine.normalization import normalize
from engine.identity import deduplicate

class Adapters(unittest.TestCase):
 def test_openfootball_flat_and_rounds(self):
  a=OpenFootball();r={'date':'2023-08-01','team1':'A','team2':'B','score':{'ft':[2,1]}}
  self.assertEqual(a.parse(a.rows({'matches':[r]})[0],{'league':'eng.1','season':'2023-24'}).home_goals,2)
  self.assertEqual(len(a.rows({'rounds':[{'name':'1','matches':[r]}]})),1)
 def test_openfootball_catalog_multiseason(self):
  a=OpenFootball();rows=[{'path':p,'type':'blob','sha':'test'} for p in ['2022-23/eng.1.json','2023-24/de.1.json','README.md']]
  self.assertEqual(len(a.catalog({'tree':rows})),2)
  with self.assertRaises(ValueError):a.catalog({'truncated':True})
 def test_openfootball_unplayed_no_invented_score(self):
  r=OpenFootball().parse({'date':'2023-08-01','team1':'A','team2':'B'},{'league':'eng.1','season':'2023-24'})
  self.assertIsNone(r.home_goals)
 def test_openliga_regulation_only(self):
  a=OpenLiga();r={'leagueShortcut':'bl1','leagueSeason':2023,'matchID':1,'matchDateTime':'2023-08-01T10:00:00','team1':{'teamName':'A'},'team2':{'teamName':'B'},'matchIsFinished':True,'matchResults':[{'resultTypeKind':'After90Minutes','pointsTeam1':1,'pointsTeam2':1}]}
  self.assertEqual(a.parse(r,{'league':'bl1','season':'2023'}).target,'regulation90')
  r['matchResults'][0]['resultTypeKind']='AfterExtraTime'
  with self.assertRaises(ValueError):a.parse(r,{'league':'bl1','season':'2023'})
 def test_openliga_catalog(self):
  rows=[{'leagueShortcut':'bl1','leagueSeason':s} for s in (2022,2023)]+[{'leagueShortcut':'hockey','leagueSeason':2023}]
  self.assertEqual(len(OpenLiga().catalog(rows)),2)
 def test_international_zip_and_semantics(self):
  a=International();f=io.BytesIO()
  with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('international_results-master/results.csv','date,home_team,away_team,home_score,away_score,tournament,neutral\n2020-01-01,A,B,1,0,Friendly,TRUE\n')
  rows=a.decode(f.getvalue(),'collect');r=a.parse(rows[0],{})
  self.assertTrue(r.neutral);self.assertEqual(r.target,'final_including_extra_time');self.assertEqual(len(a.catalog(rows)),1)
 def test_international_missing_neutral(self):
  with self.assertRaises(ValueError):International().parse({'neutral':'','home_score':'1','away_score':'0'}, {})
 def test_sportsdb_no_assumed_final(self):
  r={'idLeague':'4328','strSport':'Soccer','strSeason':'2023-2024','idEvent':'1','dateEvent':'2023-08-01','strHomeTeam':'A','strAwayTeam':'B','strStatus':'Not Started','intHomeScore':0,'intAwayScore':0}
  a=SportsDB();p={'league':'4328','season':'2023-2024'}
  self.assertIsNone(a.parse(r,p).home_goals)
  r['strStatus']='FT';self.assertEqual(a.parse(r,p).home_goals,0)
  with self.assertRaises(ValueError):a.parse(r,{'league':'123','season':'2023-2024'})
 def test_fjelstul(self):
  r={'match_id':'M-1','tournament_id':'WC-2022','match_date':'2022-12-18','home_team_name':'A','away_team_name':'B','home_team_score':'3','away_team_score':'3'}
  self.assertEqual(Fjelstul().parse(r,{}).target,'final_including_extra_time')
 def test_worldcup_old_and_new(self):
  a=WorldCup();r={'date':'2018-06-14','team1':{'name':'A'},'team2':{'name':'B'},'score1':1,'score2':0}
  self.assertEqual(a.parse(r,{'season':'2018'}).target,'provider_final_unknown')
  r['score']={'ft':[0,0]};self.assertEqual(a.parse(r,{'season':'2018'}).home_goals,0)
 def test_footballcsv(self):
  a=FootballCSV();body=b'Matchday,Date,Team 1,FT,Team 2\n1,Sat Aug 12 2023,A,2-1,B\n'
  r=a.parse(a.decode(body,'collect')[0],{'season':'2023-24','league':'eng.1'});self.assertEqual(r.home_goals,2)
  self.assertIn('/2020s/2023-24/eng.1.csv',a.url('collect',{'season':'2023-24','league':'eng.1'}))
 def test_conflicting_duplicates_all_rejected(self):
  r={'date':'2023-08-01','team1':'A','team2':'B','score':{'ft':[2,1]}}
  good,bad=normalize(OpenFootball(),{'matches':[r,dict(r,score={'ft':[1,2]}),r]},{'league':'eng.1','season':'2023-24'})
  self.assertEqual(good,[]);self.assertEqual(len(bad),3)
 def test_exact_duplicate_collapses(self):
  r={'date':'2023-08-01','team1':'A','team2':'B','score':{'ft':[2,1]}}
  good,bad=normalize(OpenFootball(),{'matches':[r,r]},{'league':'eng.1','season':'2023-24'})
  self.assertEqual(len(good),1);self.assertEqual(bad,[])
 def test_url_injection_rejected(self):
  for league in ('../secret','eng.1?token=x','https://evil.invalid'):
   with self.subTest(league=league),self.assertRaises(ValueError):OpenFootball().url('collect',{'league':league,'season':'2023-24'})
 def test_identity_requires_reviewed_aliases(self):
  r=Result('x','1','C','2023','2023-01-01','A','B',1,0,'regulation90',False).dict();r2=dict(r,source='y')
  out,issues=deduplicate([r,r2],{});self.assertEqual(len(issues['unresolved']),2)
  aliases={(s,'C',t):t for s in ('x','y') for t in ('A','B')};out,issues=deduplicate([r,r2],aliases)
  self.assertEqual(len(out),1);self.assertEqual(len(out[0]['provenance']),2)
  out,issues=deduplicate([r,dict(r2,home_goals=2)],aliases);self.assertEqual(len(issues['conflicts']),2)
