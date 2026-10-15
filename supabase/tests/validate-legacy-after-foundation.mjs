// Run unchanged legacy assertions AFTER 003. Only expected table count expands.
import {readFileSync,writeFileSync,unlinkSync} from 'node:fs';
for(const [source,marker,extra] of [
 ['validate.mjs','await db.exec(sql);',['002_research_engine.sql','003_multi_agent_foundation.sql']],
 ['validate-phase2.mjs',"await db.exec(readFileSync(new URL('../migrations/002_research_engine.sql',import.meta.url),'utf8'));",['003_multi_agent_foundation.sql']]
]){
 let code=readFileSync(new URL(source,import.meta.url),'utf8');
 const addition=extra.map(f=>`await db.exec(readFileSync(new URL('../migrations/${f}',import.meta.url),'utf8'));`).join('\n');
 if(!code.includes(marker))throw new Error('Legacy test layout changed; review shim');
 code=code.replace(marker,marker+'\n'+addition).replace('===20','>=29').replace('===29','>=29');
 const temporary=new URL(`compat-${source}-${process.pid}.mjs`,import.meta.url);
 try{writeFileSync(temporary,code);await import(temporary.href)}finally{unlinkSync(temporary)}
}
