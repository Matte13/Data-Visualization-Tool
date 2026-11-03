/* CountryInvestments — deterministic visual associations between entities, years and local budgets. */
(function (root) {
  'use strict';

  const FALLBACK_YEARS = ['#4b72bf', '#1b9b89', '#8a63bc', '#ca8640', '#527d97', '#af667c'];
  const FALLBACK_DOMAINS = ['#3b8e9c', '#9270ad', '#b57f47', '#5f8e69', '#b56f7d'];
  const compareText = (a, b) => String(a).localeCompare(String(b), 'it', {numeric: true});
  const keyForYear = value => value == null ? '' : String(value);
  const yearLabel = value => value === '' ? 'Anno non specificato' : value;
  const isSelected = (values, value) => values == null || values.includes(String(value));

  function render({data, filters, esc, icon, money, model, colorForYear, colorForDomain}) {
    const sourceRows = data.rows || [];
    const allYears = [...new Set(sourceRows.map(row => keyForYear(row.year)))].sort(compareText);
    const years = allYears.filter(year => isSelected(filters.years, year));
    const entities = data.entities.filter(entity => isSelected(filters.entities, entity.id));
    const yearColor = year => typeof colorForYear === 'function' ? colorForYear(year) : FALLBACK_YEARS[Math.max(0, allYears.indexOf(year)) % FALLBACK_YEARS.length];
    const allDomains = [...new Set(sourceRows.map(row => row.domain || 'Non specificato'))].sort(compareText);
    const domainColor = domain => typeof colorForDomain === 'function' ? colorForDomain(domain) : FALLBACK_DOMAINS[Math.max(0, allDomains.indexOf(domain)) % FALLBACK_DOMAINS.length];

    function summarize(records, entityId) {
      const amount = model.totals(records, [entityId]);
      const known = records.filter(row => model.localAmount(row, [entityId]) != null);
      const unallocatedCount = records.filter(row => row.allocationStatus !== 'mapped').length;
      const missingEstimateCount = records.length - known.length - unallocatedCount;
      return {
        rows: records,
        count: records.length,
        knownCount: known.length,
        unknownCount: records.length - known.length,
        unknownLabel: unallocatedCount ? missingEstimateCount ? 'Non determinato' : 'Da attribuire' : 'Non stimato',
        value: known.length ? amount.local : records.length ? null : 0,
        state: !records.length ? 'empty' : !known.length ? 'unknown' : amount.missingLocal ? 'partial' : amount.local === 0 ? 'zero' : 'known',
      };
    }
    function filterForEntity(entityId, year) {
      const scope = {...filters, entities: [entityId], entityScope: 'selected'};
      if (year !== undefined) scope.years = [year];
      return model.filterRows(sourceRows, scope);
    }
    const cards = entities.map(entity => {
      const records = filterForEntity(entity.id);
      const summary = summarize(records, entity.id);
      const annual = years.map(year => ({year, ...summarize(filterForEntity(entity.id, year), entity.id)}));
      const domainGroups = model.aggregate(records.filter(row => model.localAmount(row, [entity.id]) != null), 'domain', [entity.id])
        .filter(group => group.local > 0).sort((a, b) => b.local - a.local || compareText(a.label, b.label));
      return {entity, summary, annual, domainGroups};
    }).sort((a, b) => (b.summary.value || 0) - (a.summary.value || 0) || compareText(a.entity.name, b.entity.name));

    const scaleMaximum = Math.max(1, ...cards.flatMap(card => card.annual.map(annual => annual.value || 0)));
    const assigned = cards.reduce((total, card) => total + (card.summary.value || 0), 0);
    const visibleRowKeys = new Set(cards.flatMap(card => card.summary.rows.map(row => row.key)));
    const visibleKnown = cards.some(card => card.summary.knownCount > 0);
    const partial = cards.some(card => card.summary.unknownCount > 0);
    const unallocatedRows = model.filterRows(sourceRows, {...filters, entities: null, entityScope: 'all', localBudget: 'all'})
      .filter(row => row.allocationStatus !== 'mapped');
    const unallocatedValue = model.sum(unallocatedRows, 'localTotal');
    const unallocatedHasValue = unallocatedRows.some(row => row.localTotal != null);
    const annualTotals = years.map(year => {
      const values = cards.map(card => card.annual.find(annual => annual.year === year));
      const knownCount = values.reduce((count, value) => count + value.knownCount, 0);
      const unknownCount = values.reduce((count, value) => count + value.unknownCount, 0);
      return {year, value: knownCount ? values.reduce((total, value) => total + (value.value || 0), 0) : unknownCount ? null : 0, partial: unknownCount > 0};
    });
    const groupGlobal = model.totals(model.filterRows(sourceRows, {...filters, entities: null, entityScope: 'all'}));
    const header = `<div class="country-section-heading"><div><h2>Budget Local per country e anno</h2><p>Seleziona un anno nella scheda di un’entità per aprire le remediation corrispondenti.</p></div><div class="country-aggregate"><span>Local attribuito alle entità selezionate</span><strong>${visibleKnown || !partial ? money(assigned) : 'Non determinato'}</strong><small>${entities.length} entità · ${visibleRowKeys.size} righe${partial ? ' · importi disponibili' : ''}</small></div></div>`;
    const legend = `<div class="country-year-legend" aria-label="Colori degli anni">${annualTotals.map(annual => `<div class="country-year-summary" style="--year-color:${esc(yearColor(annual.year))}"><span class="country-year-heading"><i></i>${esc(yearLabel(annual.year))}</span><strong>${money(annual.value)}</strong><small>Local attribuito${annual.partial ? ' · parziale' : ''}</small></div>`).join('')}</div>`;
    const explanation = `<div class="country-reading-guide">${icon('info',16)}<p><strong>Scala dei grafici.</strong> Le barre usano la stessa scala: ${money(scaleMaximum === 1 && !cards.some(card => card.annual.some(annual => annual.value > 0)) ? 0 : scaleMaximum)} corrispondono alla barra completa. Seleziona un anno per aprire la mappa.</p></div>`;
    const globalNote = `<div class="country-global-context">${icon('globe',16)}<span>Il budget <strong>Global resta di gruppo</strong> e non è distribuito alle singole country.${groupGlobal.missingGlobal && groupGlobal.missingGlobal === groupGlobal.count ? '' : ` Nel perimetro: ${money(groupGlobal.global)}.`} Qui sono rappresentate esclusivamente le attribuzioni Local ricostruibili dal file.</span></div>`;
    const unallocated = unallocatedRows.length ? `<div class="country-unallocated" role="note">${icon('warning',18)}<span><strong>${unallocatedHasValue ? money(unallocatedValue) + ' Local' : 'Budget Local non determinato'} senza attribuzione certa.</strong> ${unallocatedRows.length} ${unallocatedRows.length===1?'voce non è attribuita':'voci non sono attribuite'} alle singole entità. I totali del gruppo restano quelli della fonte.</span></div>` : '';

    if (!entities.length || !years.length || !cards.some(card => card.summary.count)) {
      return `<section class="country-investments">${header}${years.length ? legend : ''}${globalNote}<div class="country-empty">${icon('globe',34)}<h3>Nessun dato per questi filtri</h3><p>Seleziona almeno un’entità e un anno, oppure modifica gli altri filtri.</p></div>${unallocated}</section>`;
    }

    function annualBlock(annual, card) {
      const hasRows = annual.count > 0;
      const stateText = {empty:'Nessuna voce',unknown:'Non determinato',partial:'Stima parziale',zero:'Budget zero',known:`${annual.count} ${annual.count === 1 ? 'riga' : 'righe'} di remediation`}[annual.state];
      const valueText = annual.state === 'empty' ? '—' : annual.state === 'unknown' ? annual.unknownLabel : money(annual.value);
      const width = annual.value == null ? 0 : Math.max(0, annual.value / scaleMaximum * 100);
      return `<button class="country-year-button country-year-${annual.state}" data-country-year="${esc(annual.year)}" data-entity="${esc(card.entity.id)}" style="--year-color:${esc(yearColor(annual.year))}" ${hasRows ? '' : 'disabled'} aria-label="${esc(card.entity.name)}, ${esc(yearLabel(annual.year))}, ${esc(valueText)}, ${esc(stateText)}"><span class="country-year-title"><i></i>${esc(yearLabel(annual.year))}${icon('arrow',13)}</span><strong class="country-year-amount">${valueText}</strong><span class="country-bar-track"><span class="country-bar-fill" style="width:${width}%"></span>${annual.state === 'unknown' ? '<span class="country-bar-unknown"></span>' : ''}</span><span class="country-year-caption">${stateText}</span></button>`;
    }
    const grid = `<div class="country-investment-grid">${cards.map((card, index) => `<article class="country-card" data-country="${esc(card.entity.id)}"><header class="country-card-header"><span class="country-ordinal">${String(index + 1).padStart(2,'0')}</span><div><h3>${esc(card.entity.name)}</h3><span>${card.summary.count} ${card.summary.count === 1 ? 'riga' : 'righe'} nel perimetro${card.summary.unknownCount ? ` · ${card.summary.unknownCount} non determinate` : ''}</span></div><div class="country-card-budget"><span>Local attribuito</span><strong class="country-total">${card.summary.state === 'empty' ? '—' : card.summary.state === 'unknown' ? card.summary.unknownLabel : money(card.summary.value)}</strong>${card.summary.state === 'partial' ? '<small>Somma disponibile</small>' : ''}</div></header><div class="country-connection-line"><span>${icon('globe',13)} ${esc(card.entity.name)}</span><i></i><span>Investimenti per anno</span></div><div class="country-annual-flow" style="--country-year-count:${Math.min(years.length,3)}">${card.annual.map(annual => annualBlock(annual,card)).join('')}</div><footer class="country-card-footer"><div class="country-domain-links">${card.domainGroups.slice(0,3).map(group => `<span class="country-domain-chip" style="--domain-color:${esc(domainColor(group.label))}" title="${esc(group.label)} · ${esc(money(group.local))}"><i></i>${esc(group.label)}</span>`).join('')}${card.domainGroups.length > 3 ? `<span class="country-other-domains">+${card.domainGroups.length-3} domini</span>` : ''}${!card.domainGroups.length ? '<span class="country-other-domains">Nessun budget positivo attribuito</span>' : ''}</div><button class="country-explore" data-entity="${esc(card.entity.id)}">Remediation ${icon('arrow',13)}</button></footer></article>`).join('')}</div>`;
    return `<section class="country-investments">${header}${legend}${explanation}${globalNote}${unallocated}${grid}<p class="country-method-note">Attribuzioni economiche da formule e gruppi di LE_List: non certificano l’applicabilità operativa delle remediation. Zero, stima mancante e nessuna voce restano distinti.</p></section>`;
  }

  root.CountryInvestments = {render};
})(typeof globalThis !== 'undefined' ? globalThis : window);
