// Node render/interaction smoke checks; NOT browser/layout/mobile acceptance.
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const snapshot=JSON.parse(readFileSync('public/data/dashboard.json','utf8'));
const nodes=new Map();
const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',disabled:false,
 events:{},addEventListener(n,f){this.events[n]=f},querySelectorAll(){return[]},
 showModal(){this.open=true},close(){this.open=false}});return nodes.get(id)};
const requests=[];
let unsafe=false;
const context=vm.createContext({Intl,Date,Number,Error,encodeURIComponent,
 document:{querySelector:node,querySelectorAll:()=>[]},location:{hash:'#history'},
 window:{addEventListener(){}},fetch:async url=>{requests.push(url);return {ok:true,
 json:async()=>structuredClone(unsafe?{...snapshot,execution_enabled:true}:snapshot)}}});
vm.runInContext(readFileSync('public/app.js','utf8'),context);
await vm.runInContext('load()',context);
assert(node('#match-list').innerHTML.includes(snapshot.history[0].home));
context.location.hash='#research';vm.runInContext('render()',context);
assert(node('#match-list').innerHTML.includes('Yayımlanmış worker kaydı yok'));
const recorded=structuredClone(snapshot.history[0]);
Object.assign(recorded,{id:'worker-record',mode:'recorded_research',origin_mode:'retrospective',
 as_of:'2025-03-01T14:00:00+00:00',reviews:[{status:'abstain',round_no:2,risk_action:'skip'}],
 findings:[{issue_type:'low_sample',severity:'high',evidence_ids:['<unsafe>'],requested_action:'review'}],
 roles:[{id:'score_engine',status:'done'}]});
recorded.home='<img src=x onerror=alert(1)>';
context.recorded=recorded;vm.runInContext("data.research={records:[recorded]};render();openFixture('worker-record')",context);
assert(node('#detail').open);
assert(!node('#detail-content').innerHTML.includes('<img src=x'));
assert(node('#detail-content').innerHTML.includes('&lt;unsafe&gt;'));
assert(node('#detail-content').innerHTML.includes('Risk: skip'));
vm.runInContext("selectedModel='elo';renderDetail()",context);
assert(node('#detail-content').innerHTML.includes(recorded.models.elo.model_sha256));
vm.runInContext("selectedDate='2026-10-18'",context);await vm.runInContext('load()',context);
assert(requests.at(-1).includes('date=2026-10-18'));
unsafe=true;await vm.runInContext('load()',context);
assert(node('#workspace').innerHTML.includes('Veri yüklenemedi'));
console.log('Dashboard Node smoke checks passed: archive, research empty/detail, escaping, review, model switch, date request, unsafe feed. Browser QA not performed.');
