// Synthetic SQL cases. Local PGlite, NOT a hosted Supabase integration test.
import { PGlite } from '@electric-sql/pglite';
import { readFileSync } from 'node:fs';
const db=new PGlite();
await db.exec(readFileSync(new URL('../migrations/001_lab.sql',import.meta.url),'utf8'));
await db.exec(readFileSync(new URL('../migrations/002_research_engine.sql',import.meta.url),'utf8'));
let passed=0;
function assert(x){if(!x)throw new Error('assertion failed');}
async function ok(name,fn){await fn();passed++;console.log('PASS '+name);}
async function reject(name,sql,re){await ok(name,async()=>{let err;try{await db.exec(sql)}catch(e){err=e}assert(err&&re.test(String(err.message)))})}
await ok('additive migrations create 29 tables',async()=>assert((await db.query("select count(*)::int n from pg_tables where schemaname='lab'")).rows[0].n===29));
await ok('all tables RLS enabled',async()=>assert((await db.query("select count(*)::int n from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='lab' and c.relkind='r' and not c.relrowsecurity")).rows[0].n===0));
await ok('wallet remains 1000 TRY, pilot disabled',async()=>{const r=(await db.query('select * from lab.paper_wallet')).rows[0];assert(Number(r.balance_kurus)===100000&&!r.betting_enabled)});
await db.exec("create role phase2_browser; grant usage on schema lab to phase2_browser; set role phase2_browser");
await reject('browser cannot enqueue',"insert into lab.collection_jobs(source_id,kind,parameters,dedupe_key) values('x','collect','{}','x')",/permission denied/);
await reject('browser cannot claim',"select lab.claim_collection_job()",/permission denied/);
await reject('browser cannot read source health','select * from lab.source_health',/permission denied/);
await db.exec('reset role');
await db.exec("insert into lab.sources(id,status,license_url,review_expires) values('test','approved','https://example.invalid/license',now()+interval '1 day')");
const j=(await db.query("insert into lab.collection_jobs(source_id,kind,parameters,dedupe_key) values('test','collect','{}','test-1') returning id")).rows[0].id;
await reject('duplicate job key refused',"insert into lab.collection_jobs(source_id,kind,parameters,dedupe_key) values('test','collect','{}','test-1')",/duplicate key/);
const lease=(await db.query('select * from lab.claim_collection_job()')).rows[0];
await ok('claim sets expiring lease',async()=>assert(lease.id===j&&lease.status==='running'&&lease.lease_token&&lease.lease_until));
await ok('leased task not reclaimed early',async()=>assert((await db.query('select * from lab.claim_collection_job()')).rows.length===0));
await ok('incorrect lease cannot complete',async()=>assert(!(await db.query('select lab.complete_collection_job($1,gen_random_uuid(),\'done\') ok',[j])).rows[0].ok));
await db.query("update lab.collection_jobs set lease_until=now()-interval '1 second' where id=$1",[j]);
await ok('expired lease cannot complete',async()=>assert(!(await db.query("select lab.complete_collection_job($1,$2,'done') ok",[j,lease.lease_token])).rows[0].ok));
const lease2=(await db.query('select * from lab.claim_collection_job()')).rows[0];
await ok('expired job gets new token',async()=>assert(lease2.lease_token!==lease.lease_token));
await ok('current token completes once',async()=>assert((await db.query("select lab.complete_collection_job($1,$2,'done') ok",[j,lease2.lease_token])).rows[0].ok));
await ok('completed token cannot be replayed',async()=>assert(!(await db.query("select lab.complete_collection_job($1,$2,'done') ok",[j,lease2.lease_token])).rows[0].ok));
await reject('running status requires lease',"update lab.collection_jobs set status='running'",/check constraint/);
await reject('bad split boundaries refused',"insert into lab.dataset_manifests(dataset_sha256,evaluation_mode,score_definition,train_start,train_end_exclusive,validation_end_exclusive,test_end_exclusive,manifest) values(repeat('a',64),'retrospective','regulation90','2020-01-01','2019-01-01','2021-01-01','2022-01-01','{}')",/check constraint/);
const data=(await db.query("insert into lab.dataset_manifests(dataset_sha256,evaluation_mode,score_definition,train_start,train_end_exclusive,validation_end_exclusive,test_end_exclusive,manifest) values(repeat('a',64),'retrospective','regulation90','2010-01-01','2020-01-01','2022-01-01','2024-01-01','{}') returning id")).rows[0].id;
const model=(await db.query("insert into lab.research_model_runs(dataset_id,model_name,code_sha256,artifact_sha256,artifact,training_end,validation_metrics) values($1,'poisson',repeat('a',64),repeat('b',64),'{}','2019-12-31','{}') returning id",[data])).rows[0].id;
function pred({training='2019-12-31',day='2022-01-01',grid='[[0.1,0.2],[0.3,0.1]]',tail=.3,ph=.4}={}){return `insert into lab.research_score_predictions(model_run_id,match_ref,match_date,training_end,home_name,away_name,home_rate,away_rate,rho,grid,tail_probability,p_home,p_draw,p_away) values('${model}',gen_random_uuid()::text,'${day}','${training}','A','B',1,1,0,'${grid}',${tail},${ph},.3,.3)`}
await ok('valid normalized prediction accepted',()=>db.exec(pred()));
await reject('prediction cannot misstate training cutoff',pred({training:'2018-01-01'}),/model_training_cutoff_mismatch/);
await reject('prediction cannot precede training',pred({day:'2018-01-01'}),/check constraint/);
await reject('score mass enforced',pred({tail:.1}),/score_grid_mass/);
await reject('negative score probability refused',pred({grid:'[[-0.1,0.4],[0.3,0.1]]'}),/invalid_score_probability/);
await reject('outcome mass enforced',pred({ph:.5}),/check constraint/);
await reject('score predictions immutable',"update lab.research_score_predictions set home_rate=2",/append_only_table/);
await reject('model run immutable',"delete from lab.research_model_runs",/append_only_table/);
const raw=(await db.query("insert into lab.raw_snapshots(source_id,request_url,received_at,content_sha256,payload,data_kind) values('test','https://example.invalid/data',now(),repeat('a',64),'{}','real') returning id")).rows[0].id;
function ext(weight=0,pub="now()-interval '1 hour'"){return `insert into lab.external_score_forecasts(source_id,raw_snapshot_id,match_ref,published_at,kickoff_at,selection,ensemble_weight) values('test','${raw}','m',${pub},now()-interval '1 day','1-0',${weight})`}
await ok('historical forecast stored as unverified',async()=>{await db.exec(ext());assert(!(await db.query('select verified_prematch from lab.external_score_forecasts')).rows[0].verified_prematch)});
await reject('unvalidated external weight forced zero',ext(.5),/check constraint/);
await reject('future publication refused',ext(0,"now()+interval '1 day'"),/check constraint/);
await reject('external forecasts immutable',"update lab.external_score_forecasts set selection='2-0'",/append_only_table/);
console.log(`TOTAL ${passed} Phase 2 PostgreSQL checks passed. Hosted Supabase and concurrent network sessions NOT tested.`);
await db.close();
