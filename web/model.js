/* Pure, deterministic view calculations. No network or AI services. */
(function (root) {
  'use strict';
  const number = (value) => typeof value === 'number' && Number.isFinite(value) ? value : null;
  const sum = (rows, field) => rows.reduce((total, row) => total + (number(row[field]) ?? 0), 0);
  const money = (value, compact = false) => value == null ? 'Non stimato' : new Intl.NumberFormat('it-IT', {
    style: 'currency', currency: 'EUR', maximumFractionDigits: compact || !Number.isInteger(value) ? 2 : 0,
    ...(compact ? { notation: 'compact' } : {}),
  }).format(value);
  // null/undefined means unrestricted; an explicitly empty selection means none.
  const selected = (items, value) => items == null || (Array.isArray(items) && items.some(item => String(item) === String(value ?? '')));
  const statusSelected = (items, status) => items == null || items === 'all' ||
    (Array.isArray(items) ? items.includes(status) : items === status);
  function localAmount(row, entities = null) {
    if (entities == null) return number(row.localTotal);
    if (!entities.length) return 0;
    if (row.allocationStatus !== 'mapped') return null;
    const allocations = (row.allocations || []).filter(a => entities.includes(a.entityId));
    if (allocations.some(a => number(a.amount) == null)) return null;
    return allocations.reduce((total, allocation) => total + allocation.amount, 0);
  }
  function remediationBudget(row, entities=null, scope='all') {
    const global=number(row.globalBudget),local=localAmount(row,entities);
    const total=scope==='global'?global:scope==='local'?local:global==null&&local==null?null:(global??0)+(local??0);
    return money(total,true)+(scope==='all'?` · Global ${money(global,true)} · Local ${money(local,true)}`:'');
  }
  function remediationTags(row) {
    const tags=[];
    const budget=String(row.capexOpex||'').trim().toLowerCase();
    if(budget==='capex'||budget==='opex')tags.push({label:budget.toUpperCase(),kind:budget});
    if(row.sheet==='OT')tags.push({label:'OT',kind:'ot'});
    else if(row.sheet==='Remediations')tags.push({label:'CMA, WIFI & VA',kind:'cma'});
    if(['yes','nis 2','nis2'].includes(String(row.nis2||'').trim().toLowerCase()))tags.push({label:'NIS2',kind:'nis2'});
    return tags;
  }
  function attributeValues(row, field) {
    if(field==='risk'&&Array.isArray(row.riskTypes))return row.riskTypes.length?row.riskTypes:['Non specificato'];
    if(field==='impact'&&Array.isArray(row.impactTypes))return row.impactTypes.length?row.impactTypes:['Non specificato'];
    if(field==='riskLevel')return [row.riskLevel||({Alto:'High',Medio:'Medium',Basso:'Low'}[row.impact])||'Non specificato'];
    return [row[field]||'Non specificato'];
  }
  function attributeGroups(rows, field, entities=null) {
    const groups=new Map();
    for(const row of rows)for(const label of new Set(attributeValues(row,field))){
      if(!groups.has(label))groups.set(label,[]);
      groups.get(label).push(row);
    }
    return [...groups].map(([label,records])=>({label,rows:records,...totals(records,entities)}));
  }
  function filterRows(rows, filters = {}) {
    // 'all' is explicit because summing every entity cannot recover unallocated
    // source budgets; group totals must retain the original cached Excel amount.
    if (Array.isArray(filters.entities) && filters.entities.length === 0) return [];
    const entities = filters.entityScope === 'all' ? null : filters.entities;
    const query = (filters.query || '').trim().toLocaleLowerCase('it');
    return rows.filter(row => {
      if (!selected(filters.sheets, row.sheet) || !selected(filters.years, row.year) ||
          !selected(filters.domains, row.domain) || !selected(filters.owners, row.owner || 'Non specificato')) return false;
      if (['capexOpex','risk','impact','riskLevel','remediationType'].some(field => !attributeValues(row,field).some(value=>selected(filters[field],value)))) return false;
      const nis2Value = (row.nis2 || '').trim().toLowerCase();
      const nis2Status = ['yes','nis 2','nis2'].includes(nis2Value) ? 'yes' : nis2Value === 'no' ? 'no' : 'missing';
      if (!statusSelected(filters.nis2, nis2Status)) return false;
      const priorityValue = (row.priority || '').trim().toLowerCase();
      const priorityStatus = ['yes','no'].includes(priorityValue) ? priorityValue : ['n/a','na'].includes(priorityValue)?'na':'missing';
      if (!statusSelected(filters.priority, priorityStatus)) return false;
      const local = localAmount(row, entities);
      if (entities != null && row.allocationStatus === 'mapped' &&
          !(row.allocations || []).some(a => entities.includes(a.entityId))) return false;
      // Ambiguous rows remain visible for review; never silently convert unknown to 0.
      if (filters.localBudget === 'positive' && !(local > 0)) return false;
      if (filters.localBudget === 'zero' && local !== 0) return false;
      if (filters.localBudget === 'missing' && local !== null) return false;
      if (query && ![row.id,row.name,row.domain,row.owner,row.globalDescription,row.localDescription,row.applicableCountries,row.capexOpex,row.risk,row.impact,row.riskTypes,row.impactTypes,Object.values(row.impactLevels||{}),row.riskLevel,row.remediationType,row.capexOpexNote,row.excelRow]
        .join(' ').toLocaleLowerCase('it').includes(query)) return false;
      return true;
    });
  }
  // Only declared metadata may enter the investment map; never fill gaps.
  function investmentRows(rows) {
    return rows.filter(row => ['capex','opex'].includes(String(row.capexOpex||'').trim().toLowerCase())
      && attributeValues(row,'risk').some(value=>String(value).trim()&&String(value).trim().toLowerCase()!=='non specificato'));
  }
  function totals(rows, entities = null) {
    return {
      global: sum(rows, 'globalBudget'),
      local: rows.reduce((n, r) => n + (localAmount(r, entities) ?? 0), 0),
      missingGlobal: rows.filter(r => number(r.globalBudget) == null).length,
      missingLocal: rows.filter(r => localAmount(r, entities) == null).length,
      unresolvedLocal: entities != null && entities.length ? sum(rows.filter(r => r.allocationStatus !== 'mapped'), 'localTotal') : 0,
      count: rows.length,
    };
  }
  function aggregate(rows, field, entities = null) {
    const groups = new Map();
    for (const row of rows) {
      const label = String(row[field] || 'Non specificato');
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label).push(row);
    }
    return Array.from(groups, ([label, records]) => ({ label, rows: records, ...totals(records, entities) }));
  }
  function budgetBreakdown(rows, entities, selectedEntities = null) {
    const definitions=[['complete-ot','Local Complete + OT'],['complete','Local Complete senza OT'],['business','Local Business'],['unclassified','Entità non classificate']];
    const known=new Set(definitions.slice(0,3).map(([id])=>id));
    const chosen=entities.filter(entity=>selectedEntities===null||selectedEntities.includes(entity.id));
    const types=new Map(chosen.map(entity=>[entity.id,known.has(entity.localCategory)?entity.localCategory:'unclassified']));
    const categories=new Map(definitions.map(([id,label])=>[id,{id,label,entityCount:[...types.values()].filter(value=>value===id).length,
      base:0,ot:0,total:0,missing:0,known:0,baseMissing:0,otMissing:0,baseKnown:0,otKnown:0}]));
    const result={globalBase:0,globalOt:0,global:0,localBase:0,localOt:0,localTotal:0,
      unallocatedBase:0,unallocatedOt:0,unallocated:0,classificationAvailable:[...types.values()].some(value=>value!=='unclassified'),
      missingGlobal:0,missingLocal:0,unresolvedSource:0,rowCount:rows.length,baseCount:0,otCount:0,
      missingGlobalBase:0,missingGlobalOt:0,missingLocalBase:0,missingLocalOt:0};
    for(const row of rows){
      const ot=row.sheet==='OT',suffix=ot?'Ot':'Base',component=ot?'ot':'base';
      const global=number(row.globalBudget),local=localAmount(row,selectedEntities);
      result[ot?'otCount':'baseCount']++;
      result['global'+suffix]+=global??0;result['local'+suffix]+=local??0;
      result['missingGlobal'+suffix]+=global===null?1:0;result['missingLocal'+suffix]+=local===null?1:0;
      if(row.allocationStatus!=='mapped'){result.unresolvedSource+=number(row.localTotal)??0;continue;}
      for(const allocation of row.allocations||[]){
        const category=categories.get(types.get(allocation.entityId));if(!category)continue;
        const value=number(allocation.amount);
        if(value===null){category.missing++;category[component+'Missing']++;}
        else{category[component]+=value;category.known++;category[component+'Known']++;}
      }
    }
    for(const category of categories.values())category.total=category.base+category.ot;
    result.categories=[...categories.values()];
    result.global=result.globalBase+result.globalOt;result.localTotal=result.localBase+result.localOt;
    result.missingGlobal=result.missingGlobalBase+result.missingGlobalOt;result.missingLocal=result.missingLocalBase+result.missingLocalOt;
    if(selectedEntities===null){
      result.unallocatedBase=result.localBase-result.categories.reduce((sum,category)=>sum+category.base,0);
      result.unallocatedOt=result.localOt-result.categories.reduce((sum,category)=>sum+category.ot,0);
      for(const key of ['unallocatedBase','unallocatedOt'])if(Math.abs(result[key])<1e-9)result[key]=0;
    }
    result.unallocated=result.unallocatedBase+result.unallocatedOt;
    result.missingAllocationCount=result.categories.reduce((sum,category)=>sum+category.missing,0);
    return result;
  }
  function csv(rows, entities = null, scope = 'all') {
    const quote = value => {
      let text = String(value ?? '');
      // Spreadsheet formula injection can also hide after whitespace.
      if (/^[\s]*[=+\-@]/.test(text)) text = "'" + text;
      return '"' + text.replaceAll('"', '""') + '"';
    };
    const headers = ['Foglio','Riga Excel','ID originale','Dominio','Remediation','Anno','Owner','Budget Global EUR (non ripartito)',
      entities != null ? 'Budget Local EUR (entità selezionate)' : 'Budget Local complessivo EUR',
      'Local Complete unitario EUR','Local BO unitario EUR','Formula Local originale','Stato attribuzione','Nota attribuzione',
      'Country / LE selezionate','NIS2','Priorità','Descrizione Global','Descrizione Local','Applicabilità originale (da verificare)',
      'Capex/Opex','Risk Type','Impact Type','Impatto legacy','Risk Level','Type Of Remediation','Note Capex/Opex','Foglio sorgente','Intestazione priorità originale','Stime da definire originali','Owner nel file originale','Budget visualizzato','Budget visualizzato EUR',...(rows.some(row=>row.impactLevels)?['Reputational Impact','Regulatory Impact','Economic Impact','Operational Impact']:[])];
    const selectedAmount = row => {
      const global=number(row.globalBudget),local=localAmount(row,entities);
      return scope==='global'?global:scope==='local'?local:global==null&&local==null?null:(global??0)+(local??0);
    };
    const values = rows.map(r => [r.sheet,r.excelRow,r.id,r.domain,r.name,r.year,r.owner,r.globalBudget,
      localAmount(r, entities),r.localComplete,r.localBusiness,r.localFormula,r.allocationStatus,r.allocationNote,
      (entities || []).join(' | '),r.nis2,r.priority,r.globalDescription,r.localDescription,r.applicableCountries,
      r.capexOpex||'',attributeValues(r,'risk').filter(v=>v!=='Non specificato').join(' | '),(Array.isArray(r.impactTypes)?r.impactTypes.join(' | '):''),r.impact||'',attributeValues(r,'riskLevel').filter(v=>v!=='Non specificato').join(' | '),r.remediationType||'',r.capexOpexNote||'',r.sourceSheet||r.sheet,r.prioritySourceHeader||'',Object.entries(r.sourceBudgetMarkers||{}).map(([field,value])=>field+': '+value).join(' | '),r.sourceOwner??r.owner,{all:'Global + Local',global:'Global',local:'Local'}[scope],selectedAmount(r),...(rows.some(row=>row.impactLevels)?['Reputational','Regulatory','Economic','Operational'].map(type=>r.impactLevels?.[type]||''):[])]);
    return '\uFEFF' + [headers, ...values].map(row => row.map(quote).join(';')).join('\r\n');
  }
  const api = {remediationTags,remediationBudget,attributeValues,attributeGroups,number,sum,money,localAmount,filterRows,investmentRows,totals,aggregate,budgetBreakdown,csv};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.RemediationModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : window);
