import {PGlite} from '@electric-sql/pglite';
import {readFileSync} from 'node:fs';
const db=new PGlite();let count=0;
const check=(condition,name)=>{if(!condition)throw new Error(name);count++;console.log('PASS '+name)};
await db.exec('create role anon nologin;create role authenticated nologin;create role service_role nologin bypassrls');
for(const f of ['001_lab.sql','002_research_engine.sql','003_multi_agent_foundation.sql','004_cloud_security.sql','005_hosted_worker_membership.sql']){
 await db.exec(readFileSync(new URL('../migrations/'+f,import.meta.url),'utf8'));check(true,'migration '+f);
}
const scalar=async q=>(await db.query(q)).rows[0].v;
check(await scalar("select count(*)::int v from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='lab' and p.prosecdef and not ('search_path=pg_catalog, lab, pg_temp'=any(p.proconfig))")===0,'definer search_path includes pg_temp last');
for(const role of ['anon','authenticated','service_role']){
 check(!await scalar(`select has_schema_privilege('${role}','lab','usage') v`),role+' no schema access');
 check(!await scalar(`select has_function_privilege('${role}','lab.post_agent_message(jsonb)','execute') v`),role+' no definer execution');
}
await db.exec('begin;grant usage on schema lab to authenticated;grant select,update on lab.paper_wallet to authenticated;set local role authenticated');
check(await scalar('select count(*)::int v from lab.paper_wallet')===0,'RLS hides wallet even with temporary ACL');
check((await db.query('update lab.paper_wallet set balance_kurus=1 returning id')).rows.length===0,'RLS denies update with temporary ACL');
await db.exec('rollback');
check(await scalar('select balance_kurus::int v from lab.paper_wallet')===100000,'wallet unchanged');
check(await scalar('select betting_enabled v from lab.paper_wallet')===false,'pilot stays disabled');
console.log(`TOTAL ${count} Phase 0.1 PGlite checks passed; hosted/native NOT tested.`);
await db.close();
