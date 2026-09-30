// Exercise dashboard logic in a DOM simulation; this is not visual browser QA.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'outputs/kbo_team_dashboard.html'), 'utf8');
const payload = source.match(/<script id="snapshot" type="application\/json">([\s\S]*?)<\/script>/)[1];
const app = [...source.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
class Element {
  constructor(id=''){this.id=id;this.children=[];this.events={};this.value='';this.textContent='';this.attrs={};}
  appendChild(child){this.children.push(child);return child;}
  replaceChildren(){this.children=[];}
  addEventListener(event,callback){this.events[event]=callback;}
  setAttribute(key,value){this.attrs[key]=value;}
  click(){this.events.click?.();}
}
const elements = Object.fromEntries([...source.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element(m[1])]));
elements.snapshot.textContent=payload;elements.season.value='2025';
const charts=[];
class Chart {
  static defaults={font:{}};
  constructor(element,config){this.config=config;this.data=config.data;this.options=config.options;charts.push(this);}
  update(){}
}
let csvBlob;
const context=vm.createContext({document:{getElementById:id=>elements[id],createElement:()=>new Element()},Chart,Blob,URL:{createObjectURL:blob=>{csvBlob=blob;return 'blob:test';},revokeObjectURL(){}},setTimeout:fn=>fn(),console});
vm.runInContext(app,context);
assert.equal(elements.tbody.children.length,10);
assert.match(elements['selected-title'].textContent,/LG/);
assert.equal(elements.k1.textContent,'60.7%');
assert.equal(charts[0].data.labels.length,10);
assert.match(elements['coverage-note'].textContent,/714/);
elements.season.value='2024';elements.season.events.change();
assert.match(elements.coverage.textContent,/720/);
assert.equal(elements.k1.textContent,'53.5%');
elements.team.value='all';elements.team.events.change();
assert.equal(elements.k1.textContent,'720');
const snapshot=JSON.parse(payload),rows=snapshot.rows.filter(r=>r.season===2024);
const weighted=rows.reduce((a,r)=>a+r.avg_velocity*r.measured_velocity_count,0)/rows.reduce((a,r)=>a+r.measured_velocity_count,0);
assert.equal(elements.k4.textContent,weighted.toFixed(1));
for(const metric of ['win_rate','run_differential_per_game','home_runs_per_game','batting_strikeout_rate','batting_walk_rate','avg_velocity','pitching_strikeout_rate','pitching_walk_rate']){
  elements['rank-metric'].value=metric;elements['rank-metric'].events.change();
  assert.equal(charts[0].data.datasets[0].data.length,10);
  assert.ok(charts[0].data.datasets[0].data.every(Number.isFinite));
  if(metric!=='win_rate'){elements['scatter-metric'].value=metric;elements['scatter-metric'].events.change();assert.ok(charts[1].data.datasets[0].data.every(r=>Number.isFinite(r.x)&&Number.isFinite(r.y)));}
}
// Sort win rate ascending and select a team using the rendered table.
elements.thead.children[0].children[5].children[0].click();
assert.equal(elements.tbody.children[0].children[0].children[0].textContent,'키움 히어로즈');
elements.tbody.children[0].children[0].children[0].click();
assert.equal(elements.team.value,'WO');
assert.equal(elements.k1.textContent,'40.3%');
elements.download.click();
csvBlob.text().then(csv=>{
  assert.equal(csv.trim().split('\r\n').length,11);
  assert.match(csv,/2024/);
  assert.doesNotMatch(csv,/^"2025",/m);
  console.log('PASS: season/team changes, 8 ranking metrics, 7 scatter metrics, weighted league velocity, table sort/select, 10-row CSV export. Chart rendering not tested.');
});
