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
 assert.match(csv,/Capex\/Opex/);assert.match(csv,/Impact Type/);
 assert.match(csv,/'=UNTRUSTED/);
});

test('investment map excludes missing or invalid classifications without altering source totals',()=>{
 const before=M.totals(rows);
 const found=M.investmentRows([...rows,{...rows[0],key:'missing-risk',risk:''},{...rows[0],key:'invalid-class',capexOpex:'Other'}]);
 assert.equal(found.length,2);assert.equal(found[0].key,'a');assert.equal(found[1].key,'b');
 assert.equal(M.totals(rows).global,before.global);assert.equal(rows.length,3);
});

test('multi-valued risk/impact filters count each source row once and remain independent',()=>{
 const multi=[{...rows[0],riskTypes:['Cyber','Compliance'],impactTypes:['Economic','Regulatory'],riskLevel:'High'},
 {...rows[1],riskTypes:['Compliance'],impactTypes:['Operational'],riskLevel:'Low'}];
 const found=M.filterRows(multi,{risk:['Cyber','Compliance'],impact:['Economic','Regulatory']});
 assert.equal(found.length,1);assert.equal(M.totals(found).global,100);
 assert.equal(M.attributeGroups(multi,'risk').find(g=>g.label==='Compliance').count,2);
 assert.equal(M.filterRows(multi,{riskLevel:['Low']}).length,1);
 assert.equal(M.attributeValues(multi[0],'impact').join(','),'Economic,Regulatory');
 assert.equal(M.attributeValues(multi[0],'riskLevel')[0],'High');
});

test('priority N/A is distinguishable from an empty priority',()=>{
 const data=[{...rows[0],priority:'N/A'},{...rows[1],priority:''}];
 assert.equal(M.filterRows(data,{priority:['na']}).length,1);
 assert.equal(M.filterRows(data,{priority:['na']})[0].key,'a');
 assert.equal(M.filterRows(data,{priority:['missing']})[0].key,'b');
});

test('four rated impacts stay independent of risk level and export without duplicating budgets',()=>{
 const row={...rows[0],riskTypes:['Cyber','Compliance'],impactTypes:['Reputational','Regulatory','Economic','Operational'],riskLevel:'High',impactLevels:{Reputational:'Low',Regulatory:'High',Economic:'Medium',Operational:'High'}};
 assert.deepEqual(M.attributeValues(row,'impact'),['Reputational','Regulatory','Economic','Operational']);
 assert.deepEqual(Array.from(M.attributeValues(row,'riskLevel')),['High']);
 assert.equal(M.filterRows([row],{impact:['Reputational']}).length,1);
 const groups=M.attributeGroups([row],'impact');
 assert.equal(groups.length,4);
 assert.ok(groups.every(group=>group.rows.length===1));
 const csv=M.csv([row]);
 assert.ok(csv.includes('"Reputational Impact";"Regulatory Impact";"Economic Impact";"Operational Impact"'));
 assert.ok(csv.endsWith('"Low";"High";"Medium";"High"'));
});
