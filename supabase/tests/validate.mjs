// PostgreSQL semantics via PGlite; NOT hosted Supabase or concurrent network sessions.
import { PGlite } from '@electric-sql/pglite';
import { readFileSync } from 'node:fs';
const db=new PGlite();
const sql=readFileSync(new URL('../migrations/001_lab.sql',import.meta.url),'utf8');
await db.exec(sql);
let passed=0;
async function ok(label, fn){await fn();passed++;console.log('PASS '+label);}
function assert(x){if(!x)throw new Error('assertion failed');}
async function reject(label,sql,pattern){await ok(label,async()=>{let err;try{await db.exec(sql);}catch(e){err=e;}assert(err && pattern.test(String(err.message)));});}
await ok('migration applies',async()=>assert((await db.query("select count(*)::int n from pg_tables where schemaname='lab'")).rows[0].n===20));
await ok('initial balance 1000 TRY and pilot disabled',async()=>{const r=(await db.query('select * from lab.paper_wallet')).rows[0];assert(Number(r.balance_kurus)===100000&&!r.betting_enabled);});
await reject('disabled pilot refuses stake',"select lab.place_paper_bet('test-0001',gen_random_uuid(),gen_random_uuid(),1000)",/pilot_disabled/);
await ok('all tables have RLS',async()=>assert((await db.query("select count(*)::int n from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='lab' and c.relkind='r' and not c.relrowsecurity")).rows[0].n===0));
await db.exec("create role lab_test_browser; grant usage on schema lab to lab_test_browser; set role lab_test_browser");
await reject('browser cannot modify wallet','update lab.paper_wallet set balance_kurus=999999',/permission denied/);
await reject('browser cannot execute staking RPC',"select lab.place_paper_bet('test-0001',gen_random_uuid(),gen_random_uuid(),1000)",/permission denied/);
await db.exec('reset role');
await reject('ledger is append only',"update lab.wallet_ledger set amount_kurus=1",/append_only_table/);
await reject('ledger deletion denied',"delete from lab.wallet_ledger",/append_only_table/);
// SYNTHETIC test environment only. 'real' markers below deliberately exercise provenance checks.
await db.exec(`
INSERT INTO lab.sources(id,status,license_url,review_expires) VALUES('test','approved','https://example.invalid/license',now()+interval '1 day');
INSERT INTO lab.raw_snapshots(id,source_id,request_url,received_at,content_sha256,payload,data_kind)
VALUES('00000000-0000-0000-0000-000000000001','test','https://example.invalid/data',now()-interval '1 hour',repeat('a',64),'{}','real');
INSERT INTO lab.teams(id,name) VALUES('00000000-0000-0000-0000-000000000002','TEST Alpha'),('00000000-0000-0000-0000-000000000003','TEST Beta');
INSERT INTO lab.model_versions(id,name,code_sha,parameters,trained_through,role,dataset_hash)
VALUES('00000000-0000-0000-0000-000000000004','TEST MODEL','test','{}',now()-interval '2 hours','champion','test');
UPDATE lab.paper_wallet SET betting_enabled=true,pilot_start=now()-interval '1 hour',pilot_end=now()-interval '1 hour'+interval '7 days';
`);
async function fixture(i,options={}){
 const m=(await db.query("INSERT INTO lab.matches(competition,season,home_id,away_id,kickoff_at,status) VALUES('TEST','2026','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003',now()+interval '2 hours','scheduled') returning id")).rows[0].id;
 const p=(await db.query(`INSERT INTO lab.predictions(match_id,model_id,feature_cutoff,kickoff_at,p_home,p_draw,p_away,score_grid,input_snapshot_ids)
 VALUES($1,'00000000-0000-0000-0000-000000000004',now()-interval '30 minutes',(select kickoff_at from lab.matches where id=$1),0.5,0.3,0.2,'{}',ARRAY['00000000-0000-0000-0000-000000000001']::uuid[]) returning id`,[m])).rows[0].id;
 const o=(await db.query(`INSERT INTO lab.odds_snapshots(match_id,source_id,bookmaker,market,outcome,decimal_odds,source_updated_at,observed_at,raw_snapshot_id)
 VALUES($1,'test','TEST BOOK','1X2','H',2.1,now()-interval '1 minute',now(),'00000000-0000-0000-0000-000000000001') returning id`,[m])).rows[0].id;
 return {m,p,o,call:(key='test-key-'+i,stake=1000)=>`select lab.place_paper_bet('${key}','${p}','${o}',${stake}) id`};
}
const first=await fixture(1);
let firstId;
await ok('atomic stake and ledger',async()=>{firstId=(await db.query(first.call())).rows[0].id;assert(Number((await db.query('select balance_kurus from lab.paper_wallet')).rows[0].balance_kurus)===99000);});
await ok('idempotent retry no second debit',async()=>{assert((await db.query(first.call())).rows[0].id===firstId);assert(Number((await db.query('select balance_kurus from lab.paper_wallet')).rows[0].balance_kurus)===99000);});
await reject('idempotency conflicting payload',first.call('test-key-1',500),/idempotency_conflict/);
await reject('negative stake',first.call('negative-key',-1),/invalid_stake_request/);
await reject('over per match cap',first.call('large-stake',1001),/invalid_stake_request/);
const stale=await fixture(20);
await db.exec(`update lab.matches set kickoff_at=now()-interval '1 minute' where id='${stale.m}'`);
await reject('kickoff passed blocks bet',stale.call(),/ineligible_or_stale_inputs/);
const cross=await fixture(21);
await reject('odds from different match',`select lab.place_paper_bet('cross-match','${cross.p}','${first.o}',100)`,/ineligible_or_stale_inputs/);
for(let i=2;i<=10;i++){const f=await fixture(i);await db.exec(f.call());}
await ok('exact 100 TRY daily cap accepted',async()=>assert(Number((await db.query('select sum(stake_kurus) s from lab.paper_bets')).rows[0].s)===10000));
const extra=await fixture(11);
await reject('101 TRY day rejected',extra.call('test-key-11',100),/daily_limit/);
await ok('failed transaction does not debit',async()=>assert(Number((await db.query('select balance_kurus from lab.paper_wallet')).rows[0].balance_kurus)===90000));
await db.exec("update lab.paper_bets set status='void' where id='"+firstId+"'");
await reject('void does not replenish daily allowance',extra.call('void-refill',100),/daily_limit/);
await ok('Istanbul budget day from server clock',async()=>assert((await db.query("select count(*)::int n from lab.paper_bets where budget_day<>(clock_timestamp() at time zone 'Europe/Istanbul')::date")).rows[0].n===0));
await ok('ledger reconciles with wallet',async()=>assert((await db.query('select (select sum(amount_kurus) from lab.wallet_ledger)=(select balance_kurus from lab.paper_wallet) good')).rows[0].good));
await reject('second champion not allowed',`INSERT INTO lab.model_versions(name,code_sha,parameters,trained_through,role,dataset_hash) VALUES('OTHER','test','{}',now(),'champion','test')`,/duplicate key/);
await db.exec("update lab.paper_wallet set pilot_start=now()-interval '8 days',pilot_end=now()-interval '1 day'");
await reject('seven day pilot expiration',extra.call('expired-key',100),/pilot_disabled/);
console.log(`TOTAL ${passed} PostgreSQL checks passed. Concurrent hosted sessions NOT tested.`);
await db.close();
