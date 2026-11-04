/* Independent arithmetic examples; no customer workbook or copied calculations. */
const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../web/model.js');

const entities = [
  {id:'plant', localCategory:'complete-ot', otEligible:true},
  {id:'office', localCategory:'complete', otEligible:false},
  {id:'business', localCategory:'business', otEligible:false},
  {id:'legacy', localCategory:null, otEligible:null},
];
const source = [
  {key:'Remediations:4', id:'R.1', sheet:'Remediations', globalBudget:100,
   localTotal:80, localComplete:999, localBusiness:0, allocationStatus:'mapped',
   allocations:[{entityId:'plant',amount:20},{entityId:'office',amount:30},{entityId:'business',amount:30}]},
  {key:'OT:2', id:'OT.1', sheet:'OT', globalBudget:50, localTotal:10,
   allocationStatus:'mapped', allocations:[{entityId:'plant',amount:10}]},
  {key:'Remediations:26', id:'R.23', sheet:'Remediations', globalBudget:5,
   localTotal:40, allocationStatus:'ambiguous', allocations:[]},
  {key:'Remediations:27', id:'R.23', sheet:'Remediations', globalBudget:5,
   localTotal:60, allocationStatus:'ambiguous', allocations:[]},
  {key:'Remediations:29', id:'R.INS', sheet:'Remediations', globalBudget:null,
   localTotal:0, allocationStatus:'mapped',
   allocations:[{entityId:'office',amount:null},{entityId:'business',amount:0}]},
];
const category = (result,id) => result.categories.find(item=>item.id===id);

test('base plus OT reconcile once and preserve both unresolved duplicate rows',()=>{
  const result=M.budgetBreakdown(source,entities);
  assert.deepEqual([result.globalBase,result.globalOt,result.global],[110,50,160]);
  assert.deepEqual([result.localBase,result.localOt,result.localTotal],[180,10,190]);
  assert.deepEqual([result.unallocatedBase,result.unallocatedOt,result.unallocated],[100,0,100]);
  assert.equal(result.unresolvedSource,100);
  assert.equal(result.classificationAvailable,true);
  assert.equal(result.missingGlobal,1);
  assert.equal(result.categories.reduce((n,item)=>n+item.total,0)+result.unallocated,190);
});

test('entity classification owns charges even when the unit column has another category name',()=>{
  const result=M.budgetBreakdown(source,entities);
  for(const [id,base,ot,total,count] of [
    ['complete-ot',20,10,30,1],['complete',30,0,30,1],['business',30,0,30,1],
  ]){
    const item=category(result,id);
    assert.deepEqual([item.base,item.ot,item.total,item.entityCount],[base,ot,total,count]);
  }
  // Business receives the explicit allocation although localBusiness is zero.
  assert.equal(category(result,'business').base,30);
});

test('one selected Business entity has no invented OT or unresolved country budget',()=>{
  const rows=M.filterRows(source,{entities:['business'],entityScope:'selected'});
  const result=M.budgetBreakdown(rows,entities,['business']);
  assert.deepEqual([result.globalBase,result.globalOt,result.global],[110,0,110]);
  assert.deepEqual([result.localBase,result.localOt,result.localTotal],[30,0,30]);
  assert.equal(result.unallocated,0);
  assert.equal(result.unresolvedSource,100);
  assert.equal(result.missingLocal,2);
  assert.equal(category(result,'business').entityCount,1);
  assert.equal(category(result,'complete-ot').entityCount,0);
});

test('unknown allocation remains unknown while an explicit zero remains known',()=>{
  const missing=M.budgetBreakdown([source.at(-1)],entities,['office']);
  const zero=M.budgetBreakdown([source.at(-1)],entities,['business']);
  assert.equal(missing.missingLocal,1);
  assert.equal(category(missing,'complete').missing,1);
  assert.equal(zero.missingLocal,0);
  assert.equal(category(zero,'business').missing,0);
  assert.equal(category(zero,'business').total,0);
});

test('unclassified legacy entities retain mapped budgets without guessing categories',()=>{
  const legacy=entities.map(item=>({...item,localCategory:null,otEligible:null}));
  const result=M.budgetBreakdown(source,legacy);
  assert.equal(result.classificationAvailable,false);
  assert.equal(category(result,'unclassified').entityCount,4);
  assert.deepEqual([category(result,'unclassified').base,category(result,'unclassified').ot],[80,10]);
  assert.equal(result.unallocated,100);
});

test('empty row and entity selections report actual zeros without changing eligibility',()=>{
  const result=M.budgetBreakdown([],entities,[]);
  for(const key of ['globalBase','globalOt','global','localBase','localOt','localTotal','unallocated'])assert.equal(result[key],0);
  assert.ok(result.categories.every(item=>item.entityCount===0&&item.total===0));
});
