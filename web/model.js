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
  function filterRows(rows, filters = {}) {
    // 'all' is explicit because summing every entity cannot recover unallocated
    // source budgets; group totals must retain the original cached Excel amount.
    if (Array.isArray(filters.entities) && filters.entities.length === 0) return [];
    const entities = filters.entityScope === 'all' ? null : filters.entities;
    const query = (filters.query || '').trim().toLocaleLowerCase('it');
    return rows.filter(row => {
      if (!selected(filters.sheets, row.sheet) || !selected(filters.years, row.year) ||
          !selected(filters.domains, row.domain) || !selected(filters.owners, row.owner || 'Non specificato')) return false;
      const nis2Value = (row.nis2 || '').trim().toLowerCase();
      const nis2Status = ['yes','nis 2','nis2'].includes(nis2Value) ? 'yes' : nis2Value === 'no' ? 'no' : 'missing';
      if (!statusSelected(filters.nis2, nis2Status)) return false;
      const priorityValue = (row.priority || '').trim().toLowerCase();
      const priorityStatus = ['yes','no'].includes(priorityValue) ? priorityValue : 'missing';
      if (!statusSelected(filters.priority, priorityStatus)) return false;
      const local = localAmount(row, entities);
      if (entities != null && row.allocationStatus === 'mapped' &&
          !(row.allocations || []).some(a => entities.includes(a.entityId))) return false;
      // Ambiguous rows remain visible for review; never silently convert unknown to 0.
      if (filters.localBudget === 'positive' && !(local > 0)) return false;
      if (filters.localBudget === 'zero' && local !== 0) return false;
      if (filters.localBudget === 'missing' && local !== null) return false;
      if (query && ![row.id,row.name,row.domain,row.owner,row.globalDescription,row.localDescription,row.applicableCountries,row.excelRow]
        .join(' ').toLocaleLowerCase('it').includes(query)) return false;
      return true;
    });
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
      'Budget visualizzato','Budget visualizzato EUR'];
    const selectedAmount = row => {
      const global=number(row.globalBudget),local=localAmount(row,entities);
      return scope==='global'?global:scope==='local'?local:global==null&&local==null?null:(global??0)+(local??0);
    };
    const values = rows.map(r => [r.sheet,r.excelRow,r.id,r.domain,r.name,r.year,r.owner,r.globalBudget,
      localAmount(r, entities),r.localComplete,r.localBusiness,r.localFormula,r.allocationStatus,r.allocationNote,
      (entities || []).join(' | '),r.nis2,r.priority,r.globalDescription,r.localDescription,r.applicableCountries,
      {all:'Global + Local',global:'Global',local:'Local'}[scope],selectedAmount(r)]);
    return '\uFEFF' + [headers, ...values].map(row => row.map(quote).join(';')).join('\r\n');
  }
  const api = {number,sum,money,localAmount,filterRows,totals,aggregate,csv};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.RemediationModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : window);
