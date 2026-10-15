// SYNTHETIC fixtures. PGlite is local PostgreSQL semantics, not hosted Auth or parallel sessions.
import {PGlite} from '@electric-sql/pglite';
import {readFileSync} from 'node:fs';
const db=new PGlite();
for(const f of ['001_lab.sql','002_research_engine.sql','003_multi_agent_foundation.sql']) await db.exec(readFileSync(new URL('../migrations/'+f,import.meta.url),'utf8'));
let passed=0;
const assert=x=>{if(!x)throw new Error('assertion failed')};
async function ok(label,fn){await fn();passed++;console.log('PASS '+label)}
async function reject(label,sql,args=[],pattern=/.+/){await ok(label,async()=>{let err;try{await db.query(sql,args)}catch(e){err=e}assert(err&&pattern.test(String(err.message)))})}
async function role(name){await db.exec('SET ROLE '+name)}
async function owner(){await db.exec('RESET ROLE')}
const scalar=async(sql,args=[])=>Object.values((await db.query(sql,args)).rows[0])[0];
await ok('all three migrations apply',async()=>assert(await scalar("SELECT count(*)::int FROM lab.agent_roles")===14));
await ok('all lab tables have RLS',async()=>assert(await scalar("SELECT count(*)::int FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='lab' AND c.relkind='r' AND NOT c.relrowsecurity")===0));
await ok('initial wallet and pilot unchanged',async()=>{const w=(await db.query('select * from lab.paper_wallet')).rows[0];assert(Number(w.balance_kurus)===100000&&!w.betting_enabled)});
await ok('50 TRY is disabled unverified assumption',async()=>{const r=(await db.query('select * from lab.coupon_rule_versions')).rows[0];assert(r.minimum_cost_kurus===5000&&!r.enabled&&r.assumption_status==='user_reported_unverified')});
await db.exec(`CREATE ROLE foundation_browser NOLOGIN;GRANT USAGE ON SCHEMA lab TO foundation_browser;`);
await role('foundation_browser');
await reject('browser cannot read raw evidence','select * from lab.raw_snapshots',[],/permission denied/);
await reject('browser cannot modify wallet','update lab.paper_wallet set balance_kurus=1',[],/permission denied/);
await reject('browser cannot create prediction','insert into lab.prediction_runs(fixture_id) values(gen_random_uuid())',[],/permission denied/);
await reject('browser cannot call message RPC',"select lab.post_agent_message('{}')",[],/permission denied/);
await owner();
await db.exec("insert into lab.sources(id,status,license_url,review_expires) values('foundation-test','approved','https://example.invalid/license',now()+interval '1 day')");
await db.exec("insert into lab.source_access_policies(source_id,revision,status,permission_url,license,review_expires,max_daily,min_interval_seconds) values('foundation-test',1,'approved','https://example.invalid/license','SYNTHETIC',now()+interval '1 day',1,0)");
const raw=await scalar("insert into lab.raw_snapshots(source_id,request_url,received_at,content_sha256,payload,data_kind) values('foundation-test','https://example.invalid/fixture',now()-interval '2 hours',repeat('a',64),'{}','real') returning id");
// 'real' is a synthetic test marker to exercise live provenance checks, not collected match data.
const rawNew=await scalar("insert into lab.raw_snapshots(source_id,request_url,received_at,content_sha256,payload,data_kind) values('foundation-test','https://example.invalid/new',now()-interval '90 minutes',repeat('b',64),'{}','real') returning id");
const home=await scalar("insert into lab.teams(name) values('SYNTHETIC A') returning id");
const away=await scalar("insert into lab.teams(name) values('SYNTHETIC B') returning id");
const competition=await scalar("insert into lab.competitions(canonical_key,name) values('SYNTHETIC','TEST') returning id");
const season=await scalar("insert into lab.seasons(competition_id,label) values($1,'TEST') returning id",[competition]);
const dataset=await scalar("insert into lab.dataset_manifests(dataset_sha256,evaluation_mode,score_definition,train_start,train_end_exclusive,validation_end_exclusive,test_end_exclusive,manifest) values(repeat('c',64),'retrospective','regulation90','2010-01-01','2020-01-01','2022-01-01','2024-01-01','{}') returning id");
const model=await scalar("insert into lab.model_versions(name,code_sha,parameters,trained_through,role,dataset_hash) values('SYNTHETIC model','code','{}','2019-12-31','champion',repeat('c',64)) returning id");
await db.query("insert into lab.model_version_contracts values($1,$2,'regulation90','local://test',repeat('d',64))",[model,dataset]);
async function fixture(){
 const id=await scalar("insert into lab.matches(competition,season,home_id,away_id,kickoff_at,status) values('SYNTHETIC','TEST',$1,$2,now()+interval '1 day','scheduled') returning id",[home,away]);
 await db.query("insert into lab.fixture_contexts values($1,$2,'regulation90','verified',false)",[id,season]);return id;
}
const match=await fixture();
const asOf=await scalar("select (now()-interval '1 hour')::text");
async function run(agent,matchId=match){await role('lab_'+agent);const id=await scalar("select lab.start_agent_run($1,$2,$3,'prematch')",[agent,matchId,asOf]);await owner();return id}
async function evidence(matchId,snapshot,quality='unknown'){
 const id=await scalar('select gen_random_uuid()');await role('lab_data_validator');await db.query("select lab.register_evidence($1,$2,$3,'regulation90',$4,'SYNTHETIC evidence')",[id,matchId,snapshot,quality]);await owner();return id;
}
const ev=await evidence(match,raw);const resolved=await evidence(match,rawNew,'verified');const red=await run('red_team');const referee=await run('scientific_referee');
const msg={schema_version:'1.0',message_id:await scalar('select gen_random_uuid()'),agent_run_id:red,fixture_id:match,agent_role:'red_team',created_at:asOf,input_snapshot_ids:[raw],evidence_ids:[ev],model_version_id:model,issue_type:'lineup_uncertainty',severity:'critical',requested_action:'scenario_analysis',status:'pending_review',numeric_override:null,note:'SYNTHETIC'};
await role('lab_red_team');
await ok('valid agent message accepted',async()=>assert(await scalar('select lab.post_agent_message($1)',[msg])===msg.message_id));
await ok('message retry idempotent',async()=>assert(await scalar('select lab.post_agent_message($1)',[msg])===msg.message_id));
await reject('changed payload conflicts','select lab.post_agent_message($1)',[{...msg,severity:'low'}],/idempotency_conflict/);
await reject('missing required JSON field','select lab.post_agent_message($1)',[{...msg,message_id:crypto.randomUUID(),evidence_ids:undefined}],/schema/);
await reject('wrong schema version','select lab.post_agent_message($1)',[{...msg,message_id:crypto.randomUUID(),schema_version:'2.0'}],/schema/);
await reject('numeric override refused','select lab.post_agent_message($1)',[{...msg,message_id:crypto.randomUUID(),numeric_override:.49}],/schema/);
await reject('unknown probability field refused','select lab.post_agent_message($1)',[{...msg,message_id:crypto.randomUUID(),p_home:.49}],/schema/);
await reject('nonexistent evidence refused','select lab.post_agent_message($1)',[{...msg,message_id:crypto.randomUUID(),evidence_ids:[crypto.randomUUID()]}],/evidence/);
await reject('forged score-engine role refused','select lab.post_agent_message($1)',[{...msg,message_id:crypto.randomUUID(),agent_role:'score_engine'}],/permission/);
await reject('Red Team cannot directly insert probabilities','insert into lab.score_probability_distributions(prediction_run_id) values(gen_random_uuid())',[],/permission denied/);
await reject('Red Team cannot call prediction RPC',"select lab.record_prediction(gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),'{}')",[],/permission denied/);
await owner();
await ok('one stored message',async()=>assert(await scalar('select count(*)::int from lab.agent_messages')===1));
const finding=await scalar('select id from lab.review_findings where message_id=$1',[msg.message_id]);
await role('lab_scientific_referee');
const first=await scalar("select lab.decide_review('review-first',$1,$2)",[finding,referee]);
await ok('review retry idempotent',async()=>assert(await scalar("select lab.decide_review('review-first',$1,$2)",[finding,referee])===first));
const second=await scalar("select lab.decide_review('review-second',$1,$2)",[finding,referee]);
await reject('third review refused',"select lab.decide_review('review-third',$1,$2)",[finding,referee],/review_limit/);
await owner();
await ok('second unresolved critical review abstains and skips',async()=>{const r=(await db.query('select * from lab.review_decisions where id=$1',[second])).rows[0];assert(r.status==='abstain'&&r.risk_action==='skip')});
await reject('review immutable',"update lab.review_decisions set status='approved'",[],/append_only/);
await ok('unknown/conflicting evidence supported',async()=>{await evidence(match,raw,'conflicting');assert(await scalar("select count(*)::int from lab.evidence_references where quality in ('unknown','conflicting')")===2)});
await role('lab_source_hunter');
await ok('first quota reservation accepted',async()=>assert(await scalar("select lab.reserve_source_request('foundation-test')")));
await ok('quota exhaustion safely returns false',async()=>assert(!await scalar("select lab.reserve_source_request('foundation-test')")));
await owner();
await role('lab_coordinator');
const job=await scalar("select lab.enqueue_workflow('test-task-0001','validate',$1)",[match]);
await ok('job enqueue retry same ID',async()=>assert(await scalar("select lab.enqueue_workflow('test-task-0001','validate',$1)",[match])===job));
await reject('job payload conflict',"select lab.enqueue_workflow('test-task-0001','model',$1)",[match],/idempotency_conflict/);
const child=await scalar("select lab.enqueue_workflow('test-task-child','validate',$1,'{}',$2)",[match,[job]]);
await role('lab_data_validator');
const claimed=(await db.query("select * from lab.claim_workflow('data_validator','worker-a')")).rows[0];
await ok('first worker claims job',async()=>assert(claimed.id===job));
await ok('second claim gets no leased job or blocked child',async()=>assert((await db.query("select * from lab.claim_workflow('data_validator','worker-b')")).rows.length===0));
await ok('wrong token cannot finish',async()=>assert(!await scalar("select lab.finish_workflow($1,gen_random_uuid(),'worker-a')",[job])));
await ok('current token finishes',async()=>assert(await scalar("select lab.finish_workflow($1,$2,'worker-a')",[job,claimed.lease_token])));
await ok('dependency becomes eligible',async()=>assert((await db.query("select * from lab.claim_workflow('data_validator','worker-b')")).rows[0].id===child));
await owner();
await db.query("update lab.workflow_jobs set lease_until=now()-interval '1 second' where id=$1",[child]);
await role('lab_data_validator');const reclaimed=(await db.query("select * from lab.claim_workflow('data_validator','worker-c')")).rows[0];
await ok('expired lease retried with new token',async()=>assert(reclaimed.id===child&&reclaimed.attempts===2));await owner();
function distribution(){const grid=[];for(let h=0;h<=20;h++){let row=[];for(let a=0;a<=20;a++){let factorial=n=>{let x=1;for(let i=2;i<=n;i++)x*=i;return x};row.push(Math.exp(-2)/(factorial(h)*factorial(a)))}grid.push(row)}const sum=grid.flat().reduce((a,b)=>a+b,0);let draw=grid.reduce((v,r,i)=>v+r[i],0);return {home_rate:1,away_rate:1,rho:0,grid,outside_grid_probability:Math.max(0,1-sum),p_1x2:[(1-draw)/2,draw,(1-draw)/2]}}
async function prediction(matchId){
 const feature=await scalar("insert into lab.feature_snapshots(fixture_id,score_target,feature_time,available_at,content_sha256,features) values($1,'regulation90',$2,now()-interval '2 hours',repeat('e',64),'{}') returning id",[matchId,asOf]);
 await db.query('insert into lab.feature_snapshot_inputs values($1,$2)',[feature,raw]);const agent=await run('score_engine',matchId);
 await role('lab_score_engine');const id=await scalar('select lab.record_prediction($1,$2,$3,$4,$5)',[matchId,model,feature,agent,distribution()]);await owner();return {id,feature,agent};
}
const prediction1=await prediction(match);
await role('lab_score_engine');
const prediction2=await scalar('select lab.record_prediction($1,$2,$3,$4,$5)',[match,model,prediction1.feature,prediction1.agent,distribution()]);
await reject('score worker cannot update history','update lab.prediction_runs set revision=90',[],/permission denied/);
await reject('score worker cannot modify wallet','update lab.paper_wallet set balance_kurus=1',[],/permission denied/);
await owner();
await ok('V1 V2 stored separately',async()=>assert(prediction1.id!==prediction2&&await scalar('select count(*)::int from lab.prediction_runs where fixture_id=$1',[match])===2));
await reject('even ordinary owner update is append-only','update lab.prediction_runs set revision=90',[],/append_only/);
await role('lab_score_engine');
const invalid=distribution();invalid.grid[0][0]+=.1;
await reject('numeric model inconsistency refused','select lab.record_prediction($1,$2,$3,$4,$5)',[match,model,prediction1.feature,prediction1.agent,invalid],/grid_model_mismatch/);await owner();
const badFeature=await scalar("insert into lab.feature_snapshots(fixture_id,score_target,feature_time,available_at,content_sha256,features) values($1,'final_including_extra_time',now()-interval '1 hour',now()-interval '2 hours',repeat('e',64),'{}') returning id",[match]);await db.query('insert into lab.feature_snapshot_inputs values($1,$2)',[badFeature,raw]);
await role('lab_score_engine');await reject('score targets cannot mix','select lab.record_prediction($1,$2,$3,$4,$5)',[match,model,badFeature,prediction1.agent,distribution()],/target_mismatch/);await owner();
const futureFeature=await scalar("insert into lab.feature_snapshots(fixture_id,score_target,feature_time,available_at,content_sha256,features) values($1,'regulation90',now()+interval '1 hour',now()+interval '1 hour',repeat('e',64),'{}') returning id",[match]);await db.query('insert into lab.feature_snapshot_inputs values($1,$2)',[futureFeature,raw]);
await role('lab_score_engine');await reject('future features rejected','select lab.record_prediction($1,$2,$3,$4,$5)',[match,model,futureFeature,prediction1.agent,distribution()],/time_leakage/);await owner();
await role('lab_dashboard');await ok('dashboard can read distributions',async()=>assert(await scalar('select count(*)::int from lab.score_probability_distributions')===2));await reject('dashboard cannot alter prediction','delete from lab.prediction_runs',[],/permission denied/);await owner();

// Build eligible synthetic decisions as trusted test fixture setup, not a running risk engine.
async function eligibleDecision(){
 const id=await fixture();const p=await prediction(id);const evidence1=await evidence(id,raw);const evidence2=await evidence(id,rawNew,'verified');const redRun=await run('red_team',id);const refRun=await run('scientific_referee',id);
 const m={...msg,message_id:crypto.randomUUID(),fixture_id:id,agent_run_id:redRun,evidence_ids:[evidence1]};await role('lab_red_team');await db.query('select lab.post_agent_message($1)',[m]);await owner();
 const f=await scalar('select id from lab.review_findings where message_id=$1',[m.message_id]);await role('lab_scientific_referee');const decision=await scalar('select lab.decide_review($1,$2,$3,$4)',['approve-'+id,f,refRun,evidence2]);await owner();
 const odds=await scalar("insert into lab.odds_snapshots(match_id,source_id,bookmaker,market,outcome,decimal_odds,source_updated_at,observed_at,raw_snapshot_id) values($1,'foundation-test','SYNTHETIC','1X2','H',2,now(),now(),$2) returning id",[id,raw]);
 const bet=await scalar("insert into lab.betting_decisions(prediction_run_id,review_decision_id,odds_id,action,maximum_stake_kurus,reason) values($1,$2,$3,'bet',5000,'SYNTHETIC fixture only') returning id",[p.id,decision,odds]);return {match:id,bet};
}
const one=await eligibleDecision(),two=await eligibleDecision(),three=await eligibleDecision();
await role('lab_risk_manager');await reject('pilot remains closed',"select lab.reserve_virtual_coupon('paper-test-1',$1,'paper-assumption-v1',5000)",[one.bet],/pilot_disabled/);await owner();
await db.exec("update lab.paper_wallet set betting_enabled=true,pilot_start=now()-interval '1 hour',pilot_end=now()-interval '1 hour'+interval '7 days'");
await role('lab_risk_manager');await reject('unverified rule not automatically enabled',"select lab.reserve_virtual_coupon('paper-test-1',$1,'paper-assumption-v1',5000)",[one.bet],/rule_or_risk/);await owner();
await db.exec("insert into lab.coupon_rule_versions values('synthetic-rule',5000,'verified','https://example.invalid/rules',true,10000,'Balanced',1,now())");
await role('lab_risk_manager');
await reject('below configurable minimum refused',"select lab.reserve_virtual_coupon('paper-test-1',$1,'synthetic-rule',1000)",[one.bet],/rule_or_risk/);
const coupon=await scalar("select lab.reserve_virtual_coupon('paper-test-1',$1,'synthetic-rule',5000)",[one.bet]);
await ok('coupon retry no second debit',async()=>assert(await scalar("select lab.reserve_virtual_coupon('paper-test-1',$1,'synthetic-rule',5000)",[one.bet])===coupon));
await scalar("select lab.reserve_virtual_coupon('paper-test-2',$1,'synthetic-rule',5000)",[two.bet]);
await reject('over 100 TRY combined daily budget refused',"select lab.reserve_virtual_coupon('paper-test-3',$1,'synthetic-rule',5000)",[three.bet],/daily_limit/);await owner();
await ok('exact 100 TRY spent and 900 TRY balance',async()=>assert(Number(await scalar('select balance_kurus from lab.paper_wallet'))===90000));
const event=await scalar("insert into lab.fixture_events(fixture_id,snapshot_id,event_type,quality,payload) values($1,$2,'cancelled','verified','{}') returning id",[one.match,raw]);
await role('lab_risk_manager');
const settlement=await scalar("select lab.settle_coupon_void('void-test-1',$1,$2)",[coupon,event]);
await ok('same coupon settlement idempotent',async()=>assert(await scalar("select lab.settle_coupon_void('void-test-1',$1,$2)",[coupon,event])===settlement));
await reject('different key cannot settle coupon twice',"select lab.settle_coupon_void('void-test-2',$1,$2)",[coupon,event],/idempotency_conflict/);
await reject('refund does not replenish daily cap',"select lab.reserve_virtual_coupon('paper-test-3',$1,'synthetic-rule',5000)",[three.bet],/daily_limit/);await owner();
await ok('wallet ledger reconciles after refund',async()=>assert(await scalar('select (select sum(amount_kurus) from lab.wallet_ledger)=(select balance_kurus from lab.paper_wallet)')));
await reject('settlement immutable','delete from lab.coupon_settlement_records',[],/append_only/);
await ok('PUBLIC cannot execute critical functions',async()=>assert(!await scalar("select has_function_privilege('foundation_browser','lab.reserve_virtual_coupon(text,uuid,text,integer)','EXECUTE')")));
console.log(`TOTAL ${passed} Phase 0 PostgreSQL checks passed. Parallel PostgreSQL sessions and hosted Supabase Auth NOT tested.`);
await db.close();
