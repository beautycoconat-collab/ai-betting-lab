import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const data=JSON.parse(readFileSync('public/data/dashboard.json','utf8'));
assert.equal(data.schema_version,'1.0'); assert.equal(data.execution_enabled,false); assert.equal(data.pilot_enabled,false);
assert.equal(data.roles.length,14);
assert(data.history.every(f=>f.mode==='retrospective'));
for(const f of data.history)for(const m of Object.values(f.models)){
 assert(Math.abs(m.p_1x2.reduce((a,b)=>a+b,0)-1)<1e-9);
 assert(m.p_1x2.every(p=>p>=0&&p<=1)); assert(m.training_end<f.date);
}
for(const file of ['public/app.js','public/app.css','public/index.html'])assert(readFileSync(file,'utf8').length>100);
console.log(`Dashboard publication checks passed: ${data.history.length} historical fixtures, pilot disabled.`);
