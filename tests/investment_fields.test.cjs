const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const context={Intl};context.window=context;vm.createContext(context);
vm.runInContext(fs.readFileSync('web/model.js','utf8'),context);
const M=context.RemediationModel;
const rows=[{key:'a',sheet:'Remediations',capexOpex:'Capex',risk:'Cyber',impact:'Alto',globalBudget:100,localTotal:40},
{key:'b',sheet:'Remediations',capexOpex:'Opex',risk:'Compliance',impact:'Medio',globalBudget:200,localTotal:60},
{key:'c',sheet:'OT',globalBudget:50,localTotal:10}];
test('investment filters compose without duplicating or distributing budget',()=>{
 const found=M.filterRows(rows,{capexOpex:['Capex'],risk:['Cyber'],impact:['Alto']});
 assert.equal(found.length,1);assert.equal(found[0].key,'a');
 assert.equal(M.totals(found).global,100);assert.equal(M.totals(found).local,40);
 assert.equal(M.filterRows(rows,{capexOpex:['Capex'],risk:['Compliance']}).length,0);
 assert.equal(M.filterRows(rows,{impact:[]}).length,0);
});
test('unknown metadata includes OT explicitly and never invents its classification',()=>{
 const found=M.filterRows(rows,{impact:['Non specificato']});
 assert.equal(found.length,1);assert.equal(found[0].key,'c');
 assert.equal(M.filterRows(rows,{}).length,3);
});
test('CSV carries source attributes and still escapes spreadsheet formulas',()=>{
 const csv=M.csv([{...rows[0],risk:'=UNTRUSTED()'}]);
 assert.match(csv,/Capex\/Opex/);assert.match(csv,/Impatto/);
 assert.match(csv,/'=UNTRUSTED/);
});

test('investment map excludes missing or invalid classifications without altering source totals',()=>{
 const before=M.totals(rows);
 const found=M.investmentRows([...rows,{...rows[0],key:'missing-risk',risk:''},{...rows[0],key:'invalid-class',capexOpex:'Other'}]);
 assert.equal(found.length,2);assert.equal(found[0].key,'a');assert.equal(found[1].key,'b');
 assert.equal(M.totals(rows).global,before.global);assert.equal(rows.length,3);
});
