/* OwnerMap — offline year → owner → domain → remediation associations. */
(function (root) {
  'use strict';

  const PAGE_SIZE = 6;
  const OWNER_COLORS = ['#58738c', '#68927d', '#9b84aa', '#b09a73'];
  const YEAR_COLORS = ['#7964cf', '#d8942f', '#ce668b', '#4b91ba', '#81994d', '#c77a4d'];
  const DOMAIN_COLORS = ['#478ba8', '#9375be', '#4a9c83', '#cd8d4c', '#657ec0', '#b56a8a', '#899b43', '#629caa', '#af7f5f'];
  const compare = (a, b) => String(a).localeCompare(String(b), 'it', {numeric: true});
  const yearKey = row => String(row.year ?? '');
  const ownerKey = row => String(row.owner || 'Non specificato');
  const domainKey = row => String(row.domain || 'Non specificato');
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  function groupBy(rows, key) {
    const result = new Map();
    for (const row of rows) {
      const label = key(row);
      if (!result.has(label)) result.set(label, []);
      result.get(label).push(row);
    }
    return result;
  }

  function wrap(text, width, lines = 2) {
    const result = [''];
    for (const word of String(text ?? '').split(/\s+/).filter(Boolean)) {
      if (result[result.length - 1] && (result[result.length - 1] + ' ' + word).length > width) result.push(word);
      else result[result.length - 1] = (result[result.length - 1] + ' ' + word).trim();
    }
    if (result.length > lines) {
      result.length = lines;
      result[lines - 1] = result[lines - 1].slice(0, width - 1) + '…';
    }
    // A single long source token must not draw over adjacent columns.
    return result.map(line => line.length > width ? line.slice(0, width - 1) + '…' : line);
  }

  function render(options = {}) {
    const {
      data, rows: suppliedRows, year: requestedYear, owner: requestedOwner,
      domain: requestedDomain, page: requestedPage, model: suppliedModel,
      colorForYear: suppliedYearColor, colorForDomain: suppliedDomainColor,
      scope = 'all', entitySelection = null,
    } = options;
    const rows = Array.isArray(suppliedRows) ? suppliedRows : (data?.rows || []);
    const model = suppliedModel || root.RemediationModel;
    const esc = typeof options.esc === 'function' ? options.esc : escapeHtml;
    const icon = typeof options.icon === 'function' ? options.icon : () => '';
    const money = options.money || model.money;
    const entities = typeof entitySelection === 'function' ? entitySelection() : entitySelection;
    const yearGroups = groupBy(rows, yearKey);
    const years = [...yearGroups.keys()].sort((a, b) => (a === '') - (b === '') || compare(a, b));
    const incomingYear = requestedYear == null ? null : String(requestedYear);
    const year = incomingYear != null && yearGroups.has(incomingYear) ? incomingYear : years[0] ?? null;
    const changedYear = incomingYear != null && incomingYear !== year;
    const yearRows = year == null ? [] : yearGroups.get(year);
    const ownerGroups = groupBy(yearRows, ownerKey);
    const domainGroups = groupBy(yearRows, domainKey);
    const owners = [...ownerGroups.keys()].sort(compare);
    const ownerPalette = [...new Set((Array.isArray(data?.rows) ? data.rows : rows).map(ownerKey))].sort(compare);
    const ownerColors = new Map(ownerPalette.map((label, index) => [label, OWNER_COLORS[index % OWNER_COLORS.length]]));
    const domains = [...domainGroups.keys()].sort(compare);
    const incomingOwner = requestedOwner == null ? null : String(requestedOwner);
    const owner = !changedYear && incomingOwner != null && ownerGroups.has(incomingOwner) ? incomingOwner : null;
    const changedOwner = incomingOwner != null && incomingOwner !== owner;
    const focusedOwnerRows = owner == null ? yearRows : ownerGroups.get(owner);
    const focusedDomains = groupBy(focusedOwnerRows, domainKey);
    const incomingDomain = requestedDomain == null ? null : String(requestedDomain);
    const domain = !changedYear && !changedOwner && incomingDomain != null && focusedDomains.has(incomingDomain) ? incomingDomain : null;
    const focused = domain == null ? [] : focusedDomains.get(domain);
    const pages = Math.max(1, Math.ceil(focused.length / PAGE_SIZE));
    const requestedNumber = Number(requestedPage);
    const page = domain == null ? 0 : Math.max(0, Math.min(pages - 1, Number.isFinite(requestedNumber) ? Math.trunc(requestedNumber) : 0));
    const visible = focused.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
    const yearColor = value => suppliedYearColor ? suppliedYearColor(value) : YEAR_COLORS[Math.max(0, years.indexOf(value)) % YEAR_COLORS.length];
    const domainColor = value => suppliedDomainColor ? suppliedDomainColor(value) : DOMAIN_COLORS[Math.max(0, domains.indexOf(value)) % DOMAIN_COLORS.length];
    const yearLabel = value => value === '' ? 'Anno non specificato' : value;
    const sourceRef = row => `${row.sourceSheet || row.sheet || 'Excel'} · riga ${row.excelRow ?? '—'}`;
    const rowKey = row => String(row.key ?? `${row.sheet || 'Excel'}:${row.excelRow ?? ''}`);
    const text = (value, x, y, width, lines = 2, className = 'node-title') => `<text class="${className}" x="${x}" y="${y}">${wrap(value, width, lines).map((line, index) => `<tspan x="${x}" dy="${index ? 17 : 0}">${esc(line)}</tspan>`).join('')}</text>`;
    const amount = (records, compact = true) => {
      if (!records.length) return '—';
      const total = model.totals(records, entities);
      const unknownGlobal = total.count > 0 && total.missingGlobal === total.count;
      const unknownLocal = total.count > 0 && total.missingLocal === total.count;
      if ((scope === 'global' && unknownGlobal) || (scope === 'local' && unknownLocal) || (unknownGlobal && unknownLocal)) return 'Non stimato';
      return money((scope === 'local' ? 0 : total.global) + (scope === 'global' ? 0 : total.local), compact);
    };
    const edge = (type, from, to, path, active = false, muted = false) => `<path class="map-edge${active ? ' highlight' : ''}${muted ? ' muted' : ''}" data-owner-map-edge="${type}" data-owner-map-from="${esc(from)}" data-owner-map-to="${esc(to)}" d="${path}" style="marker-end:url(#owner-map-arrow)"/>`;
    const title = '<div class="panel-title"><div><h2>Mappa per anno e owner</h2></div><button class="button small" data-action="png">' + icon('download', 15) + ' Salva PNG</button></div>';
    const explanation = '<div class="map-explanation">Seleziona un anno e, se necessario, un owner. Apri un dominio per consultare le remediation; doppio click su una remediation per i dettagli. Le frecce rappresentano le associazioni presenti nel file.</div>';

    if (!rows.length) return {
      html: `<section class="panel map-panel owner-map-panel">${title}${explanation}<div class="empty-state"><h2>Nessuna remediation</h2><p>Modifica i filtri per visualizzare le associazioni.</p></div></section>`,
      year: null, owner: null, domain: null, page: 0,
    };

    const yearY = index => 85 + index * 128;
    const ownerY = index => 75 + index * 92;
    const domainY = index => 75 + index * 86;
    const leafY = index => 75 + index * 122;
    const height = Math.max(610, yearY(years.length - 1) + 125,
      ownerY(owners.length - 1) + 95, domainY(domains.length - 1) + 90,
      leafY(visible.length - 1) + 130);
    const ownerIndex = new Map(owners.map((label, index) => [label, index]));
    const domainIndex = new Map(domains.map((label, index) => [label, index]));
    const yearNodes = years.map((label, index) => {
      const y = yearY(index);
      const long = label === '';
      return `<g class="map-node year-node${label === year ? ' chosen' : ''}" role="button" tabindex="0" data-owner-map-year="${esc(label)}" style="--year-color:${esc(yearColor(label))}" aria-label="Esplora anno ${esc(yearLabel(label))}" aria-pressed="${label === year}"><title>${esc(yearLabel(label))} · ${esc(amount(yearGroups.get(label), false))}</title><rect x="20" y="${y}" width="150" height="108" rx="10"/>${long ? text(yearLabel(label), 34, y + 25, 18, 2) : `<text x="34" y="${y + 31}" class="map-year">${esc(label)}</text>`}<text x="34" y="${y + 69}" class="node-budget">${esc(amount(yearGroups.get(label)))}</text></g>`;
    }).join('');
    const ownerNodes = owners.map((label, index) => {
      const y = ownerY(index);
      return `<g class="map-node owner-node${label === owner ? ' chosen' : ''}${owner != null && label !== owner ? ' dimmed' : ''}" role="button" tabindex="0" data-owner-map-owner="${esc(label)}" style="--owner-color:${ownerColors.get(label) || OWNER_COLORS[0]}" aria-label="Esplora owner ${esc(label)}" aria-pressed="${label === owner}"><title>${esc(label)} · ${esc(amount(ownerGroups.get(label), false))}</title><rect x="220" y="${y}" width="210" height="74" rx="8"/>${text(label, 234, y + 23, 26, 2)}<text x="234" y="${y + 61}" class="node-sub">${esc(amount(ownerGroups.get(label)))}</text></g>`;
    }).join('');
    const domainNodes = domains.map((label, index) => {
      const y = domainY(index), records = focusedDomains.get(label) || [], available = records.length > 0;
      const interaction = available ? `role="button" tabindex="0" data-owner-map-domain="${esc(label)}" aria-pressed="${label === domain}"` : 'aria-disabled="true"';
      return `<g class="map-node domain-node${label === domain ? ' chosen' : ''}" ${interaction} style="--domain-color:${esc(domainColor(label))}" aria-label="${available ? 'Apri dominio' : 'Nessuna voce per questo owner nel dominio'} ${esc(label)}"><title>${esc(label)} · ${esc(amount(records, false))}</title><rect x="510" y="${y}" width="260" height="68" rx="8"/>${text(label, 524, y + 23, 34, 2)}<text x="524" y="${y + 57}" class="node-sub">${esc(amount(records))}</text></g>`;
    }).join('');
    const leaves = visible.map((row, index) => {
      const y = leafY(index);
      return `<g class="map-node leaf${options.selectedRemediation===rowKey(row)?' chosen':''}" role="button" tabindex="0" data-detail="${esc(rowKey(row))}" style="--domain-color:${esc(domainColor(domain))}" aria-label="Dettaglio ${esc(row.name)} · ${esc(ownerKey(row))} · ${esc(sourceRef(row))}"><title>${esc(row.name)} · ${esc(amount([row], false))}</title><rect x="860" y="${y}" width="440" height="108" rx="8"/>${text(row.name, 876, y + 41, 60, 2)}<text x="876" y="${y + 83}" class="node-sub">${esc(model.remediationBudget(row,entities,scope))}</text></g>`;
    }).join('');
    const selectedYearY = yearY(years.indexOf(year)) + 54;
    const yearEdges = owners.map((label, index) => edge('year-owner', year, label,
      `M170 ${selectedYearY} C194 ${selectedYearY},194 ${ownerY(index) + 37},212 ${ownerY(index) + 37}`,
      owner == null || label === owner, owner != null && label !== owner)).join('');
    const pairs = new Map();
    for (const row of yearRows) {
      const ownerLabel = ownerKey(row);
      if (!pairs.has(ownerLabel)) pairs.set(ownerLabel, new Set());
      pairs.get(ownerLabel).add(domainKey(row));
    }
    const ownerEdges = owners.map(ownerLabel => [...pairs.get(ownerLabel)].sort(compare).map(domainLabel => {
      const fromY = ownerY(ownerIndex.get(ownerLabel)) + 37;
      const toY = domainY(domainIndex.get(domainLabel)) + 34;
      const inFocus = (owner == null || ownerLabel === owner) && (domain == null || domainLabel === domain);
      return edge('owner-domain', ownerLabel, domainLabel, `M430 ${fromY} C466 ${fromY},466 ${toY},502 ${toY}`,
        (owner != null || domain != null) && inFocus, !inFocus);
    }).join('')).join('');
    const leafEdges = domain == null ? '' : visible.map((row, index) => {
      const fromY = domainY(domainIndex.get(domain)) + 34, toY = leafY(index) + 54;
      return edge('domain-remediation', domain, rowKey(row), `M770 ${fromY} C810 ${fromY},810 ${toY},852 ${toY}`, true);
    }).join('');
    const placeholder = domain == null ? `<g class="owner-map-placeholder"><rect x="860" y="75" width="440" height="154" rx="8"/>${text('Seleziona un dominio', 882, 113, 48, 1)}${text('Le remediation dell’anno e dell’owner scelti compariranno in questa colonna.', 882, 145, 58, 3, 'node-sub')}</g>` : '';
    const path = `<div class="map-path owner-map-path"><span class="year-pill" style="--year-color:${esc(yearColor(year))}">${esc(yearLabel(year))}</span>${icon('chevron', 14)}<button class="text-button" data-action="owner-map-all" aria-pressed="${owner == null}">Tutti gli owner</button>${owner == null ? '' : icon('chevron', 14) + '<strong>' + esc(owner) + '</strong>'}${domain == null ? '' : icon('chevron', 14) + '<strong>' + esc(domain) + '</strong>'}<span class="map-page-controls owner-map-controls"><button data-action="owner-map-prev" aria-label="Remediation precedenti" ${domain == null || page === 0 ? 'disabled' : ''}>←</button><span>${domain == null ? 'Apri un dominio' : `${page + 1} / ${pages} · ${focused.length} righe`}</span><button data-action="owner-map-next" aria-label="Remediation successive" ${domain == null || page === pages - 1 ? 'disabled' : ''}>→</button></span></div>`;
    const svg = `<svg id="owner-concept-map" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1320 ${height}" role="group" aria-label="Mappa anno, owner, dominio e remediation"><defs><marker id="owner-map-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 10 5 0 10z" fill="#a0b8bc"/></marker></defs><rect width="1320" height="${height}" fill="#fbfcfd"/><text x="20" y="32" class="map-col-label">01 / ANNO</text><text x="220" y="32" class="map-col-label">02 / OWNER · ${owners.length}</text><text x="510" y="32" class="map-col-label">03 / DOMINIO · ${domains.length}</text><text x="860" y="32" class="map-col-label">04 / REMEDIATION${domain == null ? '' : ' · ' + focused.length + ' RIGHE'}</text>${yearEdges}${ownerEdges}${leafEdges}${yearNodes}${ownerNodes}${domainNodes}${leaves}${placeholder}</svg>`;
    return {html: `<section class="panel map-panel owner-map-panel">${title}${explanation}${path}<div class="map-scroll">${svg}</div></section>`, year, owner, domain, page};
  }

  const api = {render};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.OwnerMap = api;
})(typeof globalThis !== 'undefined' ? globalThis : window);
