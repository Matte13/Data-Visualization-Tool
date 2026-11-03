'use strict';
// Only fictional fixture data is used in the public test suite.
const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const M = require('../web/model.js');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(execFileSync(process.env.PYTHON || 'python', ['-c',
  "import json,sys;sys.path.insert(0,'tests');from fixtures import make_workbook;from app.workbook import parse_workbook;print(json.dumps(parse_workbook(make_workbook(),'demo.xlsx')))"
], {cwd:root, encoding:'utf8'}));
const filters = patch => ({query:'',sheets:['Remediations'],years:[],domains:[],owners:[],entities:[],scope:'all',localBudget:'all',nis2:'all',priority:'all',...patch});
const filtered = patch => M.filterRows(data.rows,filters(patch));
const source = row => data.rows.find(r=>r.key===`Remediations:${row}`);
const entity = index => `Demo Entity ${String(index).padStart(2,'0')}`;

test('main scope retains every source record with exact fictional reference totals',()=>{
  const t=M.totals(filtered());
  assert.equal(t.count,5);assert.equal(t.global,6400);assert.equal(t.local,3190);
  assert.equal(t.global+t.local,9590);assert.equal(t.missingGlobal,1);
});
test('OT is separate and adds to totals only when explicitly selected',()=>{
  assert.equal(filtered({sheets:['OT']}).length,2);
  const combined=M.totals(filtered({sheets:['Remediations','OT']}));
  assert.equal(combined.count,7);assert.equal(combined.global,7600);assert.equal(combined.local,3490);
});
test('annual aggregation includes ID-less source records',()=>{
  assert.deepEqual(M.aggregate(filtered(),'year').map(y=>[y.label,y.count,y.global,y.local]),[
    ['2027',1,1000,1380],['2028',2,5000,1810],['2029',2,400,0]
  ]);
});
test('owner totals preserve distinct rows with repeated source identifiers',()=>{
  const rows=filtered({owners:['Supplier A']});const t=M.totals(rows);
  assert.equal(t.count,3);assert.equal(t.global,4000);assert.equal(t.local,2190);
});
test('duplicate identifiers and missing identifiers remain independently navigable',()=>{
  assert.equal(filtered().filter(r=>r.id==='R.2').length,2);
  assert.equal(filtered().filter(r=>!r.id).length,1);
  assert.notEqual(source(5).key,source(6).key);
});
test('year, owner, domain and full-text filters combine deterministically',()=>{
  assert.deepEqual(filtered({years:['2028'],owners:['Supplier B'],domains:['Security'],query:'BACKUP'}).map(r=>r.key),['Remediations:5']);
});
test('search includes source descriptions and row references case-insensitively',()=>{
  assert.ok(filtered({query:'ORIGINAL GLOBAL TEXT 4'}).some(r=>r.key==='Remediations:4'));
  assert.ok(filtered({query:'governance'}).every(r=>r.domain==='Governance'));
});
test('yes, no and unspecified priority remain distinct',()=>{
  assert.equal(filtered({priority:'yes'}).length,1);
  assert.equal(filtered({priority:'no'}).length,2);
  assert.equal(filtered({priority:'missing'}).length,2);
});
test('NIS2 no and unknown values are never combined',()=>{
  const yes=filtered({sheets:[],nis2:'yes'}),no=filtered({sheets:[],nis2:'no'}),missing=filtered({sheets:[],nis2:'missing'});
  assert.equal(yes.length+no.length+missing.length,7);
  assert.ok(no.every(r=>r.nis2.toLowerCase()==='no'));
  assert.ok(missing.every(r=>!r.nis2));
});
test('entity allocations reconcile to mapped amounts without inventing ambiguous costs',()=>{
  const rows=filtered();const attributed=data.entities.reduce((total,e)=>total+M.totals(rows,[e.id]).local,0);
  assert.equal(attributed,2380);
  assert.equal(M.totals(rows).local-attributed,810);
});
test('ambiguous rows stay visible but have no fabricated entity budget',()=>{
  const rows=filtered({entities:[entity(1)]});
  assert.ok(rows.some(r=>r.key==='Remediations:6'));
  assert.equal(M.localAmount(source(6),[entity(1)]),null);
  assert.equal(M.totals(rows,[entity(1)]).unresolvedLocal,810);
});
test('multi-entity selection adds local allocations once and never multiplies Global',()=>{
  const r=source(4),entities=[entity(1),entity(2)];
  assert.equal(M.localAmount(r,entities),200);
  const t=M.totals([r],entities);assert.equal(t.global,1000);assert.equal(t.local,200);
});
test('country zero and missing local estimates stay separate',()=>{
  const zero=filtered({entities:[entity(1)],localBudget:'zero'});
  assert.ok(zero.some(r=>r.key==='Remediations:7'));
  assert.ok(!zero.some(r=>r.key==='Remediations:8'));
  assert.equal(M.localAmount(source(8),[entity(1)]),null);
  assert.ok(filtered({entities:[entity(1)],localBudget:'missing'}).some(r=>r.key==='Remediations:8'));
});
test('Local level combined with zero-budget filter still shows zero-budget rows',()=>{
  const zero=filtered({scope:'local',entities:[entity(1)],localBudget:'zero'});
  assert.ok(zero.some(r=>r.key==='Remediations:7'));
});
test('positive local filter excludes unresolved amounts explicitly',()=>{
  const rows=filtered({entities:[entity(1)],localBudget:'positive'});
  assert.ok(rows.length>0);
  assert.ok(rows.every(r=>M.localAmount(r,[entity(1)])>0));
  assert.ok(!rows.some(r=>r.key==='Remediations:6'));
});
test('special group allocation follows its explicit members only',()=>{
  const r=source(5);
  assert.equal(M.localAmount(r,[entity(1)]),200);
  assert.equal(M.localAmount(r,[entity(6)]),0);
  assert.equal(M.localAmount(r,[entity(1),entity(2)]),400);
});
test('CSV keeps source text while neutralizing spreadsheet formula injection',()=>{
  const r={...source(4),name:'  =HYPERLINK("x")',owner:'@SUM(1)',globalDescription:'Line one\nLine "two"'};
  const csv=M.csv([r],[entity(1)]);
  assert.ok(csv.startsWith('\uFEFF"Foglio";'));
  assert.ok(csv.includes('"\'  =HYPERLINK(""x"")"'));
  assert.ok(csv.includes('"\'@SUM(1)"'));
  assert.ok(csv.includes('"Line one\nLine ""two"""'));
  assert.ok(csv.includes('Budget Local EUR (entità selezionate)'));
  assert.ok(csv.includes('"1000";"100";'));
});
test('CSV blank estimates stay blank while zero remains numeric zero',()=>{
  assert.ok(M.csv([source(8)]).includes('"";"0";"";"0";'));
});
test('money formatting distinguishes absent estimates, zero and cents',()=>{
  assert.equal(M.money(null),'Non stimato');assert.notEqual(M.money(0),'Non stimato');
  assert.match(M.money(1234.56),/,56\s*€/);
  assert.equal(M.money(1234.56).replace(/\D/g,''),'123456');
});
test('empty result remains a real zero-row result',()=>{
  const rows=filtered({query:'does not exist in the synthetic source'});
  assert.equal(rows.length,0);assert.equal(M.totals(rows).count,0);
});
