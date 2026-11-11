/* Data Visualization Tool — self-contained client. All views derive from the unchanged workbook rows. */
(() => {
  'use strict';
  const APP_VERSION = '1.4.9';
  const M = window.RemediationModel;
  const $ = (selector, root = document) => root.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = (name, size = 18) => {
    const paths = {grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
      owners:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-4a6 6 0 0 1 12 0v4m1-17a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 4v3"/>',table:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 10v10M3 15h18"/>',map:'<rect x="9" y="2" width="6" height="5" rx="1"/><rect x="2" y="17" width="6" height="5" rx="1"/><rect x="16" y="17" width="6" height="5" rx="1"/><path d="M12 7v5M5 17v-5h14v5"/>',
      globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',check:'<path d="m5 12 4 4L19 6"/>',shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
      upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5"/>',download:'<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',close:'<path d="m6 6 12 12M6 18 18 6"/>',
      present:'<rect x="3" y="3" width="18" height="13" rx="2"/><path d="M12 16v5m-4 0h8"/>',filter:'<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v1"/>',chevron:'<path d="m9 5 7 7-7 7"/>',file:'<path d="M14 2H5v20h14V7zM14 2v5h5M8 12h8m-8 4h8"/>',warning:'<path d="m12 3 10 18H2zM12 9v5m0 3v1"/>',reset:'<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/>',print:'<path d="M6 8V2h12v6M6 17H3V8h18v9h-3M6 14h12v8H6z"/>',link:'<path d="m10 14 4-4m-6 6-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m2 1 2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',menu:'<path d="M3 6h18M3 12h18M3 18h18"/>'};
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.grid}</svg>`;
  };
  // Original vector logo from the supplied KPMG template; no remote asset.
  const kpmgLogo = () => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 484832 194706" fill="currentColor" aria-hidden="true" focusable="false"><path d="M480938,148130L455744,148130L459917,131488L409445,131488L405289,148130L380916,148130L380916,144709C381293,142845 381618,140878 382079,138775C386526,120816 398311,103062 418715,103062C426771,103062 434792,106141 433698,117292L463732,117292C464912,112161 466896,103216 461234,95058C454821,86198 441942,82641 425214,82641C413328,82641 395933,84539 380916,94357L380916,3708L480938,3708ZM421914,172537C416372,173606 410745,174179 405101,174247C390683,174247 380643,167543 380438,151910L427027,151910ZM364275,90064L364275,110759C358044,119364 353522,129082 350951,139390C350195,142258 349663,145180 349360,148130L334669,148130L347223,88524L304943,88524L267110,148164L264339,148164L264339,3759L364326,3759ZM308449,148130L293398,148130L316163,112315ZM247731,88388L222709,88388L205606,148130L179027,148130C192538,143136 200765,133592 203314,119413C205400,108399 204408,101164 199893,95725C193154,87652 179642,88353 167653,88353L147796,88353L147796,3759L247697,3759ZM231740,148130L242258,110759L242635,148130ZM158981,133934L158981,133934C158007,133934 157032,134054 155920,134054C154466,134054 153320,134054 152243,134054L145846,134054L148805,123125L150207,117686L153628,104961C155116,104961 156570,104961 157972,104961L162915,104961C171467,104961 176718,105440 178668,108159C180156,110212 179967,113735 178206,119105C175196,128341 171364,133045 159084,133986M131291,93741L129717,98872L115419,146471L114854,148181L67683,148181L64006,140365L114683,88524L82187,88524L42507,131283L55351,88524L31270,88524L31270,3759L131188,3759ZM377119,-89L377119,97076C373861,99667 370856,102560 368140,105713L368140,-89L260525,-89L260525,88388L251614,88388L251614,-89L143965,-89L143965,88524L135071,88524L135071,-89L27456,-89L27456,100907L-47,192480L24120,192480L36247,151927L39667,151927L59696,192480L89028,192480L69513,151927L113623,151927L101377,192480L127785,192480L139860,152047L145641,152047L145641,151927L204408,151927L192761,192360L219374,192360L230662,151927L242635,151927L242960,192360L265280,192360L290935,151927L307713,151927L299059,192360L325227,192360L333779,151927L348933,151927C348334,164464 351533,175872 359845,183517C370004,192839 385603,194617 397131,194617C413526,194421 429850,192418 445807,188648L454872,151927L484786,151927L484786,-89Z"/></svg>`;
  const filterFields=['sheets','years','domains','owners','entities','nis2','priority','capexOpex','risk','impact','riskLevel','remediationType'];
  const defaultFilters = () => ({query:'',...Object.fromEntries(filterFields.map(field=>[field,data?filterOptions(field):null])),scope:'all',localBudget:'all',entityScope:'all'});
  let projects = [], activeProjectId = null, pendingFile = null;
  let data, standalone = Boolean(window.DVT_DATA), state = {view:'overview',filters:defaultFilters(),page:1,pageSize:15,sort:'source',direction:1,detail:null,mapYear:null,mapDomain:null,mapPage:0,ownerMapYear:null,ownerMapOwner:null,ownerMapDomain:null,ownerMapPage:0,presentation:false,busy:false,menu:false,filterOpen:['sheets','years'],topFilterOpen:null,projectDialog:null,projectName:''};
  if (window.DVT_STATE) { Object.assign(state, window.DVT_STATE); state.filters = {...defaultFilters(), ...window.DVT_STATE.filters}; }
  const views = [['overview','grid','Panoramica'],['map','map','Mappa Navigabile'],['owner-map','owners','Mappa Navigabile per Owner'],['risk-map','map','Mappa rischi e investimenti'],['risk-first-map','map','Mappa per Risk Type'],['remediation-map','map','Mappa remediation'],['table','table','Remediation'],['countries','globe','Country / legal entity']];
  const unique = field => [...new Set(data.rows.map(r => String(field==='owner'?(r.owner||'Non specificato'):(r[field]??''))))].sort((a,b) => a.localeCompare(b,'it',{numeric:true}));
  function filterOptions(field) {
    if(['capexOpex','risk','impact','riskLevel','remediationType'].includes(field))return [...new Set(data.rows.flatMap(row=>M.attributeValues(row,field)))].sort();
    if(field==='entities')return data.entities.map(entity=>entity.id);
    if(field==='priority'&&data.rows.some(row=>['n/a','na'].includes(String(row.priority||'').trim().toLowerCase())))return ['yes','no','na','missing'];
    if(field==='nis2'||field==='priority')return ['yes','no','missing'];
    return unique({sheets:'sheet',years:'year',domains:'domain',owners:'owner'}[field]);
  }
  const visibleFilterOptions=field=>filterOptions(field).filter(value=>!['capexOpex','risk','impact','riskLevel','remediationType'].includes(field)||String(value).trim().toLocaleLowerCase('it')!=='non specificato');
  function normalizeFilters() {
    for(const field of filterFields){
      const options=filterOptions(field),value=state.filters[field];
      const values=value==null||value==='all'?options:Array.isArray(value)?value:[String(value)];
      state.filters[field]=[...new Set(values.map(String))].filter(item=>options.includes(item));
    }
    state.filters.entityScope=state.filters.entities.length===data.entities.length?'all':'selected';
  }
  const entitySelection = () => state.filters.entityScope==='all'?null:state.filters.entities;
  const currentRows = () => M.filterRows(data.rows, state.filters);
  const money = M.money;
  const scopeTotals = rows => {
    const result = M.totals(rows,entitySelection());
    return {...result,displayGlobal:state.filters.scope === 'local' ? 0 : result.global,displayLocal:state.filters.scope === 'global' ? 0 : result.local};
  };
  const fieldName = field => ({years:'Anno',domains:'Dominio',owners:'Owner',entities:'Country / LE',sheets:'Perimetro dati',nis2:'Riferimento NIS2',priority:data?.rows.find(row=>row.prioritySourceHeader)?.prioritySourceHeader||'Priorità nel file',capexOpex:'Capex/Opex',risk:'Risk Type',impact:'Impact Type',riskLevel:'Risk Level',remediationType:'Type Of Remediation'})[field];
  const filterLabel = (field,value) => field==='nis2'||field==='priority'?({yes:'Sì',no:'No',na:'Non applicabile',missing:'Non specificato'}[value]):value||'Non specificato';
  const colorBy = (field,value,palette) => palette[Math.max(0,unique(field).indexOf(String(value??'')))%palette.length];
  const colorForYear = value => colorBy('year',value,['#7964cf','#d8942f','#ce668b','#4b91ba','#81994d','#c77a4d']);
  const colorForDomain = value => colorBy('domain',value,['#478ba8','#9375be','#4a9c83','#cd8d4c','#657ec0','#b56a8a','#899b43','#629caa','#af7f5f']);
  function syncSidebar() {
    const sidebar=$('.sidebar');if(!sidebar)return;
    for(const field of filterFields){
      const options=visibleFilterOptions(field),selected=state.filters[field].filter(value=>options.includes(value)),group=sidebar.querySelector(`details[data-group="${field}"]`);
      if(!group)continue;
      group.querySelector('.filter-count').textContent=selected.length===options.length?'Tutti':`${selected.length}/${options.length}`;
      for(const input of group.querySelectorAll('input[data-filter]'))input.checked=selected.includes(input.value);
      const master=group.querySelector('input[data-filter-all]');
      master.checked=options.length>0&&selected.length===options.length;master.indeterminate=selected.length>0&&selected.length<options.length;master.disabled=!options.length;
    }
    for(const button of sidebar.querySelectorAll('[data-view]')){
      const active=button.dataset.view===state.view;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
    }
    const projectSelect=sidebar.querySelector('#project-select');if(projectSelect){projectSelect.value=activeProjectId;projectSelect.disabled=state.busy;}
    const create=sidebar.querySelector('[data-action="new-project"]');if(create)create.disabled=state.busy;
    const scope=sidebar.querySelector('[data-sidebar-select="scope"]');if(scope)scope.value=state.filters.scope;
  }
  function checks(field, values, {label} = {}) {
    const selected=(state.filters[field]||[]).filter(value=>values.includes(value)),all=selected.length===values.length;
    return `<details class="filter-group" ${state.filterOpen.includes(field)?'open':''} data-group="${field}"><summary>${esc(label||fieldName(field))}<span class="filter-count">${all?'Tutti':`${selected.length}/${values.length}`}</span></summary><div class="filter-group-content"><label class="check-option master-option"><input type="checkbox" data-filter-all="${field}" aria-label="Seleziona tutti: ${esc(label||fieldName(field))}" ${all?'checked':''}><span>Seleziona tutti</span></label><div class="filter-options">${values.map(value=>`<label class="check-option"><input type="checkbox" data-filter="${field}" value="${esc(value)}" ${selected.includes(value)?'checked':''}><span>${esc(filterLabel(field,value))}</span></label>`).join('')}</div></div></details>`;
  }
  function sidebar() {
    return `<aside class="sidebar" data-source="${esc((data.project?.id||'')+':'+data.source.sha256)}"><a class="brand" aria-label="KPMG · Data Visualization Tool" href="#" data-action="home"><span class="brand-mark kpmg-brand" aria-hidden="true">${kpmgLogo()}</span><span class="brand-name">Data Visualization<span class="brand-line"> Tool</span><span class="brand-sub">STRUMENTO INTERNO</span></span></a>
      ${projectPicker()}
      <div class="sidebar-label">Viste</div><nav aria-label="Viste principali">${views.map(([id,i,label]) => `<button data-view="${id}" class="nav-item ${state.view === id ? 'active' : ''}" ${state.view === id ? 'aria-current="page"' : ''}>${icon(i)}<span>${label}</span></button>`).join('')}</nav>
      <div class="sidebar-divider"></div><div class="sidebar-label filter-label">Filtri <button title="Ripristina filtri" aria-label="Ripristina filtri" data-action="reset">${icon('reset',15)}</button></div>
      <div class="sidebar-filters"><label class="select-filter budget-sidebar-filter" for="sidebar-budget-scope">Budget da visualizzare<select id="sidebar-budget-scope" data-sidebar-select="scope">${[['all','Global + Local'],['global','Global'],['local','Local']].map(([value,label])=>`<option value="${value}">${label}</option>`).join('')}</select></label>${filterFields.map(field=>checks(field,visibleFilterOptions(field))).join('')}</div>
      <footer class="sidebar-footer">${icon('shield',16)}<span>Elaborazione locale<small>Nessun servizio AI o cloud</small><small class="app-version">Versione ${APP_VERSION}</small></span><span class="status-dot"></span></footer></aside>`;
  }
  function chips() {
    const chips=filterFields.filter(field=>state.filters[field].length!==filterOptions(field).length).map(field=>{
      const values=state.filters[field],label=values.length===0?'Nessuno':values.length===1?filterLabel(field,values[0]):`${values.length} di ${filterOptions(field).length}`;
      return `<button class="filter-chip" data-reset-group="${field}" title="Seleziona di nuovo tutti">${esc(fieldName(field))}: ${esc(label)} ${icon('close',12)}</button>`;
    });
    for(const [field,label] of [['localBudget','Budget local'],['scope','Livello']])if(state.filters[field]!=='all')chips.push(`<button class="filter-chip" data-clear="${field}">${label}: ${esc({positive:'Con budget',zero:'Budget zero',missing:'Non determinato',local:'Local',global:'Global'}[state.filters[field]])} ${icon('close',12)}</button>`);
    return `<div class="chip-row"><span class="chip-label">Vista corrente</span>${chips.length?chips.join(''):'<span class="all-data-chip">'+icon('check',12)+' Tutti i dati selezionati</span>'}<button class="text-button" data-action="reset">Ripristina filtri</button></div>`;
  }
  function toolbar() {
    return `<div class="toolbar"><label class="search-box">${icon('search')}<input id="search" placeholder="Cerca remediation, dominio o owner…" value="${esc(state.filters.query)}" aria-label="Cerca remediation"></label>
    <div class="scope-switch" role="group" aria-label="Livello budget da rappresentare" title="Scegli i budget da rappresentare nei grafici. Per selezionare le righe usa il filtro budget Local.">${[['all','Global + Local'],['global','Global'],['local','Local']].map(([v,l]) => `<button data-scope="${v}" class="${state.filters.scope===v?'selected':''}" aria-pressed="${state.filters.scope===v}">${l}</button>`).join('')}</div>
    <select class="budget-select" data-select="localBudget" aria-label="Filtra per budget locale">${[['all','Tutti i budget local'],['positive','Con budget local > 0'],['zero','Budget local = 0'],['missing','Budget local non determinato']].map(([v,l])=>`<option value="${v}" ${state.filters.localBudget===v?'selected':''}>${l}</option>`).join('')}</select></div>`;
  }
  function viewFilters() {
    const labels={sheets:'Perimetro',years:'Anno',domains:'Dominio',owners:'Owner',entities:'Country / LE',nis2:'NIS2',priority:data?.rows.find(row=>row.prioritySourceHeader)?.prioritySourceHeader||'Priorità',capexOpex:'Capex/Opex',risk:'Risk Type',impact:'Impact Type',riskLevel:'Risk Level',remediationType:'Type Of Remediation'};
    return `<section class="view-filters" data-source="${esc((data.project?.id||'')+':'+data.source.sha256)}" aria-label="Filtri delle viste">
      <div class="view-filters-heading"><span>${icon('filter',15)} Filtri</span><button class="text-button" data-action="reset">${icon('reset',13)} Ripristina filtri</button></div>
      <div class="view-filter-groups">${filterFields.map(field=>`<details class="view-filter" data-top-group="${field}" name="view-filters" ${state.topFilterOpen===field?'open':''}>
        <summary title="${esc(fieldName(field))}"><span class="view-filter-label">${esc(labels[field])}</span><span class="view-filter-count"></span>${icon('chevron',12)}</summary>
        <div class="view-filter-panel"><label class="view-filter-option view-filter-master"><input type="checkbox" data-top-filter-all="${field}" aria-label="Seleziona tutti: ${esc(fieldName(field))}"><span>Seleziona tutti</span></label>
          <div class="view-filter-options">${visibleFilterOptions(field).map(value=>`<label class="view-filter-option"><input type="checkbox" data-top-filter="${field}" value="${esc(value)}"><span>${esc(filterLabel(field,value))}</span></label>`).join('')}</div></div>
      </details>`).join('')}</div>
      <div class="view-filter-tools"><label class="budget-level-filter">Budget da visualizzare<select class="budget-select" data-top-select="scope">${[['all','Global + Local'],['global','Global'],['local','Local']].map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label>
        <div class="view-filters-presentation-tools"><label class="search-box">${icon('search',16)}<input id="presentation-search" placeholder="Cerca remediation, dominio o owner…" aria-label="Cerca remediation in presentazione"></label>
          <select class="budget-select" data-top-select="localBudget" aria-label="Budget locale in presentazione">${[['all','Tutti i budget local'],['positive','Con budget local > 0'],['zero','Budget local = 0'],['missing','Budget local non determinato']].map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select>
        </div></div></section>`;
  }
  function syncViewFilters() {
    const bar=$('.view-filters');if(!bar)return;
    for(const group of bar.querySelectorAll('[data-top-group]')){
      const field=group.dataset.topGroup,options=visibleFilterOptions(field),selected=state.filters[field].filter(value=>options.includes(value));
      const all=selected.length===options.length;
      group.querySelector('.view-filter-count').textContent=all?'Tutti':`${selected.length}/${options.length}`;
      group.classList.toggle('is-filtered',!all);
      for(const input of group.querySelectorAll('[data-top-filter]'))input.checked=selected.includes(input.value);
      const master=group.querySelector('[data-top-filter-all]');
      master.checked=options.length>0&&all;master.indeterminate=selected.length>0&&!all;master.disabled=!options.length;
    }
    $('#presentation-search',bar).value=state.filters.query;
    for(const select of bar.querySelectorAll('[data-top-select]'))select.value=state.filters[select.dataset.topSelect];
  }
  function closeViewFilters({focus=false}={}) {
    const group=$('.view-filters details[open]');
    state.topFilterOpen=null;
    if(group){group.open=false;if(focus)group.querySelector('summary').focus({preventScroll:true});}
    return Boolean(group);
  }
  const summaryMoney = (t, field, compact=false) => t.count && t[field === 'global' ? 'missingGlobal' : 'missingLocal'] === t.count ? 'Non stimato' : money(t[field],compact);
  const selectedMoney = (t, compact=false) => {
    const unknownG=t.count && t.missingGlobal===t.count, unknownL=t.count && t.missingLocal===t.count;
    if ((state.filters.scope==='global'&&unknownG)||(state.filters.scope==='local'&&unknownL)||(unknownG&&unknownL)) return 'Non stimato';
    return money(t.displayGlobal+t.displayLocal,compact);
  };
  const budgetMoney = (t, compact=false) => selectedMoney({...t,displayGlobal:state.filters.scope==='local'?0:t.global,displayLocal:state.filters.scope==='global'?0:t.local},compact);
  function kpis(rows) {
    const t=scopeTotals(rows), entities=entitySelection()===null?0:state.filters.entities.length;
    const cards=[['Budget selezionato',selectedMoney(t),`${state.filters.scope==='all'?'Global + Local':state.filters.scope==='global'?'Solo Global':'Solo Local'} · ${t.missingGlobal || t.missingLocal ? 'stime disponibili' : 'valori da Excel'}`,'accent',icon('arrow',18)],
      ['Budget Global',summaryMoney(t,'global'),(t.missingGlobal?'Stima incompleta · ':'')+(entities?'Budget di gruppo, non ripartito per country':'Investimento a livello di gruppo'),'',icon('globe',19)],
      ['Budget Local',summaryMoney(t,'local'),(t.missingLocal?'Stima incompleta · ':'')+(entities?`${entities} entità · attribuzione da formule`:'Complessivo, non somma dei costi unitari'),'',icon('map',19)],
      ['Voci di remediation',String(rows.length).padStart(2,'0'),`${new Set(rows.map(r=>r.domain)).size} domini · ${new Set(rows.map(r=>r.owner).filter(Boolean)).size} owner`,'',icon('table',19)]];
    return `<div class="kpi-grid">${cards.map(([l,v,sub,c,i])=>`<article class="kpi ${c}"><div class="kpi-label">${l}<span>${i}</span></div><div class="kpi-value">${v}</div><div class="kpi-note">${sub}</div></article>`).join('')}</div>
    ${entities ? `<div class="context-note">${icon('info',16)}<span>Il Global resta un budget di gruppo: non è una quota delle country selezionate. Il Local include solo attribuzioni ricostruibili.${t.missingLocal ? ` <strong>${t.missingLocal} righe senza attribuzione certa (${money(t.unresolvedLocal)} complessivi) restano visibili ma sono escluse dal Local selezionato.</strong>` : ''}</span></div>` : ''}`;
  }
  const panelTitle=(eyebrow,title,aside='')=>`<div class="panel-title"><div>${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}<h2>${title}</h2></div>${aside}</div>`;
  function budgetReconciliation(rows) {
    const b=M.budgetBreakdown(rows,data.entities,entitySelection());
    const value=(amount,missing=0,known=1)=>missing>0&&!known?'Non stimato':money(amount);
    const groupValue=(kind,component)=>{
      const suffix=component==='ot'?'Ot':'Base',count=component==='ot'?b.otCount:b.baseCount;
      return value(b[kind+suffix],b['missing'+(kind==='global'?'Global':'Local')+suffix],count-b['missing'+(kind==='global'?'Global':'Local')+suffix]);
    };
    const categoryCard=c=>`<article class="budget-category" data-local-category="${c.id}"><div class="budget-category-heading"><h3>${esc(c.label)}</h3><span>${c.entityCount} entità</span></div>
      <strong class="budget-category-total" data-budget-part="total">${value(c.total,c.missing,c.known)}</strong>
      <dl><div><dt>Base Remediations</dt><dd data-budget-part="base">${value(c.base,c.baseMissing,c.baseKnown)}</dd></div><div><dt>Delta OT</dt><dd data-budget-part="ot">${value(c.ot,c.otMissing,c.otKnown)}</dd></div></dl>
      ${c.missing?`<p class="budget-partial">${c.missing} ${c.missing===1?'stima mancante':'stime mancanti'} · importi disponibili</p>`:''}</article>`;
    const residual=b.unallocated!==0?`<div class="budget-residual" role="note">${icon('info',16)}<span><strong>Local da attribuire: ${money(b.unallocated)}.</strong> Incluso nel totale Local del gruppo, separato dalle categorie perché le legal entity non sono confermate.</span></div>`:
      entitySelection()!==null&&b.unresolvedSource?`<div class="budget-residual" role="note">${icon('info',16)}<span>${money(b.unresolvedSource)} Local di gruppo senza attribuzione certa: nessuna quota viene assegnata alle entità selezionate.</span></div>`:'';
    return `<section class="panel budget-reconciliation">${panelTitle('','Composizione del budget','<span class="subtle-label">Base + delta OT</span>')}<p class="budget-reconciliation-intro">Importi complessivi nel perimetro dei filtri. Il delta OT viene aggiunto una sola volta.</p>
      ${state.filters.scope!=='local'?`<div class="budget-global-summary"><div><span>Global base</span><strong data-global-budget="base">${groupValue('global','base')}</strong></div><span class="budget-sum-sign" aria-hidden="true">+</span><div><span>Delta Global OT</span><strong data-global-budget="ot">${groupValue('global','ot')}</strong></div><span class="budget-sum-sign" aria-hidden="true">=</span><div><span>Global complessivo</span><strong data-global-budget="total">${value(b.global,b.missingGlobal,b.rowCount-b.missingGlobal)}</strong></div></div>`:''}
      ${state.filters.scope!=='global'?`${!b.classificationAvailable?'<p class="budget-classification-note">Il file non dichiara le categorie delle legal entity: gli importi restano disponibili senza dedurre una classificazione.</p>':''}<div class="budget-category-grid">${b.categories.filter(c=>c.entityCount>0).map(categoryCard).join('')}</div>${residual}
        <div class="budget-local-summary"><span>Local base <strong data-budget-local="base">${groupValue('local','base')}</strong></span><span aria-hidden="true">+</span><span>Delta Local OT <strong data-budget-local="ot">${groupValue('local','ot')}</strong></span><span aria-hidden="true">=</span><span>Local complessivo <strong data-budget-local="total">${value(b.localTotal,b.missingLocal,b.rowCount-b.missingLocal)}</strong></span></div>`:''}
      <details class="budget-method"><summary>Come sono calcolati i budget</summary><p>Global base e delta Global OT sono importi di gruppo. Il Local segue le formule delle singole remediation e le X di LE_List: i costi unitari vengono attribuiti soltanto alle legal entity del relativo gruppo. Complete + OT comprende la base Complete e il solo delta OT; Complete senza OT e Business rimangono separati.</p><p>I gruppi specifici delle remediation restano distinti dai gruppi organizzativi. Un costo della colonna Complete può essere applicato a una legal entity Business, come previsto dal file. Le righe duplicate restano interventi distinti. Le attribuzioni geografiche non confermate rimangono sospese. Stime mancanti, zeri e importi da attribuire rimangono distinguibili.</p></details></section>`;
  }
  function budgetLegend(chart) {
    return `<span class="budget-legend" role="group" aria-label="Budget ${chart==='domain'?'per dominio':'per anno'} da visualizzare">${[['global','Global'],['local','Local']].map(([value,label])=>{
      const selected=state.filters.scope==='all'||state.filters.scope===value,only=state.filters.scope===value;
      const title=only?`${label} selezionato. Attiva anche ${value==='global'?'Local':'Global'} per cambiare la selezione.`:`${selected?'Nascondi':'Mostra anche'} il budget ${label}`;
      return `<button type="button" id="budget-legend-${chart}-${value}" data-budget-component="${value}" aria-pressed="${selected}" aria-disabled="${only}" title="${title}"><i class="legend-dot ${value}"></i>${label}</button>`;
    }).join('')}</span>`;
  }
  function overview(rows) {
    const totalOf=x=>(state.filters.scope==='local'?0:x.global)+(state.filters.scope==='global'?0:x.local);
    const annual=M.aggregate(rows,'year',entitySelection()).sort((a,b)=>a.label.localeCompare(b.label));
    const domains=M.aggregate(rows,'domain',entitySelection()).sort((a,b)=>totalOf(b)-totalOf(a));
    const owners=M.aggregate(rows,'owner',entitySelection()).sort((a,b)=>totalOf(b)-totalOf(a));
    const max=Math.max(...annual.map(totalOf),1);
    return `${budgetReconciliation(rows)}<div class="overview-grid"><section class="panel annual-panel">${panelTitle('','Budget per anno','<span class="subtle-label">EUR · valori complessivi</span>')}<div class="legend">${budgetLegend('year')}<small>Clicca un anno per esplorarlo</small></div>
      <div class="annual-chart">${annual.map(a=>{const g=state.filters.scope==='local'?0:a.global,l=state.filters.scope==='global'?0:a.local;return `<button class="year-column" data-year="${a.label}" aria-label="Filtra anno ${a.label}, ${esc(budgetMoney(a))}"><span class="column-total">${budgetMoney(a,true)}</span><span class="bar-track"><span class="stacked-bar" style="height:${Math.max(2,(g+l)/max*100)}%"><span class="bar-local" style="flex:${l}">${l>max*.1?money(l,true):''}</span><span class="bar-global" style="flex:${g}">${g>max*.1?money(g,true):''}</span></span></span><strong class="year-chart-label" style="--year-color:${colorForYear(a.label)}">${esc(a.label)}</strong><small>${a.count} righe</small></button>`}).join('')}</div>
      <div class="chart-footnote">Un’unica annualità per riga, come nel file di origine.</div></section>
      <section class="panel owner-panel">${panelTitle('','Budget per owner',icon('globe',19))}<div class="owner-list">${owners.map((o,i)=>`<button class="owner-row" data-owner="${esc(o.label)}"><span class="owner-avatar owner-${i%4}">${esc(o.label.slice(0,2))}</span><span class="owner-info"><span class="owner-name">${esc(o.label)}</span><span class="mini-bar"><i style="width:${Math.max(1,totalOf(o)/Math.max(...owners.map(totalOf),1)*100)}%"></i></span><small>${o.count} righe di remediation</small></span><strong>${budgetMoney(o,true)}</strong>${icon('chevron',14)}</button>`).join('')}</div><p class="small-note">Owner riportati dal file; nessuna attribuzione automatica dei fornitori.</p></section>
      <section class="panel domain-panel">${panelTitle('','Budget per dominio',`<span class="subtle-label">${domains.length} domini</span>`)}<div class="domain-chart">${domains.map(d=>`<button class="domain-row" data-domain="${esc(d.label)}"><span class="domain-name" style="--domain-color:${colorForDomain(d.label)}"><i class="domain-dot"></i>${esc(d.label)}</span><span class="domain-track"><span class="domain-stack" style="width:${Math.max(1,totalOf(d)/Math.max(...domains.map(totalOf),1)*100)}%"><i class="global" style="flex:${state.filters.scope==='local'?0:d.global}"></i><i class="local" style="flex:${state.filters.scope==='global'?0:d.local}"></i></span></span><strong>${budgetMoney(d,true)}</strong><span class="row-count">${d.count}</span></button>`).join('')}</div><div class="chart-footnote domain-chart-footer"><span>Seleziona un dominio per aprire il dettaglio delle remediation.</span>${budgetLegend('domain')}</div></section>
    </div>`;
  }
  const sourceRef=row=>`${row.sourceSheet||row.sheet} · riga ${row.excelRow}`;
  function sortedRows(rows) {
    if(state.sort==='source') return rows;
    return [...rows].sort((a,b)=> {
      const v=state.sort==='local'?M.localAmount(a,entitySelection()):a[state.sort];
      const w=state.sort==='local'?M.localAmount(b,entitySelection()):b[state.sort];
      if(v==null) return w==null?0:1;if(w==null)return -1;
      return state.direction*(typeof v==='number'?v-w:String(v).localeCompare(String(w),'it',{numeric:true}));
    });
  }
  function tableView(rows) {
    const sorted=sortedRows(rows),pages=Math.max(1,Math.ceil(rows.length/state.pageSize));state.page=Math.min(state.page,pages);
    return `<section class="remediation-explorer">${panelTitle('','Remediation selezionate',`<span class="subtle-label">${rows.length} attività · clicca una scheda</span>`)}<div class="card-toolbar"><span><i class="legend-dot global"></i> Global di gruppo <i class="legend-dot local"></i> Local ${entitySelection()===null?'complessivo':'selezionato'}</span><label>Ordina per <select id="remediation-sort">${[['source','Ordine del file'],['name','Nome'],['year','Anno'],['owner','Owner'],['globalBudget','Budget Global'],['local','Budget Local']].map(([value,label])=>`<option value="${value}" ${state.sort===value?'selected':''}>${label}</option>`).join('')}</select></label><button class="icon-button" data-action="sort-direction" aria-label="Inverti ordinamento">${state.direction===1?'↑':'↓'}</button></div><div class="remediation-grid">${sorted.slice((state.page-1)*state.pageSize,state.page*state.pageSize).map(row=>`<button class="remediation-card" data-detail="${esc(row.key)}" style="--domain-color:${colorForDomain(row.domain)}" aria-label="Dettaglio ${esc(row.name)}"><span class="remediation-card-top"><span class="source-id">${esc(row.id||`Riga ${row.excelRow}`)}</span><span class="year-pill" style="--year-color:${colorForYear(row.year)}">${esc(row.year||'Anno non specificato')}</span></span><span class="remediation-domain"><i></i>${esc(row.domain||'Dominio non specificato')}</span><strong class="remediation-title">${esc(row.name)}</strong><span class="remediation-owner">${icon('link',13)}${esc(row.owner||'Owner non specificato')}</span><span class="remediation-budget-pair"><span class="budget-global"><small>Global</small><strong>${money(row.globalBudget)}</strong></span><span class="budget-local"><small>Local</small><strong>${money(M.localAmount(row,entitySelection()))}</strong></span></span>${row.allocationStatus!=='mapped'?'<span class="inline-warning">'+icon('info',12)+' Attribuzione locale da confermare</span>':''}<span class="remediation-card-bottom"><span>${esc(sourceRef(row))}</span><span>Apri dettaglio ${icon('arrow',13)}</span></span></button>`).join('')}</div><div class="table-footer"><span>Attività ${(state.page-1)*state.pageSize+1}–${Math.min(state.page*state.pageSize,rows.length)} di ${rows.length}</span><label>Per pagina <select id="page-size">${[15,30,62,100].map(n=>`<option ${state.pageSize===n?'selected':''}>${n}</option>`).join('')}</select></label><div class="pagination"><button data-action="prev-page" ${state.page===1?'disabled':''}>←</button><span>${state.page} / ${pages}</span><button data-action="next-page" ${state.page===pages?'disabled':''}>→</button></div></div></section>`;
  }
  function badgeStatus(value) {
    const v=String(value||'').trim().toLowerCase();if(['n/a','na'].includes(v))return '<span class="muted">Non applicabile</span>';return ['yes','nis 2','nis2'].includes(v)?'<span class="status-badge yes">Sì</span>':v==='no'?'<span class="status-badge no">No</span>':'<span class="muted">—</span>';
  }
  function wrapSvg(text,max=29,maxLines=3) {
    const words=String(text).split(/\s+/),lines=[''];
    for(const word of words){if((lines.at(-1)+' '+word).trim().length>max&&lines.at(-1))lines.push(word);else lines[lines.length-1]=(lines.at(-1)+' '+word).trim();}
    if(lines.length>maxLines){lines.length=maxLines;lines[maxLines-1]=lines.at(-1).slice(0,max-1)+'…';}return lines;
  }
  function svgText(text,x,y,max=29,maxLines=3,cls='node-title') {
    return `<text class="${cls}" x="${x}" y="${y}">${wrapSvg(text,max,maxLines).map((line,i)=>`<tspan x="${x}" dy="${i?17:0}">${esc(line)}</tspan>`).join('')}</text>`;
  }
  function mapView(rows) {
    const years=[...new Set(rows.map(r=>r.year))].sort();if(!years.includes(state.mapYear))state.mapYear=years[0];
    const yearRows=rows.filter(r=>r.year===state.mapYear),domains=M.aggregate(yearRows,'domain',entitySelection());
    if(!domains.some(d=>d.label===state.mapDomain))state.mapDomain=domains[0]?.label;
    const focused=yearRows.filter(r=>r.domain===state.mapDomain),pages=Math.max(1,Math.ceil(focused.length/6));state.mapPage=Math.min(state.mapPage,pages-1);
    const visible=focused.slice(state.mapPage*6,state.mapPage*6+6), height=Math.max(590,domains.length*76+82,visible.length*105+85);
    const yearNodes=years.map((y,i)=>{const yy=105+i*145,t=scopeTotals(rows.filter(r=>r.year===y));return `<g class="map-node year-node ${y===state.mapYear?'chosen':''}" role="button" tabindex="0" data-map-year="${y}" style="--year-color:${colorForYear(y)}" aria-label="Esplora anno ${y}"><rect x="20" y="${yy}" width="172" height="102" rx="10"/><text x="38" y="${yy+31}" class="map-year">${y}</text><text x="38" y="${yy+57}" class="node-budget">${esc(selectedMoney(t,true))}</text></g>`}).join('');
    const domainNodes=domains.map((d,i)=>{const yy=70+i*76,total=(state.filters.scope==='local'?0:d.global)+(state.filters.scope==='global'?0:d.local);return `<g class="map-node domain-node ${d.label===state.mapDomain?'chosen':''}" role="button" tabindex="0" data-map-domain="${esc(d.label)}" style="--domain-color:${colorForDomain(d.label)}" aria-label="Esplora ${esc(d.label)}"><rect x="290" y="${yy}" width="250" height="65" rx="8"/>${svgText(d.label,306,yy+23,31,2)}<text x="306" y="${yy+55}" class="node-sub">${esc(budgetMoney(d,true))}</text></g>`}).join('');
    const detailNodes=visible.map((r,i)=>{const yy=70+i*105;return `<g class="map-node leaf${state.selectedRemediation===r.key?' chosen':''}" style="--domain-color:${colorForDomain(r.domain)}" role="button" tabindex="0" data-detail="${esc(r.key)}" aria-label="Dettaglio ${esc(r.name)}"><rect x="640" y="${yy}" width="330" height="94" rx="8"/>${svgText(r.name,656,yy+39,39,2)}<text x="656" y="${yy+82}" class="node-sub">${esc(M.remediationBudget(r,entitySelection(),state.filters.scope))}</text></g>`}).join('');
    const chosenY=105+years.indexOf(state.mapYear)*145+51,chosenD=70+domains.findIndex(d=>d.label===state.mapDomain)*76+32;
    const edges=domains.map((d,i)=>`<path class="map-edge ${d.label===state.mapDomain?'highlight':''}" d="M192 ${chosenY} C240 ${chosenY},240 ${102+i*76},282 ${102+i*76}"/>`).join('')+visible.map((r,i)=>`<path class="map-edge highlight" d="M540 ${chosenD} C590 ${chosenD},590 ${117+i*105},632 ${117+i*105}"/>`).join('');
    return `<section class="panel map-panel">${panelTitle('','Mappa delle remediation','<button class="button small" data-action="png">'+icon('download',15)+' Salva PNG</button>')}<div class="map-explanation">Seleziona un anno, poi un dominio. Doppio click sulla remediation per i dettagli. Le frecce raggruppano le remediation; non indicano dipendenze tra progetti.</div><div class="map-path"><span class="year-pill" style="--year-color:${colorForYear(state.mapYear)}">${state.mapYear}</span>${icon('chevron',14)}<strong>${esc(state.mapDomain)}</strong><span class="map-page-controls"><button data-action="map-prev" ${state.mapPage===0?'disabled':''}>←</button>${state.mapPage+1}/${pages}<button data-action="map-next" ${state.mapPage===pages-1?'disabled':''}>→</button></span></div><div class="map-scroll"><svg id="concept-map" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 995 ${height}" role="img" aria-label="Mappa anno, dominio e remediation"><defs><marker id="map-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 10 5 0 10z" fill="#a0b8bc"/></marker></defs><rect width="995" height="${height}" fill="#fbfcfd"/><text x="20" y="32" class="map-col-label">01 / ANNO</text><text x="290" y="32" class="map-col-label">02 / DOMINIO</text><text x="640" y="32" class="map-col-label">03 / REMEDIATION · ${focused.length} RIGHE</text>${edges}${yearNodes}${domainNodes}${detailNodes}</svg></div></section>`;
  }

  let riskPath=Array.isArray(window.DVT_STATE?.riskPath)?window.DVT_STATE.riskPath:[];
  let riskFirstPath=Array.isArray(window.DVT_STATE?.riskFirstPath)?window.DVT_STATE.riskFirstPath:[];
  let remediationPath=Array.isArray(window.DVT_STATE?.remediationPath)?window.DVT_STATE.remediationPath:[];
  const activeRiskPath=()=>state.view==='remediation-map'?remediationPath:state.view==='risk-first-map'?riskFirstPath:riskPath;
  function selectRiskStep(step,value) {
    const path=activeRiskPath().slice(0,step);path[step]=value;
    if(state.view==='remediation-map')remediationPath=path;else if(state.view==='risk-first-map')riskFirstPath=path;else riskPath=path;
  }
  function riskMapView(rows, riskFirst=false, remediationFirst=false) {
    let path=remediationFirst?remediationPath:riskFirst?riskFirstPath:riskPath;
    const rememberPath=()=>{if(remediationFirst)remediationPath=path;else if(riskFirst)riskFirstPath=path;else riskPath=path;};
    const remediationStep=remediationFirst?1:riskFirst?2:3;
    const title=remediationFirst?'Mappa remediation':riskFirst?'Rischi, remediation e investimenti':'Rischi e investimenti';
    const originalCount=rows.length;
    rows=M.investmentRows(rows);
    const excluded=originalCount-rows.length;
    const notice=excluded?`<div class="map-explanation" role="status">${excluded} righe escluse da questa mappa: servono Capex oppure Opex e un rischio compilato. Comprendono eventuali righe OT senza questi attributi. Le righe restano disponibili nelle altre viste e nei totali.</div>`:'';
    if(!rows.length){path=[];rememberPath();return `<section class="panel map-panel investment-map"><div class="panel-title"><h2>${title}</h2></div>${notice}<div class="empty-state"><h2>Nessuna remediation con gli attributi richiesti</h2><p>Compila CAPEX/OPEX e Risk Type nel foglio All Remediations (oppure i campi del tracciato precedente), poi aggiorna l’Excel del progetto.</p></div></section>`;}
    const fields=remediationFirst?['year','key','risk','impact','capexOpex']:riskFirst?['year','risk','key','impact','capexOpex']:['year','capexOpex','domain','key','risk','impact'];
    const labels=remediationFirst?['Anno','Remediation','Risk Type','Impact Type','Capex/Opex']:riskFirst?['Anno','Risk Type','Remediation','Impact Type','Capex/Opex']:['Anno','Capex/Opex','Dominio','Remediation','Risk Type','Impact Type'];
    const xs=remediationFirst?[20,220,740,1030,1310]:riskFirst?[20,220,510,1030,1310]:[20,220,510,860,1380,1660], widths=remediationFirst?[150,440,210,210,210]:riskFirst?[150,210,440,210,210]:[150,210,260,440,210,210];
    const heights=remediationFirst?[108,108,74,74,74]:riskFirst?[108,74,108,74,74]:[108,74,68,108,74,74];
    const amount=(records,compact=false)=>{
      const total=M.totals(records,entitySelection());
      const unknownGlobal=total.missingGlobal===total.count,unknownLocal=total.missingLocal===total.count;
      if((state.filters.scope==='global'&&unknownGlobal)||(state.filters.scope==='local'&&unknownLocal)||(unknownGlobal&&unknownLocal))return 'Non stimato';
      return money((state.filters.scope==='local'?0:total.global)+(state.filters.scope==='global'?0:total.local),compact);
    };
    const columns=[];let focused=rows;
    for(let step=0;step<fields.length;step++){
      const groups=['risk','impact'].includes(fields[step])?M.attributeGroups(focused,fields[step],entitySelection()):M.aggregate(focused,fields[step],entitySelection());
      const chosen=groups.find(group=>group.label===path[step]);
      if(!chosen&&(riskFirst||step<4))path=path.slice(0,step);
      columns.push(groups);
      // Risk and Impact are independent attributes of the selected remediation.
      if(!riskFirst&&step>=4)continue;
      if(!chosen)break;
      focused=chosen.rows;
    }
    rememberPath();
    const text=(label,x,y,width,className='node-title')=>{
      const words=String(label).split(/\s+/),lines=[''];
      for(const word of words){if((lines.at(-1)+' '+word).trim().length>width&&lines.at(-1))lines.push(word);else lines[lines.length-1]=(lines.at(-1)+' '+word).trim();}
      return `<text x="${x}" y="${y}" class="${className}">${lines.slice(0,2).map((line,i)=>`<tspan x="${x}" dy="${i?17:0}">${esc(line.length>width?line.slice(0,width-1)+'…':line)}${i===1&&lines.length>2?'…':''}</tspan>`).join('')}</text>`;
    };
    const selectedRemediation=columns[remediationStep]?.findIndex(group=>group.label===path[remediationStep])??0;
    const impactLane=Math.max(85+(columns[4]?.length||0)*128+24,85+Math.max(0,selectedRemediation)*128+heights[3]+32,85+(columns[5]?.length||0)*128+24);
    const height=Math.max(610,...columns.map(groups=>85+groups.length*128),columns[5]?impactLane+40:0);
    let edges='',nodes='';
    columns.forEach((groups,step)=>{
      nodes+=`<text x="${xs[step]}" y="32" class="map-col-label">${String(step+1).padStart(2,'0')} / ${labels[step].toLocaleUpperCase('it')}</text>`;
      groups.forEach((group,index)=>{
        const x=xs[step],y=85+index*128,h=heights[step],selected=path[step]===group.label;
        const row=group.rows[0],label=step===remediationStep?row.name:group.label;
        const color=step===0?colorForYear(group.label):fields[step]==='domain'||step===remediationStep?colorForDomain(row.domain):fields[step]==='capexOpex'?(group.label==='Capex'?'#4b72bf':'#1b9b89'):'#58738c';
        const level=fields[step]==='impact'&&row.impactLevels?row.impactLevels[group.label]:M.attributeValues(row,'riskLevel')[0];
        const impactColor={High:'#c64545',Medium:'#b8840a',Low:'#32835c'}[level]||'#8a9da7';
        if(step>0){const parentStep=!riskFirst&&step===5?3:step-1;const parent=columns[parentStep].findIndex(g=>g.label===path[parentStep]);if(parent>=0){const start=xs[parentStep]+widths[parentStep],py=85+parent*128+heights[parentStep]/2;const edgePath=!riskFirst&&step===5?`M${start} ${py} C${start+24} ${py},${start+34} ${py},${start+34} ${py+24} C${start+34} ${impactLane-24},${start+34} ${impactLane},${start+58} ${impactLane} C${x-54} ${impactLane},${x-30} ${impactLane},${x-30} ${impactLane-24} C${x-30} ${y+h/2+24},${x-30} ${y+h/2},${x-8} ${y+h/2}`:`M${start} ${py} C${start+30} ${py},${x-30} ${y+h/2},${x-8} ${y+h/2}`;edges+=`<path class="map-edge highlight" data-risk-edge="${riskFirst?(step===3?'remediation-impact':'group'):step===5?'remediation-impact':step===4?'remediation-risk':'group'}" d="${edgePath}" style="marker-end:url(#risk-arrow)"/>`;}}
        const classes=step===0?'year-node':step===remediationStep?'leaf':fields[step]==='impact'?'impact-node':fields[step]==='domain'?'domain-node':'owner-node';
        nodes+=`<g class="map-node ${classes}${selected?' chosen':''}" role="button" tabindex="0" data-risk-step="${step}" data-risk-value="${esc(group.label)}" ${step===remediationStep?`data-risk-detail="${esc(row.key)}"`:''} aria-label="${esc(label)}" aria-pressed="${selected}" style="--year-color:${color};--domain-color:${color};--owner-color:${color};--impact-color:${impactColor}"><title>${esc(label)}${fields[step]==='impact'?'':` · ${esc(amount(group.rows))}`}</title><rect x="${x}" y="${y}" width="${widths[step]}" height="${h}" rx="${step===0?10:8}"/>${step===0?`<text x="${x+14}" y="${y+31}" class="map-year">${esc(label)}</text><text x="${x+14}" y="${y+69}" class="node-budget">${esc(amount(group.rows,true))}</text>`:step===remediationStep?`${text(label,x+16,y+41,60)}<text x="${x+16}" y="${y+83}" class="node-sub">${esc(M.remediationBudget(row,entitySelection(),state.filters.scope))}</text>`:`${text(label,x+14,y+23,step===2?34:26)}${fields[step]==='impact'?'':`<text x="${x+14}" y="${y+h-12}" class="node-sub">${esc(amount(group.rows,true))}</text>`}${fields[step]==='impact'&&row.impactLevels?`<text x="${x+14}" y="${y+44}" class="node-sub">${esc(level||'Non specificato')}</text>`:''}`}</g>`;
      });
    });
    const width=Math.max(780,xs[columns.length-1]+widths[columns.length-1]+20);
    return `<section class="panel map-panel investment-map"><div class="panel-title"><h2>${title}</h2></div><div class="map-explanation">${remediationFirst?'Seleziona anno, remediation, Risk Type e Impact Type per visualizzare Capex/Opex.':riskFirst?'Seleziona anno, Risk Type, remediation e Impact Type per visualizzare Capex/Opex.':'Seleziona anno, Capex/Opex e dominio, poi una remediation per vedere il rischio associato e il suo impatto.'} Click singolo per proseguire; doppio click sulla remediation per aprire il dettaglio. Risk Type e Impact Type sono attributi della remediation: le frecce non indicano coppie rischio–impatto. I budget dei gruppi di attributi possono sovrapporsi e non si sommano. Livelli: High rosso, Medium giallo, Low verde. Se presenti, i colori degli impatti seguono il livello del singolo impatto, distinto dal Risk Level.</div>${notice}<div class="map-scroll"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" style="min-width:${width}px;width:${width}px" role="group" aria-label="${riskFirst?title:'Mappa rischi e investimenti'}"><defs><marker id="risk-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0 10 5 0 10z" fill="#a0b8bc"/></marker></defs><rect width="${width}" height="${height}" fill="#fbfcfd"/>${edges}${nodes}</svg></div></section>`;
  }

  function ownerMapView(rows) {
    const result=window.OwnerMap.render({data,rows,year:state.ownerMapYear,owner:state.ownerMapOwner,
      domain:state.ownerMapDomain,page:state.ownerMapPage,esc,icon,money,model:M,colorForYear,colorForDomain,
      scope:state.filters.scope,entitySelection:entitySelection(),selectedRemediation:state.selectedRemediation});
    state.ownerMapYear=result.year;state.ownerMapOwner=result.owner;
    state.ownerMapDomain=result.domain;state.ownerMapPage=result.page;
    return result.html;
  }
  function countriesView() {
    return window.CountryInvestments.render({data,filters:state.filters,rows:currentRows(),esc,icon,money,model:M,colorForYear,colorForDomain});
  }
  function detailPanel() {
    const r=data.rows.find(r=>r.key===state.detail);if(!r)return '';
    const issues=data.issues.filter(i=>i.rowKeys?.includes(r.key));
    const riskLevels=M.attributeValues(r,'riskLevel').map(level=>{
      const severity={high:'high',alto:'high',medium:'medium',medio:'medium',low:'low',basso:'low'}[level.trim().toLowerCase()];
      return `<span class="risk-level${severity?' risk-level-'+severity:''}">${esc(level)}</span>`;
    }).join(', ');

    const text=(label,value)=>`<section class="detail-section"><h3>${label}</h3><p>${esc(value||'Non specificato nel file')}</p></section>`;
    return `<div class="drawer-overlay" data-action="close-detail"></div><aside class="detail-drawer" role="dialog" aria-modal="true" aria-label="Dettaglio remediation" tabindex="-1"><div class="drawer-top"><span class="eyebrow">Dettaglio remediation</span><button id="close-detail" class="icon-button" data-action="close-detail" aria-label="Chiudi dettaglio">${icon('close')}</button></div><span class="source-tag">${esc(sourceRef(r))}${r.id?' · '+esc(r.id):' · ID originale assente'}</span><h2>${esc(r.name)}</h2><p class="detail-domain">${esc(r.domain)}</p><div class="detail-tags"><span class="year-pill" style="--year-color:${colorForYear(r.year)}">${r.year||'Anno non specificato'}</span><span class="owner-badge">${esc(r.owner||'Owner non specificato')}</span><span>NIS2 ${badgeStatus(r.nis2)}</span><span>Priorità ${badgeStatus(r.priority)}</span></div>
    <div class="detail-budgets"><div><small>Budget Global</small><strong>${money(r.globalBudget)}</strong></div><div><small>${entitySelection()!==null?'Local · entità selezionate':'Local complessivo'}</small><strong>${money(M.localAmount(r,entitySelection()))}</strong></div><div><small>Complete · unitario</small><strong>${money(r.localComplete)}</strong></div><div><small>Business Oriented · unitario</small><strong>${money(r.localBusiness)}</strong></div></div>
    ${text('Capex/Opex',r.capexOpex)}${text('Risk Type',M.attributeValues(r,'risk').join(', '))}${r.impactLevels?`<section class="detail-section"><h3>Impatti</h3><dl>${Object.entries(r.impactLevels).map(([type,level])=>`<div><dt>${esc(type)} Impact</dt><dd><span class="risk-level risk-level-${['High','Medium','Low'].includes(level)?level.toLowerCase():'unknown'}">${esc(level||'Non specificato')}</span></dd></div>`).join('')}</dl></section>`:text('Impact Type',M.attributeValues(r,'impact').join(', '))}<section class="detail-section"><h3>Risk Level</h3><p>${riskLevels||'Non specificato nel file'}</p></section>${text('Type Of Remediation',r.remediationType)}${String(r.capexOpexNote||'').trim()&&String(r.capexOpexNote).trim()!=='-'?`<section class="detail-section capex-note-section"><h3>Note Capex/Opex</h3><p>${esc(r.capexOpexNote)}</p></section>`:''}${r.prioritySourceHeader?text(r.prioritySourceHeader,r.priority):''}${r.sourceBudgetMarkers?text('Stime da definire nel file',Object.entries(r.sourceBudgetMarkers).map(([field,value])=>({globalBudget:'Budget Global',localComplete:'Budget Local Complete',localBusiness:'Budget Local Business',localTotal:'Budget Local complessivo'}[field]||'Budget')+': '+value).join(', ')):''}${text('Attività Global · testo originale',r.globalDescription)}${text('Attività Local · testo originale',r.localDescription)}${text('Applicable Countries · da verificare',r.applicableCountries)}${r.existingCoverage?text('Who has this? · testo originale',r.existingCoverage):''}
    <section class="detail-section formula-section"><h3>Tracciabilità del budget Local</h3><code>${esc(r.localFormula||'Formula non presente nel file')}</code><p>${esc(r.allocationNote||'Attribuzione da formule e LE_List.')}</p><small>Local complessivo originale: ${money(r.localTotal)}</small></section>
    ${issues.length?`<section class="detail-section detail-alert"><h3>${icon('info',16)} Note su questa riga</h3>${issues.map(i=>`<p>${esc(i.message)}</p>`).join('')}</section>`:''}
    ${r.allocations?.length?`<section class="detail-section"><h3>Attribuzione del budget locale</h3><p class="small-note">Derivata da formula e LE_List; non è una conferma dell’applicabilità.</p><div class="allocation-list">${r.allocations.map(a=>`<div><span class="allocation-country">${window.CountryInvestments.countryFlags(a.entityId,esc,icon)}<span>${esc(a.entityId)}</span></span><strong>${money(a.amount)}</strong></div>`).join('')}</div></section>`:''}</aside>`;
  }
  function emptyView() {return `<section class="panel empty-state">${icon('search',34)}<h2>Nessuna remediation corrisponde ai filtri</h2><p>Prova a rimuovere un filtro o a cambiare la ricerca.</p><button class="button primary" data-action="reset">Ripristina filtri</button></section>`;}
  function projectPicker() {
    const projectName=data?.project?.name || data?.source?.filename?.replace(/\.xlsx$/i,'') || 'Progetto';
    return `<div class="project-picker"><label for="project-select">Progetto aperto</label>${standalone?`<strong>${esc(projectName)}</strong>`:`<select id="project-select" aria-label="Progetto attivo" ${state.busy?'disabled':''}>${projects.map(p=>`<option value="${esc(p.id)}" ${p.id===activeProjectId?'selected':''}>${esc(p.name)}</option>`).join('')}</select><button class="new-project-button" data-action="new-project" ${state.busy?'disabled':''}>+ Nuovo progetto</button>`}</div>`;
  }
  function projectDialog() {
    if(!state.projectDialog)return '';
    const creating=state.projectDialog==='create';
    return `<div class="project-overlay"></div><section class="project-dialog" role="dialog" aria-modal="true" aria-labelledby="project-dialog-title" tabindex="-1"><div class="drawer-top"><span class="eyebrow">Progetti</span><button class="icon-button" data-action="close-project" aria-label="Chiudi importazione" ${state.busy?'disabled':''}>${icon('close')}</button></div><h2 id="project-dialog-title">${creating?'Nuovo progetto':'Aggiorna Excel'}</h2><p>${creating?'Assegna un nome e carica l’Excel del progetto. Sarà conservato separatamente dagli altri.':'Sostituisci l’Excel del progetto attivo. Gli altri progetti non vengono modificati.'}</p><label class="project-field" for="project-name">Nome progetto<input id="project-name" maxlength="100" value="${esc(creating?state.projectName:data?.project?.name||'Progetto')}" ${!creating?'readonly':''} placeholder="Es. Piano di remediation 2027"></label><label class="project-dropzone" for="project-file">${icon('upload',28)}<strong>${pendingFile?esc(pendingFile.name):'Seleziona il file Excel'}</strong><span>.xlsx · massimo 10 MB · stesso tracciato</span><input type="file" id="project-file" accept=".xlsx" ${state.busy?'disabled':''}></label><div class="import-guidance"><strong>Formato supportato</strong><span>Fogli All Remediations e LE_List; supportato anche il formato precedente Remediations/OT. I dati e i gruppi delle entità possono cambiare. Le formule devono avere risultati ricalcolati e salvati.</span></div><div class="project-dialog-actions"><button class="button" data-action="close-project" ${state.busy?'disabled':''}>Annulla</button><button class="button primary" id="submit-project" data-action="submit-project" ${state.busy?'disabled':''}>${state.busy?'Importazione…':creating?'Crea progetto':'Aggiorna progetto'}</button></div></section>`;
  }
  function renderEmpty() {
    document.body.classList.remove('presentation','filters-open');
    $('#app').innerHTML=`<header class="empty-header"><a class="brand" aria-label="KPMG · Data Visualization Tool" href="#"><span class="brand-mark kpmg-brand" aria-hidden="true">${kpmgLogo()}</span><span class="brand-name">Data Visualization<span class="brand-line"> Tool</span><span class="brand-sub">STRUMENTO INTERNO</span></span></a><span class="local-status"><span class="status-dot"></span>Archivio locale</span></header><main class="welcome-page"><h1>Progetti</h1><p>Crea un progetto e carica il relativo Excel per consultare remediation, budget e country.</p><button class="button primary" data-action="new-project">${icon('upload',18)} Crea il primo progetto</button><div class="welcome-features"><article>${icon('grid',25)}<h2>Budget</h2><p>Investimenti per anno, dominio e owner.</p></article><article>${icon('map',25)}<h2>Navigazione</h2><p>Schede delle remediation, mappa e budget per country.</p></article><article>${icon('shield',25)}<h2>Archivio progetti</h2><p>Ogni progetto mantiene il proprio Excel e i propri dati.</p></article></div><div class="welcome-format">Formato Excel: <strong>All Remediations + LE_List</strong>, oppure tracciato precedente Remediations/OT. Usa lo stesso tracciato per i progetti futuri.</div></main>${projectDialog()}<div id="toast" class="toast" role="status" aria-live="polite"></div>`;
    document.body.style.overflow=state.projectDialog?'hidden':'';
    if(state.projectDialog)$('#project-name')?.focus();
  }
  function render() {
    if(!data){renderEmpty();return;}
    normalizeFilters();
    if(!views.some(view=>view[0]===state.view))state.view='overview';
    const active=document.activeElement,focusId=active?.id,position=active?.selectionStart,focusFilter=active?.dataset.filter,focusValue=active?.value;
    const topFilterFocus=active?.closest('.view-filters')?active:null;
    const topFilterScroll=[...document.querySelectorAll('.view-filter-options')].map(element=>({element,top:element.scrollTop}));
    const focusedMapField=['ownerMapYear','ownerMapOwner','ownerMapDomain'].find(field=>active?.dataset[field]!==undefined);
    const focusedMapValue=focusedMapField?active.dataset[focusedMapField]:null;
    const sidebarScroll=$('.sidebar')?.scrollTop||0;
    const riskScroll=$('.investment-map .map-scroll');
    const riskPosition={left:riskScroll?.scrollLeft||0,top:riskScroll?.scrollTop||0};
    const ownerMapScroll=$('.owner-map-panel .map-scroll');
    const ownerMapPosition={left:ownerMapScroll?.scrollLeft||0,top:ownerMapScroll?.scrollTop||0};
    const groups=[...document.querySelectorAll('details[data-group]')];if(groups.length)state.filterOpen=groups.filter(g=>g.open).map(g=>g.dataset.group);
    const ambiguousCount=data.rows.filter(r=>r.allocationStatus==='ambiguous').length;
    const rows=currentRows(),view=views.find(v=>v[0]===state.view),sheetLabel=state.filters.sheets.length?state.filters.sheets.join(' + '):'Nessun perimetro selezionato';
    document.body.classList.toggle('presentation',state.presentation);
    document.body.classList.toggle('filters-open',state.menu);
    const markup=`${sidebar()}<div class="main-shell"><header class="topbar"><div class="breadcrumb"><button class="icon-button mobile-menu" data-action="menu" aria-label="Apri navigazione">${icon('menu')}</button><span>Workspace</span>${icon('chevron',12)}<strong>${view[2]}</strong></div><div class="topbar-right"><span class="local-status"><span class="status-dot"></span>${standalone?'Copia offline':'Dati locali'}</span><button class="button small" data-action="presentation">${icon('present',15)}${state.presentation?'Esci presentazione':'Presentazione'}</button></div></header>
      <main id="main-content"><div class="page-heading"><div><h1>${esc(view[2])}</h1><p>${esc({overview:'Budget e remediation per anno, dominio e owner.',map:'Seleziona anno e dominio per aprire le remediation.','owner-map':'Esplora le associazioni tra anno, owner, dominio e remediation.','remediation-map':'Anno → Remediation → Risk Type → Impact Type → Capex/Opex.', 'risk-first-map':'Anno → Risk Type → Remediation → Impact Type → Capex/Opex.', 'risk-map':'Associazioni tra investimenti, rischi, impatto e remediation.',table:'Apri una scheda per consultare attività, budget e riferimenti al file.',countries:'Budget Local per country, legal entity e anno.'}[state.view])}</p></div><div class="heading-actions">${!standalone?`<button class="button primary pptx-button" data-action="pptx" ${state.busy||state.exportingPptx||!rows.length?'disabled':''} title="Sintesi di massimo 15 slide dei dati filtrati, con dettagli completi nelle note">${icon('present',16)} ${state.exportingPptx?'Creazione PowerPoint…':'Scarica PowerPoint'}</button>`:''}<button class="button" data-action="export-menu">${icon('download',16)} Esporta ${icon('chevron',12)}</button>${!standalone?`<button class="button" data-action="import" ${state.busy?'disabled':''}>${icon('upload',16)} ${state.busy?'Importazione…':'Aggiorna Excel'}</button>`:''}${state.exportMenu?`<div class="export-menu"><button data-action="csv">${icon('table',16)} CSV delle righe filtrate</button><button data-action="html">${icon('file',16)} Copia HTML offline</button><button data-action="print">${icon('print',16)} Stampa / salva PDF</button>${!standalone?`<button data-action="source">${icon('download',16)} Excel originale</button>`:''}</div>`:''}</div></div>
      <div class="source-line">${icon('file',15)}<strong>${esc(data.source.filename)}</strong><span>•</span><span>${esc(sheetLabel)}</span><span>•</span><span>${data.rows.length} righe disponibili · ${data.entities.length} entità</span>${!standalone?`<button class="text-button" data-action="restore" ${state.busy?'disabled':''}>Ripristina prima importazione</button>`:''}</div>
      ${toolbar()}${chips()}${viewFilters()}${kpis(rows)}
      <div class="data-notice">${icon('info',16)}<p><strong>Importi dal file Excel.</strong> ${ambiguousCount?`${ambiguousCount} righe hanno un’attribuzione geografica da verificare; `:''}le stime mancanti restano distinte da zero.</p></div>
      <div class="view-tabs" role="navigation" aria-label="Seleziona vista">${views.map(([id,i,l])=>`<button data-view="${id}" class="${state.view===id?'active':''}">${icon(i,16)}${l}</button>`).join('')}<span>${rows.length} righe selezionate</span></div>
      <div id="view-content">${!rows.length?emptyView():state.view==='countries'?countriesView():state.view==='table'?tableView(rows):state.view==='map'?mapView(rows):state.view==='owner-map'?ownerMapView(rows):state.view==='risk-map'?riskMapView(rows):state.view==='risk-first-map'?riskMapView(rows,true):state.view==='remediation-map'?riskMapView(rows,true,true):overview(rows)}</div>
      <footer class="main-footer"><span><strong>Data Visualization Tool</strong> · KPMG · Uso interno · Versione ${APP_VERSION}</span><span>Fonte Excel · importi in EUR · nessun dato generato</span><span>SHA-256 ${esc(data.source.sha256?.slice(0,12)||'—')}</span></footer></main></div>${detailPanel()}${projectDialog()}<div id="toast" class="toast" role="status" aria-live="polite"></div>`;
    const oldSidebar=$('.sidebar'),sourceKey=(data.project?.id||'')+':'+data.source.sha256;
    if(oldSidebar?.dataset.source===sourceKey){
      const template=document.createElement('template');template.innerHTML=markup;template.content.querySelector('.sidebar').remove();
      // Retain the live controls so multi-selection keeps dropdown scroll and focus.
      const oldFilters=$('.view-filters');
      if(oldFilters?.dataset.source===sourceKey)template.content.querySelector('.view-filters').replaceWith(oldFilters);
      for(const child of [...$('#app').childNodes])if(child!==oldSidebar)child.remove();
      $('#app').append(template.content);
    }else{$('#app').innerHTML=markup;if($('.sidebar'))$('.sidebar').scrollTop=sidebarScroll;}
    syncSidebar();
    syncViewFilters();
    for(const {element,top} of topFilterScroll)if(element.isConnected)element.scrollTop=top;
    const restoredRiskScroll=$('.investment-map .map-scroll');
    if(restoredRiskScroll){restoredRiskScroll.scrollLeft=riskPosition.left;restoredRiskScroll.scrollTop=riskPosition.top;}
    const restoredOwnerMapScroll=$('.owner-map-panel .map-scroll');
    if(restoredOwnerMapScroll){restoredOwnerMapScroll.scrollLeft=ownerMapPosition.left;restoredOwnerMapScroll.scrollTop=ownerMapPosition.top;}
    if(focusedMapField){const node=[...document.querySelectorAll('#owner-concept-map .map-node')].find(item=>item.dataset[focusedMapField]===focusedMapValue);node?.focus({preventScroll:true});}
    if(focusFilter){const input=[...document.querySelectorAll('input[data-filter]')].find(i=>i.dataset.filter===focusFilter&&i.value===focusValue);input?.focus({preventScroll:true});}
    if(topFilterFocus?.isConnected)topFilterFocus.focus({preventScroll:true});
    if(focusId&&$('#'+focusId)){const input=$('#'+focusId);input.focus({preventScroll:true});if(typeof position==='number'&&input.setSelectionRange) input.setSelectionRange(position,position);}
    if(state.projectDialog){$('#project-name')?.focus();document.body.style.overflow='hidden';}
    else if(state.detail) {$('#close-detail')?.focus(); document.body.style.overflow='hidden';} else document.body.style.overflow='';
  }
  let toastTimer;
  function toast(message,error=false){clearTimeout(toastTimer);const el=$('#toast');el.textContent=message;el.className='toast visible'+(error?' error':'');toastTimer=setTimeout(()=>el.classList.remove('visible'),6500);}
  function setFilters(patch){
    const position=patch.scope!==undefined?{left:window.scrollX,top:window.scrollY}:null;
    for(const field of ['capexOpex','risk','impact','riskLevel','remediationType']){
      if(!Array.isArray(patch[field]))continue;
      const visible=visibleFilterOptions(field),chosen=patch[field].filter(value=>visible.includes(value));
      patch[field]=chosen.length>0&&chosen.length===visible.length?filterOptions(field):chosen;
    }
    lastMapActivation=null;Object.assign(state.filters,patch);state.page=1;state.mapPage=0;state.ownerMapPage=0;render();
    if(position)window.scrollTo(position.left,position.top);
  }
  function download(content,type,filename){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function exportHtml(){
    if(!window.DVT_CSS||!window.DVT_MODEL||!window.DVT_COUNTRIES||!window.DVT_OWNER_MAP||!window.DVT_APP) { toast('Preparazione esportazione in corso. Riprova tra un istante.',true); return; }
    const doc=document.documentElement.cloneNode(true);doc.querySelector('#app').innerHTML='<div class="initial-loading">Apertura della copia offline…</div>';
    doc.querySelectorAll('script').forEach(el=>el.remove());doc.querySelectorAll('link[rel="stylesheet"]').forEach(el=>el.remove());
    const style=document.createElement('style');style.textContent=window.DVT_CSS;doc.querySelector('head').appendChild(style);
    for(const contents of ['window.DVT_DATA='+JSON.stringify(data).replace(/</g,'\\u003c')+';window.DVT_STATE='+JSON.stringify({view:state.view,filters:state.filters,selectedRemediation:state.selectedRemediation,riskPath,riskFirstPath,remediationPath,mapYear:state.mapYear,mapDomain:state.mapDomain,mapPage:state.mapPage,ownerMapYear:state.ownerMapYear,ownerMapOwner:state.ownerMapOwner,ownerMapDomain:state.ownerMapDomain,ownerMapPage:state.ownerMapPage,pageSize:state.pageSize,sort:state.sort,direction:state.direction}).replace(/</g,'\\u003c')+';', window.DVT_MODEL, window.DVT_COUNTRIES, window.DVT_OWNER_MAP, window.DVT_APP]) {const script=document.createElement('script');script.textContent=contents;doc.querySelector('body').appendChild(script);}
    // Scripts are static application code; source cell text is JSON-escaped above.
    download('<!doctype html>\n'+doc.outerHTML,'text/html;charset=utf-8','Data-Visualization-Tool-remediation-offline.html');toast('Copia offline salvata: include tutti i dati e i filtri.');
  }
  async function exportPng(){const ownerMode=state.view==='owner-map',svg=$(ownerMode?'#owner-concept-map':'#concept-map'),year=ownerMode?state.ownerMapYear:state.mapYear;if(!svg)return;const clone=svg.cloneNode(true),style=document.createElementNS('http://www.w3.org/2000/svg','style');style.textContent=window.DVT_CSS||'';clone.insertBefore(style,clone.firstChild);const view=svg.viewBox.baseVal;clone.setAttribute('width',view.width*2);clone.setAttribute('height',view.height*2);const blob=new Blob([new XMLSerializer().serializeToString(clone)],{type:'image/svg+xml'}),url=URL.createObjectURL(blob),img=new Image();img.onload=()=>{const canvas=document.createElement('canvas');canvas.width=view.width*2;canvas.height=view.height*2;canvas.getContext('2d').drawImage(img,0,0);URL.revokeObjectURL(url);canvas.toBlob(b=>{if(b)download(b,'image/png',`Data-Visualization-Tool-mappa-${ownerMode?'owner-':''}${year||'non-specificato'}.png`);},'image/png');};img.onerror=()=>{URL.revokeObjectURL(url);toast('Impossibile esportare la mappa.',true);};img.src=url;}
  function presentationRequest() {
    const filters=JSON.parse(JSON.stringify(state.filters));
    const entities=entitySelection();
    const countryRows=Object.fromEntries(data.entities.filter(entity=>filters.entities.includes(entity.id)).map(entity=>[
      entity.id,M.filterRows(data.rows,{...filters,entities:[entity.id],entityScope:'selected'}).map(row=>row.key)
    ]));
    return {projectId:data.project.id,rowKeys:currentRows().map(row=>row.key),entities,scope:filters.scope,filters,countryRows};
  }
  async function exportPowerPoint() {
    if(standalone||state.busy||state.exportingPptx)return;
    const request=presentationRequest();
    if(!request.rowKeys.length)return toast('Non ci sono remediation da esportare con questi filtri.',true);
    state.exportingPptx=true;state.exportMenu=false;render();
    try {
      const response=await fetch('/api/presentation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
      if(!response.ok){let message='Impossibile creare il PowerPoint.';try{message=(await response.json()).error||message;}catch{}throw new Error(message);}
      const file=await response.blob();
      const disposition=response.headers.get('Content-Disposition')||'';
      const nameMatch=disposition.match(/filename\*=UTF-8''([^;]+)/i);
      let filename='Data-Visualization-Tool.pptx';
      if(nameMatch){try{filename=decodeURIComponent(nameMatch[1]);}catch{}}
      download(file,'application/vnd.openxmlformats-officedocument.presentationml.presentation',filename);
      toast('PowerPoint scaricato: sintesi e '+request.rowKeys.length+' voci complete nelle note.');
    }catch(error){toast(error.message,true);}
    finally{state.exportingPptx=false;const button=document.querySelector('[data-action="pptx"]');if(button){button.disabled=state.busy||!currentRows().length;button.innerHTML=icon('present',16)+' Scarica PowerPoint';}}
  }
  async function refreshProjects() {
    const response=await fetch('/api/projects');const result=await response.json();
    if(!response.ok)throw new Error(result.error||'Archivio progetti non disponibile.');
    projects=result.projects;activeProjectId=data?.project?.id||result.activeProjectId;
  }
  function acceptProject(document) {
    data=document;activeProjectId=document.project.id;
    const entry={id:document.project.id,name:document.project.name,filename:document.source.filename,rows:document.rows.length,entities:document.entities.length};
    const previous=projects.findIndex(project=>project.id===entry.id);
    if(previous<0)projects.push(entry);else projects[previous]={...projects[previous],...entry};
  }
  async function refreshSavedProjects() {
    try {await refreshProjects();return '';}
    catch {return ' Il progetto è salvato; l’elenco non è stato aggiornato. Ricarica la pagina per riprovare.';}
  }
  function resetProjectView() {
    riskPath=[];riskFirstPath=[];remediationPath=[];clearTimeout(searchTimer);state.filters=defaultFilters();state.detail=null;state.selectedRemediation=null;lastMapActivation=null;state.page=1;state.view='overview';state.mapYear=null;state.mapDomain=null;state.mapPage=0;state.ownerMapYear=null;state.ownerMapOwner=null;state.ownerMapDomain=null;state.ownerMapPage=0;state.menu=false;state.exportMenu=false;state.topFilterOpen=null;state.projectDialog=null;state.projectName='';pendingFile=null;
  }
  function openProjectDialog(mode, file=null) {
    if(state.busy)return;
    state.exportMenu=false;state.projectDialog=mode;pendingFile=file;state.projectName=file?file.name.replace(/\.xlsx$/i,''):'';render();
  }
  async function activateProject(id) {
    if(state.busy||id===activeProjectId)return;
    clearTimeout(searchTimer);state.busy=true;render();
    try {const response=await fetch('/api/projects/'+encodeURIComponent(id)+'/activate',{method:'POST'});const result=await response.json();if(!response.ok)throw new Error(result.error||'Progetto non disponibile.');acceptProject(result);resetProjectView();state.busy=false;render();toast('Progetto aperto: '+result.project.name);}
    catch(error){state.busy=false;render();toast(error.message,true);}
  }
  async function importWorkbook(file){
    if(state.busy)return;
    if(!file)return toast('Seleziona il file Excel del progetto.',true);
    if(!file.name.toLowerCase().endsWith('.xlsx'))return toast('Seleziona un file Excel .xlsx.',true);
    if(file.size>10*1024*1024)return toast('Il limite di importazione è 10 MB.',true);
    const creating=state.projectDialog==='create';const name=state.projectName.trim();
    if(creating&&!name)return toast('Inserisci il nome del progetto.',true);
    clearTimeout(searchTimer);state.busy=true;state.exportMenu=false;render();
    const path=creating?'/api/projects?filename='+encodeURIComponent(file.name)+'&name='+encodeURIComponent(name):'/api/workbook?filename='+encodeURIComponent(file.name)+'&projectId='+encodeURIComponent(data.project.id);
    try {const response=await fetch(path,{method:'POST',body:file,headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}});const result=await response.json();if(!response.ok)throw new Error(result.error||'Importazione non riuscita.');acceptProject(result);resetProjectView();const warning=await refreshSavedProjects();state.busy=false;render();toast((creating?'Progetto creato. I dati degli altri progetti sono conservati.':'Excel aggiornato per il progetto attivo.')+warning);}
    catch(error){state.busy=false;render();toast(error.message,true);}
  }
  async function restoreProject() {
    if(state.busy||!data?.project)return;
    const targetId=data.project.id;
    clearTimeout(searchTimer);state.busy=true;state.exportMenu=false;render();
    let message='',failed=false;
    try {const response=await fetch('/api/reset?projectId='+encodeURIComponent(targetId),{method:'POST'});const result=await response.json();if(!response.ok)throw new Error(result.error||'Ripristino non riuscito.');acceptProject(result);resetProjectView();const warning=await refreshSavedProjects();message='Prima importazione del progetto ripristinata.'+warning;}
    catch(error){message=error.message;failed=true;}
    finally {state.busy=false;render();toast(message,failed);}
  }
  async function action(name){
    if(['csv','html','source','presentation','restore'].includes(name)) {state.exportMenu=false;render();}
    switch(name){
      case 'home':state.view='overview';render();break;
      case 'menu':state.menu=!state.menu;render();break;
      case 'reset':state.filters=defaultFilters();state.page=1;state.mapPage=0;state.ownerMapPage=0;render();break;
      case 'presentation':state.presentation=!state.presentation;render();break;
      case 'export-menu':state.exportMenu=!state.exportMenu;render();break;
      case 'close-detail':state.detail=null;render();break;
      case 'sort-direction':state.direction*=-1;render();break;
      case 'prev-page':state.page--;render();break;
      case 'next-page':state.page++;render();break;
      case 'map-prev':state.mapPage--;render();break;
      case 'map-next':state.mapPage++;render();break;
      case 'owner-map-prev':state.ownerMapPage--;render();break;
      case 'owner-map-next':state.ownerMapPage++;render();break;
      case 'owner-map-all':state.ownerMapOwner=null;state.ownerMapDomain=null;state.ownerMapPage=0;render();break;
      case 'new-project':openProjectDialog('create');break;
      case 'import':openProjectDialog('update');break;
      case 'submit-project':await importWorkbook(pendingFile);break;
      case 'close-project':if(!state.busy){state.projectDialog=null;pendingFile=null;render();}break;
      case 'pptx':await exportPowerPoint();break;
      case 'csv':download(M.csv(sortedRows(currentRows()),entitySelection(),state.filters.scope),'text/csv;charset=utf-8','Data-Visualization-Tool-remediation-filtrate.csv');break;
      case 'html':exportHtml();break;
      case 'png':await exportPng();break;
      case 'print':state.exportMenu=false;render();window.print();break;
      case 'source':{const a=document.createElement('a');a.href='/api/source?projectId='+encodeURIComponent(data.project.id);a.download=data.source.filename;a.click();break;}
      case 'restore':await restoreProject();break;
    }
  }
  let lastMapActivation=null;
  function selectMapRemediation(el, open=false, event=null) {
    const key=el.dataset.riskDetail||el.dataset.detail;
    const now=performance.now();
    state.selectedRemediation=key;
    if(el.dataset.riskDetail){const step=Number(el.dataset.riskStep);selectRiskStep(step,el.dataset.riskValue);}
    if(open){lastMapActivation=null;state.detail=key;render();return;}
    lastMapActivation={key,view:state.view,time:now,x:event?.clientX,y:event?.clientY};
    if(el.dataset.riskDetail){render();[...document.querySelectorAll('[data-risk-detail]')].find(node=>node.dataset.riskDetail===key)?.focus({preventScroll:true});}
    else{document.querySelectorAll('.map-node.leaf.chosen').forEach(node=>node.classList.remove('chosen'));el.classList.add('chosen');}
  }

  document.addEventListener('click',event=>{
    // A first click can expand/rescale the SVG under the pointer in presentation mode.
    // Recognize the second physical click even if it now lands on a different SVG child.
    if(event.detail>0&&lastMapActivation?.view===state.view&&performance.now()-lastMapActivation.time<500&&Math.hypot(event.clientX-lastMapActivation.x,event.clientY-lastMapActivation.y)<6&&event.target.closest('.map-panel')){event.preventDefault();state.detail=lastMapActivation.key;lastMapActivation=null;render();return;}
    const openFilter=$('.view-filters details[open]');
    if(openFilter&&!openFilter.contains(event.target))closeViewFilters();
    const el=event.target.closest('[data-risk-step],[data-action],[data-view],[data-detail],[data-scope],[data-budget-component],[data-year],[data-domain],[data-owner],[data-entity],[data-sort],[data-remove-field],[data-clear],[data-map-year],[data-map-domain],[data-country-year],[data-reset-group],[data-owner-map-year],[data-owner-map-owner],[data-owner-map-domain]');if(!el){lastMapActivation=null;if(state.exportMenu&&!event.target.closest('.export-menu,.heading-actions')){state.exportMenu=false;render();}return;}
    if(el.hasAttribute('disabled')||el.getAttribute('aria-disabled')==='true')return;
    event.preventDefault();
    if(el.dataset.action){action(el.dataset.action);return;}
    if(el.dataset.view){lastMapActivation=null;state.view=el.dataset.view;state.exportMenu=false;state.menu=false;render();return;}

    if(el.closest('.map-panel')&&(el.dataset.riskDetail||el.dataset.detail)){selectMapRemediation(el,event.detail===0,event);return;}
    if(el.dataset.detail){state.detail=el.dataset.detail;render();return;}
    if(el.dataset.scope){setFilters({scope:el.dataset.scope});return;}
    if(el.dataset.budgetComponent){
      const component=el.dataset.budgetComponent;
      if(state.filters.scope===component)return;
      setFilters({scope:state.filters.scope==='all'?(component==='global'?'local':'global'):'all'});return;
    }
    if(el.dataset.year){setFilters({years:[el.dataset.year]});return;}
    if(el.dataset.domain){state.view='table';setFilters({domains:[el.dataset.domain]});return;}
    if(el.dataset.owner){state.view='table';setFilters({owners:[el.dataset.owner]});return;}
    if(el.dataset.countryYear!==undefined){state.view='map';state.mapYear=Number(el.dataset.countryYear);state.mapDomain=null;setFilters({entities:[el.dataset.entity],years:[el.dataset.countryYear]});return;}
    if(el.dataset.resetGroup){setFilters({[el.dataset.resetGroup]:filterOptions(el.dataset.resetGroup)});return;}
    if(el.dataset.entity){state.view='table';setFilters({entities:[el.dataset.entity]});return;}
    if(el.dataset.sort){state.direction=state.sort===el.dataset.sort?-state.direction:1;state.sort=el.dataset.sort;render();return;}
    if(el.dataset.removeField){setFilters({[el.dataset.removeField]:state.filters[el.dataset.removeField].filter(v=>v!==el.dataset.value)});return;}
    if(el.dataset.clear){setFilters({[el.dataset.clear]:'all'});return;}
    if(el.dataset.riskStep!==undefined){const step=Number(el.dataset.riskStep);selectRiskStep(step,el.dataset.riskValue);render();[...document.querySelectorAll('[data-risk-step]')].find(node=>Number(node.dataset.riskStep)===step&&node.dataset.riskValue===activeRiskPath()[step])?.focus({preventScroll:true});return;}
    if(el.dataset.ownerMapYear!==undefined){state.ownerMapYear=el.dataset.ownerMapYear;state.ownerMapOwner=null;state.ownerMapDomain=null;state.ownerMapPage=0;render();return;}
    if(el.dataset.ownerMapOwner!==undefined){state.ownerMapOwner=el.dataset.ownerMapOwner;state.ownerMapDomain=null;state.ownerMapPage=0;render();return;}
    if(el.dataset.ownerMapDomain!==undefined){state.ownerMapDomain=el.dataset.ownerMapDomain;state.ownerMapPage=0;render();return;}
    if(el.dataset.mapYear){state.mapYear=Number(el.dataset.mapYear);state.mapPage=0;render();return;}
    if(el.dataset.mapDomain){state.mapDomain=el.dataset.mapDomain;state.mapPage=0;render();return;}
  });
  document.addEventListener('dblclick',event=>{const el=event.target.closest('.map-node[data-detail],.map-node[data-risk-detail]');if(el&&!state.detail){event.preventDefault();selectMapRemediation(el,true,event);}});
  document.addEventListener('toggle',event=>{
    const group=event.target;
    if(!group.matches?.('details[data-top-group]'))return;
    if(group.open){
      for(const other of document.querySelectorAll('.view-filters details[open]'))if(other!==group)other.open=false;
      state.topFilterOpen=group.dataset.topGroup;
    }else if(state.topFilterOpen===group.dataset.topGroup)state.topFilterOpen=null;
  },true);
  document.addEventListener('change',event=>{const el=event.target;
    const master=el.dataset.filterAll||el.dataset.topFilterAll,field=el.dataset.filter||el.dataset.topFilter;
    if(master)setFilters({[master]:el.checked?filterOptions(master):[]});
    if(field)setFilters({[field]:el.checked?[...state.filters[field],el.value]:state.filters[field].filter(v=>v!==el.value)});
    const select=el.dataset.select||el.dataset.topSelect||el.dataset.sidebarSelect;if(select)setFilters({[select]:el.value});
    if(el.id==='remediation-sort'){state.sort=el.value;state.page=1;render();}
    if(el.id==='page-size'){state.pageSize=Number(el.value);state.page=1;render();}
    if(el.id==='project-select')activateProject(el.value);
    if(el.id==='project-file'){pendingFile=el.files[0]||null;if(pendingFile&&!state.projectName.trim())state.projectName=pendingFile.name.replace(/\.xlsx$/i,'');render();}
  });
  let searchTimer;document.addEventListener('input',e=>{if(e.target.id==='project-name'){state.projectName=e.target.value;}if(e.target.id==='search'||e.target.id==='presentation-search'){const value=e.target.value;clearTimeout(searchTimer);searchTimer=setTimeout(()=>setFilters({query:value}),150);}});
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'){if(state.projectDialog){if(!state.busy){state.projectDialog=null;pendingFile=null;render();}}else if(state.exportMenu){state.exportMenu=false;render();}else if(state.detail){state.detail=null;render();}else if(closeViewFilters({focus:true})){event.preventDefault();}else if(state.presentation){state.presentation=false;render();}return;}
    if((event.key==='Enter'||event.key===' ')&&event.target.matches('[role="button"]')){event.preventDefault();event.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}
    if(event.key==='Tab'&&(state.detail||state.projectDialog)){const drawer=state.projectDialog?$('.project-dialog'):$('.detail-drawer'),items=[...drawer.querySelectorAll('button,a,input,select,[tabindex="0"]')].filter(el=>!el.disabled);if(!items.length)return;if(event.shiftKey&&document.activeElement===items[0]){event.preventDefault();items.at(-1).focus();}else if(!event.shiftKey&&document.activeElement===items.at(-1)){event.preventDefault();items[0].focus();}}
  });
  document.addEventListener('dragover',e=>{if(!standalone){e.preventDefault();}});
  document.addEventListener('drop',e=>{if(!standalone){e.preventDefault();if(!state.busy)openProjectDialog('create',e.dataTransfer.files[0]);}});
  async function boot(){
    try{
      if(standalone){data=window.DVT_DATA;window.DVT_CSS=[...document.querySelectorAll('style')].map(e=>e.textContent).join('\n');}
      else{await refreshProjects();const response=await fetch('/api/workbook'+(activeProjectId?'?projectId='+encodeURIComponent(activeProjectId):''));if(response.status===404){data=null;}else if(!response.ok){const error=await response.json();throw new Error(error.error||'Caricamento dati non riuscito');}else{acceptProject(await response.json());}}
      render();
      if(!standalone){const assets=await Promise.all(['styles.css','countries.css','brand.css','model.js','countries.js','owner-map.js','app.js'].map(async url=>{const response=await fetch(url);if(!response.ok)throw new Error('Risorsa non disponibile');return response.text();}));window.DVT_CSS=assets.slice(0,3).join("\n");[window.DVT_MODEL,window.DVT_COUNTRIES,window.DVT_OWNER_MAP,window.DVT_APP]=assets.slice(3);}
      else{const scripts=[...document.querySelectorAll('script')];window.DVT_MODEL=scripts.find(s=>s.textContent.trimStart().startsWith('/* Pure, deterministic view calculations.'))?.textContent||'';window.DVT_COUNTRIES=scripts.find(script=>script.textContent.trimStart().startsWith('/* CountryInvestments —'))?.textContent||'';window.DVT_OWNER_MAP=scripts.find(s=>s.textContent.trimStart().startsWith('/* OwnerMap —'))?.textContent||'';window.DVT_APP=scripts.find(s=>s.textContent.trimStart().startsWith('/* Data Visualization Tool — self-contained client.'))?.textContent||'';}
    }catch(error){$('#app').innerHTML=`<div class="initial-loading"><span class="brand-mark kpmg-brand" aria-hidden="true">${kpmgLogo()}</span><h1>Impossibile aprire i dati</h1><p>${esc(error.message)}</p><p>Avvia il server locale con <code>python -m app.server</code>, poi ricarica la pagina.</p></div>`;}
  }
  boot();
})();
