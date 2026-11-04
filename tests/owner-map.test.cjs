'use strict';
// Fictional source rows only. Associations and budgets are read from the model.
const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../web/model.js');
const {render} = require('../web/owner-map.js');

const esc = value => String(value ?? '').replace(/[&<>"']/g, value =>
  ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[value]));
const row = (key, year, owner, domain, globalBudget, localTotal, amount = localTotal) => ({
  key, id:'R.REPEATED', sheet:'Remediations', excelRow:Number(key.split(':').at(-1)) || 4,
  name:'Original remediation ' + key, year, owner, domain, globalBudget, localTotal,
  allocationStatus:'mapped', allocations:[{entityId:'Entity 01', amount}],
});
const rows = [
  row('Remediations:4', 2027, 'Supplier A', 'Governance', 1000, 200, 20),
  row('Remediations:5', 2027, 'Supplier A', 'Governance', 300, 40, 4),
  row('Remediations:6', 2027, 'Supplier A', 'Resilience', 80, 0),
  row('Remediations:7', 2027, 'Supplier B', 'Security', 5000, 600, 60),
  row('Remediations:8', 2027, '', 'Security', null, 0),
  row('Remediations:9', 2028, 'Supplier C', 'Operations', 900, 50, 5),
];
function view(patch = {}) {
  const selected = patch.rows || rows;
  return render({data:{rows:selected}, rows:selected, year:null, owner:null, domain:null, page:0,
    esc, icon:() => '', money:M.money, model:M, scope:'all', entitySelection:null,
    colorForYear:() => '#7964cf', colorForDomain:() => '#478ba8', ...patch});
}
function groups(html, className) {
  return [...html.matchAll(/<g\b([^>]*)>([\s\S]*?)<\/g>/g)]
    .filter(match => new RegExp(`\\b${className}\\b`).test(match[1]))
    .map(match => ({attributes:match[1], body:match[2]}));
}
function node(html, attribute, value) {
  return [...html.matchAll(/<g\b([^>]*)>([\s\S]*?)<\/g>/g)]
    .find(match => match[1].includes(`${attribute}="${esc(value)}"`));
}
function details(html) {
  return groups(html, 'leaf').map(group => group.attributes.match(/data-detail="([^"]*)"/)?.[1]);
}

test('owners and domains follow the selected year, with no fabricated domain count', () => {
  const result = view();
  assert.equal(result.year, '2027');
  assert.equal(result.owner, null);
  assert.equal(result.domain, null);
  assert.equal(groups(result.html, 'year-node').length, 2);
  assert.equal(groups(result.html, 'owner-node').length, 3);
  assert.equal(groups(result.html, 'domain-node').length, 3);
  for (const owner of ['Supplier A', 'Supplier B', 'Non specificato']) {
    assert.ok(node(result.html, 'data-owner-map-owner', owner), owner);
  }
  assert.equal(node(result.html, 'data-owner-map-owner', 'Supplier C'), undefined);
  assert.equal(details(result.html).length, 0);
  assert.match(result.html, /Seleziona un dominio/);
  const next = view({year:'2028'});
  assert.equal(groups(next.html, 'owner-node').length, 1);
  assert.equal(groups(next.html, 'domain-node').length, 1);
  assert.ok(node(next.html, 'data-owner-map-owner', 'Supplier C'));
});

test('year, owner and domain drilldown retains repeated source IDs as separate rows', () => {
  const result = view({year:'2027', owner:'Supplier A', domain:'Governance'});
  assert.deepEqual(details(result.html), ['Remediations:4', 'Remediations:5']);
  assert.ok(result.html.includes('Original remediation Remediations:4'));
  assert.ok(result.html.includes('Original remediation Remediations:5'));
  assert.equal(groups(result.html, 'owner-node').length, 3, 'other owners remain navigable');
  assert.equal(groups(result.html, 'domain-node').length, 3, 'all year domains remain visible');
  const security = groups(result.html, 'domain-node').find(group => group.body.includes('Security'));
  assert.ok(security);
  assert.match(security.attributes, /aria-disabled="true"/);
  assert.doesNotMatch(security.attributes, /data-owner-map-domain=/);
  assert.equal(node(result.html, 'data-owner-map-domain', 'Resilience')?.[2].includes('Resilience'), true);
});

test('owner budgets obey scope and selected entity allocations without multiplying Global', () => {
  for (const [scope, expected] of [['all', 1404], ['global', 1380], ['local', 24]]) {
    const result = view({year:'2027', scope, entitySelection:['Entity 01']});
    const owner = node(result.html, 'data-owner-map-owner', 'Supplier A');
    assert.ok(owner, scope);
    assert.ok(owner[2].includes(esc(M.money(expected, true))), `${scope}: ${owner[2]}`);
  }
  const group = view({year:'2027', scope:'local'});
  assert.ok(node(group.html, 'data-owner-map-owner', 'Supplier A')[2].includes(esc(M.money(240, true))));
});

test('zero and unavailable estimates remain distinct, including ambiguous entity costs', () => {
  const records = [row('Remediations:10', 2027, 'Known zero', 'Security', 0, 0),
    row('Remediations:11', 2027, 'Unknown', 'Security', null, null),
    {...row('Remediations:12', 2027, 'Ambiguous', 'Security', 80, 810), allocationStatus:'ambiguous'}];
  const local = view({rows:records, scope:'local', entitySelection:['Entity 01']});
  assert.ok(node(local.html, 'data-owner-map-owner', 'Known zero')[2].includes(esc(M.money(0, true))));
  assert.ok(node(local.html, 'data-owner-map-owner', 'Unknown')[2].includes('Non stimato'));
  assert.ok(node(local.html, 'data-owner-map-owner', 'Ambiguous')[2].includes('Non stimato'));
  assert.ok(!node(local.html, 'data-owner-map-owner', 'Ambiguous')[2].includes('810'));
  const global = view({rows:records, scope:'global', entitySelection:['Entity 01']});
  assert.ok(node(global.html, 'data-owner-map-owner', 'Ambiguous')[2].includes(esc(M.money(80, true))));
});

test('all real owner-domain associations are drawn and unrelated associations are absent', () => {
  const result = view({year:'2027'});
  const edges = [...result.html.matchAll(/<path\b([^>]*data-owner-map-edge="owner-domain"[^>]*)\/?\s*>/g)];
  assert.equal(edges.length, 4);
  const pairs = edges.map(edge => {
    const attr = name => edge[1].match(new RegExp(`${name}="([^"]*)"`))?.[1];
    return [attr('data-owner-map-from'), attr('data-owner-map-to')].join(' → ');
  });
  assert.deepEqual(pairs.sort(), ['Supplier A → Governance', 'Supplier A → Resilience',
    'Supplier B → Security', 'Non specificato → Security'].sort());
});

test('six-row pagination clamps out-of-range pages and never drops rows or invents IDs', () => {
  const records = Array.from({length:14}, (_, index) => row(`Remediations:${20 + index}`,
    2027, 'Supplier A', 'Governance', index, index));
  const source = JSON.stringify(records);
  const seen = [];
  for (let page = 0; page < 3; page++) {
    const result = view({rows:records, owner:'Supplier A', domain:'Governance', page});
    assert.equal(result.page, page);
    const keys = details(result.html);
    assert.equal(keys.length, page === 2 ? 2 : 6);
    seen.push(...keys);
  }
  assert.deepEqual(seen, records.map(record => record.key));
  assert.equal(view({rows:records, owner:'Supplier A', domain:'Governance', page:999}).page, 2);
  assert.equal(view({rows:records, owner:'Supplier A', domain:'Governance', page:-4}).page, 0);
  assert.equal(JSON.stringify(records), source);
});

test('missing years and owners are explicit options, and stale selections clear safely', () => {
  const record = row('Remediations:40', null, '', '', 0, 0);
  const result = view({rows:[...rows, record], year:'', owner:'Non specificato', domain:'Non specificato'});
  assert.equal(result.year, '');
  assert.ok(result.html.includes('Anno non specificato'));
  assert.deepEqual(details(result.html), ['Remediations:40']);
  const stale = view({year:'2039', owner:'Removed owner', domain:'Removed domain', page:40});
  assert.equal(stale.year, '2027');
  assert.equal(stale.owner, null);
  assert.equal(stale.domain, null);
  assert.equal(stale.page, 0);
});

test('source strings cannot escape text or attribute contexts', () => {
  const owner = 'Supplier "quoted" </text><script>alert(1)</script>';
  const domain = 'Domain <img src=x onerror=alert(1)> & operations';
  const record = {...row('Remediations:50', 2027, owner, domain, 1, 2),
    name:'Original </text><script>alert(2)</script> & "quote"'};
  const result = view({rows:[record], owner, domain});
  assert.doesNotMatch(result.html, /<script\b|<img\b/);
  assert.ok(result.html.includes('&lt;script&gt;'));
  assert.ok(result.html.includes('&amp;'));
  assert.ok(result.html.includes('&quot;'));
  assert.deepEqual(details(result.html), ['Remediations:50']);
});

test('the diagram height covers every year, every owner and every domain', () => {
  for (const dimension of ['years', 'owners', 'domains']) {
    const records = Array.from({length:25}, (_, index) => row(`Remediations:${100 + index}`,
      dimension === 'years' ? 2027 + index : 2027,
      dimension === 'owners' ? `Supplier ${index}` : 'Supplier A',
      dimension === 'domains' ? `Domain ${index}` : 'Security', 10, 20));
    const result = view({rows:records, year:'2027'});
    const bounds = result.html.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/);
    assert.ok(bounds);
    const height = Number(bounds[2]);
    for (const match of result.html.matchAll(/<rect\b[^>]*y="([\d.]+)"[^>]*height="([\d.]+)"/g)) {
      assert.ok(Number(match[1]) + Number(match[2]) <= height,
        `${dimension}: node exceeds SVG height ${match[0]}`);
    }
    assert.equal(groups(result.html, dimension === 'years' ? 'year-node' :
      dimension === 'owners' ? 'owner-node' : 'domain-node').length, 25, dimension);
  }
});

test('empty results render an empty state without errors or invalid numeric coordinates', () => {
  const result = view({rows:[]});
  assert.equal(result.domain, null);
  assert.equal(result.page, 0);
  assert.doesNotMatch(result.html, /NaN|Infinity|undefined/);
  assert.equal(details(result.html).length, 0);
});
