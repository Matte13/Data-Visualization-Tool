"""Browser checks for synchronized presentation filters using fictional data."""
import csv
from io import BytesIO
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from app.server import ExplorerServer, WorkbookStore
from fixtures import make_workbook, with_cached_values
from openpyxl import load_workbook
from playwright.sync_api import expect, sync_playwright
from pptx import Presentation


FIELDS = ('sheets', 'years', 'domains', 'owners', 'entities', 'nis2', 'priority')
VIEWS = ('overview', 'map', 'owner-map', 'table', 'countries')
SCOPE_TOTALS = {'all': 11090, 'global': 7600, 'local': 3490}


def ranking_workbook():
    """Opposing Global/Local leaders exercise ranking and annual-scale changes."""
    workbook = load_workbook(BytesIO(make_workbook(name_prefix='Ranking')))
    main = workbook['Remediations']
    main['I4'], main['J4'], main['I5'] = 100, 5000, 9000
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return with_cached_values(output.getvalue(), {
        'xl/worksheets/sheet2.xml': {'L4': 65080, 'L5': 1000, 'L6': 810, 'L7': 0,
                                   'L8': 0, 'I9': 12500, 'L9': 66890},
        'xl/worksheets/sheet3.xml': {'G2': 120, 'G3': 180},
    })


def top_group(page, field, *, open_group=True):
    group = page.locator(f'.view-filters details[data-top-group="{field}"]')
    if open_group and not group.evaluate('(element) => element.open'):
        group.locator('summary').click()
    return group


def row_count(page, count):
    expect(page.locator('.kpi-value').nth(3)).to_have_text(f'{count:02}')


def amount(page, value):
    formatted = page.evaluate('value => window.RemediationModel.money(value)', value)
    expect(page.locator('.kpi-value').nth(0)).to_have_text(formatted)


def assert_scope(page, scope):
    """One budget level is reflected in every visible or hidden control copy."""
    expect(page.locator('#sidebar-budget-scope')).to_have_value(scope)
    expect(page.locator('[data-top-select="scope"]')).to_have_value(scope)
    for value in ('all', 'global', 'local'):
        expect(page.locator(f'.toolbar [data-scope="{value}"]')).to_have_attribute(
            'aria-pressed', str(value == scope).lower())
    if page.locator('.annual-panel').count():
        for chart in ('year', 'domain'):
            for component in ('global', 'local'):
                button = page.locator(f'#budget-legend-{chart}-{component}')
                expect(button).to_have_attribute('aria-pressed', str(scope in ('all', component)).lower())
                assert (button.get_attribute('aria-disabled') == 'true') == (scope == component)


def chart_amounts(page, scope):
    """Independent fixture totals and relative bar scales for each component."""
    annual = {
        'all': {'2027': 3000, '2028': 7690, '2029': 400},
        'global': {'2027': 1500, '2028': 5700, '2029': 400},
        'local': {'2027': 1500, '2028': 1990, '2029': 0},
    }[scope]
    domains = {
        'all': {'Security': 8310, 'Governance': 2780},
        'global': {'Security': 6200, 'Governance': 1400},
        'local': {'Security': 2110, 'Governance': 1380},
    }[scope]
    for year, value in annual.items():
        label = page.evaluate('value => window.RemediationModel.money(value, true)', value)
        expect(page.locator(f'.annual-chart [data-year="{year}"] .column-total')).to_have_text(label)
    for domain, value in domains.items():
        label = page.evaluate('value => window.RemediationModel.money(value, true)', value)
        expect(page.locator(f'.domain-chart [data-domain="{domain}"] > strong')).to_have_text(label)
    height = page.locator('.annual-chart [data-year="2027"] .stacked-bar').evaluate(
        '(element) => parseFloat(element.style.height)')
    assert abs(height - annual['2027'] / max(annual.values()) * 100) < .01, (scope, height)
    width = page.locator('.domain-chart [data-domain="Governance"] .domain-stack').evaluate(
        '(element) => parseFloat(element.style.width)')
    assert abs(width - domains['Governance'] / max(domains.values()) * 100) < .01, (scope, width)
    for component in ('global', 'local'):
        year_height = page.locator(f'.annual-chart [data-year="2027"] .bar-{component}').evaluate(
            '(element) => element.getBoundingClientRect().height')
        domain_width = page.locator(f'.domain-chart [data-domain="Governance"] .{component}').evaluate(
            '(element) => element.getBoundingClientRect().width')
        visible = scope in ('all', component)
        assert (year_height > 0) == visible, (scope, component, year_height)
        assert (domain_width > 0) == visible, (scope, component, domain_width)


def positions(input_element):
    return input_element.evaluate('''element => {
      const group = element.closest('details');
      let scroll = element.parentElement;
      while (scroll && scroll !== group.parentElement) {
        if (/(auto|scroll)/.test(getComputedStyle(scroll).overflowY)
            && scroll.scrollHeight > scroll.clientHeight + 1) break;
        scroll = scroll.parentElement;
      }
      return {page: window.scrollY, inner: scroll?.scrollTop || 0,
        sidebar: document.querySelector('.sidebar').scrollTop,
        focused: document.activeElement === element, open: group.open};
    }''')


def close_top_groups(page):
    for field in FIELDS:
        group = top_group(page, field, open_group=False)
        if group.evaluate('(element) => element.open'):
            group.locator('summary').click()


def main():
    with tempfile.TemporaryDirectory(prefix='dvt-presentation-filters-') as directory:
        root = Path(directory)
        shutil.copytree(ROOT / 'web', root / 'web')
        store = WorkbookStore(root)
        store.create(make_workbook(name_prefix='Review'), 'review.xlsx', 'Review project')
        server = ExplorerServer(('127.0.0.1', 0), store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        errors, offline_requests = [], []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
                    args=['--no-sandbox'])
                page = browser.new_page(viewport={'width': 1440, 'height': 1100})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base)
                bar = page.locator('.view-filters')
                expect(bar).to_be_visible()
                assert bar.evaluate('''element => Boolean(element.compareDocumentPosition(
                    document.querySelector('.view-tabs')) & Node.DOCUMENT_POSITION_FOLLOWING)''')
                row_count(page, 7)
                expect(page.locator('#sidebar-budget-scope')).to_be_visible()
                expect(page.locator('[data-top-select="scope"]')).to_be_visible()
                assert_scope(page, 'all')
                chart_amounts(page, 'all')

                # Every copy starts selected and its master controls that same dimension.
                for field in FIELDS:
                    group = top_group(page, field)
                    master = group.locator(f'input[data-top-filter-all="{field}"]')
                    expect(master).to_be_checked()
                    assert group.locator('input[data-top-filter]').evaluate_all(
                        '(elements) => elements.every(element => element.checked)')
                    master.uncheck()
                    row_count(page, 0)
                    expect(page.locator(f'.sidebar input[data-filter-all="{field}"]')).not_to_be_checked()
                    master.check()
                    row_count(page, 7)
                    expect(page.locator(f'.sidebar input[data-filter-all="{field}"]')).to_be_checked()

                # A checkbox in either surface updates both copies and master mixed state.
                domain = top_group(page, 'domains')
                domain.locator('input[data-top-filter="domains"][value="Governance"]').uncheck()
                row_count(page, 4)
                expect(page.locator('.sidebar input[data-filter="domains"][value="Governance"]')).not_to_be_checked()
                for selector in ('.sidebar input[data-filter-all="domains"]',
                                 '.view-filters input[data-top-filter-all="domains"]'):
                    assert page.locator(selector).evaluate('(element) => element.indeterminate')
                sidebar_domain = page.locator('.sidebar details[data-group="domains"]')
                sidebar_domain.evaluate('(element) => {element.open = true}')
                sidebar_domain.locator('input[data-filter="domains"][value="Governance"]').check()
                row_count(page, 7)
                expect(domain.locator('input[data-top-filter="domains"][value="Governance"]')).to_be_checked()
                assert not domain.locator('input[data-top-filter-all="domains"]').evaluate(
                    '(element) => element.indeterminate')

                # Changing an option keeps the dropdown, focus and all scroll positions.
                entities = top_group(page, 'entities')
                entity = entities.locator('input[data-top-filter="entities"][value="Review Entity 20"]')
                page.locator('.sidebar').evaluate('(element) => {element.scrollTop = element.scrollHeight}')
                entity.scroll_into_view_if_needed()
                entity.focus()
                before = positions(entity)
                page.keyboard.press('Space')
                expect(entity).not_to_be_checked()
                after = positions(entity)
                assert after['focused'] and after['open'], after
                for key in ('page', 'inner', 'sidebar'):
                    assert abs(before[key] - after[key]) < 1, (key, before, after)
                page.keyboard.press('Space')
                expect(entity).to_be_checked()
                close_top_groups(page)

                # Legend toggles, sidebar and dashboard share exactly one scope.
                for button, scope in (
                    ('year-local', 'global'),
                    ('domain-local', 'all'),
                    ('domain-global', 'local'),
                    ('year-global', 'all'),
                ):
                    legend = page.locator(f'#budget-legend-{button}')
                    legend.scroll_into_view_if_needed()
                    legend.focus()
                    scroll_before = page.evaluate('window.scrollY')
                    legend.click()
                    row_count(page, 7)
                    amount(page, SCOPE_TOTALS[scope])
                    assert_scope(page, scope)
                    chart_amounts(page, scope)
                    assert legend.evaluate('(element) => document.activeElement === element')
                    scroll_after = page.evaluate('window.scrollY')
                    if button.startswith('domain-'):
                        assert scroll_before > 0, scroll_before
                        # Global-only hides the Local reconciliation cards; the
                        # browser clamps a saved offset to the shorter document.
                        maximum=page.evaluate('document.documentElement.scrollHeight-innerHeight')
                        assert abs(min(scroll_before,maximum)-scroll_after)<1, (button,scroll_before,scroll_after,maximum)
                    if scope != 'all':
                        # Keyboard activation of the sole active series is a no-op.
                        active = page.locator(f'#budget-legend-year-{scope}')
                        active.focus()
                        page.keyboard.press('Space')
                        amount(page, SCOPE_TOTALS[scope])
                        assert_scope(page, scope)
                for selector, scope in (('#sidebar-budget-scope', 'global'),
                                        ('[data-top-select="scope"]', 'local'),
                                        ('[data-top-select="scope"]', 'all')):
                    page.locator(selector).select_option(scope)
                    row_count(page, 7)
                    amount(page, SCOPE_TOTALS[scope])
                    assert_scope(page, scope)
                    chart_amounts(page, scope)

                # A legend selection is kept across views/presenter and reaches PPT.
                page.locator('#budget-legend-year-local').click()
                with page.expect_request(lambda request: request.method == 'POST'
                                         and request.url.endswith('/api/presentation')) as request_event:
                    with page.expect_download() as ppt_download:
                        page.locator('[data-action="pptx"]').click()
                payload = request_event.value.post_data_json
                assert payload['scope'] == payload['filters']['scope'] == 'global', payload
                assert len(payload['rowKeys']) == 7
                ppt_path = root / 'global-legend.pptx'
                ppt_download.value.save_as(ppt_path)
                deck = Presentation(str(ppt_path))
                charts = [shape.chart for slide in deck.slides for shape in slide.shapes if shape.has_chart]
                assert charts and all([series.name for series in chart.series] == ['Global'] for chart in charts)
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as csv_download:
                    page.locator('[data-action="csv"]').click()
                csv_path = root / 'global-legend.csv'
                csv_download.value.save_as(csv_path)
                with csv_path.open(encoding='utf-8-sig', newline='') as file:
                    reader = csv.DictReader(file, delimiter=';')
                    assert reader.fieldnames[-2:] == ['Budget visualizzato', 'Budget visualizzato EUR']
                    csv_rows = list(reader)
                assert {entry['Foglio'] + ':' + entry['Riga Excel'] for entry in csv_rows} == set(payload['rowKeys'])
                assert len(csv_rows) == 7
                assert all(entry['Budget visualizzato'] == 'Global' for entry in csv_rows)
                assert sum(float(entry['Budget visualizzato EUR'] or 0) for entry in csv_rows) == 7600
                insurance = next(entry for entry in csv_rows if entry['Remediation'] == 'Review insurance')
                assert insurance['Budget visualizzato EUR'] == ''
                for view in VIEWS:
                    page.locator(f'.view-tabs [data-view="{view}"]').click()
                    row_count(page, 7)
                    amount(page, 7600)
                    assert_scope(page, 'global')
                page.locator('.view-tabs [data-view="overview"]').click()
                page.locator('[data-action="presentation"]').click()
                amount(page, 7600)
                assert_scope(page, 'global')
                page.keyboard.press('Escape')
                page.locator('.sidebar').evaluate('(element) => {element.scrollTop = 0}')
                page.evaluate('window.scrollTo(0, 0)')
                page.screenshot(path='/tmp/data-visualization-tool-budget-legends-normal.png', full_page=True)
                page.locator('#budget-legend-year-local').click()
                assert_scope(page, 'all')

                # Presentation restores search, budget scope and Local filters too.
                page.locator('[data-action="presentation"]').click()
                expect(page.locator('.sidebar')).not_to_be_visible()
                expect(bar).to_be_visible()
                expect(page.locator('#presentation-search')).to_be_visible()
                page.locator('#presentation-search').fill('Review backup')
                row_count(page, 1)
                page.locator('[data-top-select="scope"]').select_option('global')
                amount(page, 2000)
                assert_scope(page, 'global')
                page.locator('[data-top-select="scope"]').select_option('local')
                amount(page, 1000)
                assert_scope(page, 'local')
                page.locator('[data-top-select="scope"]').select_option('all')
                page.locator('[data-top-select="localBudget"]').select_option('zero')
                row_count(page, 0)
                page.locator('[data-top-select="localBudget"]').select_option('positive')
                row_count(page, 1)
                for view in VIEWS:
                    page.locator(f'.view-tabs [data-view="{view}"]').click()
                    expect(bar).to_be_visible()
                    row_count(page, 1)

                # Closing a dropdown with Escape does not leave presentation.
                owners = top_group(page, 'owners')
                page.keyboard.press('Escape')
                assert not owners.evaluate('(element) => element.open')
                assert page.locator('body').evaluate('(element) => element.classList.contains("presentation")')
                master = top_group(page, 'years').locator('input[data-top-filter-all="years"]')
                master.focus()
                page.keyboard.press('Space')
                row_count(page, 0)
                assert master.evaluate('(element) => document.activeElement === element')
                assert top_group(page, 'years', open_group=False).evaluate('(element) => element.open')
                page.keyboard.press('Space')
                row_count(page, 1)
                page.keyboard.press('Escape')
                page.keyboard.press('Escape')
                assert not page.locator('body').evaluate('(element) => element.classList.contains("presentation")')

                # Exported HTML carries the same controls and needs no HTTP requests.
                page.locator('.view-tabs [data-view="overview"]').click()
                page.locator('#budget-legend-year-local').click()
                amount(page, 2000)
                assert_scope(page, 'global')
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as download:
                    page.locator('[data-action="html"]').click()
                html = root / 'presentation-filters-offline.html'
                download.value.save_as(html)
                offline = browser.new_page(viewport={'width': 1440, 'height': 1100})
                offline.on('pageerror', lambda error: errors.append(str(error)))
                offline.route('http**/*', lambda route: (offline_requests.append(route.request.url), route.abort()))
                offline.set_content(html.read_text())
                row_count(offline, 1)
                amount(offline, 2000)
                assert_scope(offline, 'global')
                offline.locator('#budget-legend-domain-local').click()
                amount(offline, 3000)
                assert_scope(offline, 'all')
                offline.locator('#budget-legend-year-global').click()
                amount(offline, 1000)
                assert_scope(offline, 'local')
                offline.locator('[data-action="presentation"]').click()
                offline.locator('#presentation-search').fill('Review alignment')
                offline.locator('[data-top-select="scope"]').select_option('global')
                row_count(offline, 1)
                amount(offline, 3000)
                master = top_group(offline, 'years').locator('input[data-top-filter-all="years"]')
                master.uncheck()
                row_count(offline, 0)
                master.check()
                row_count(offline, 1)
                assert not offline_requests, offline_requests
                offline.close()

                # Dropdowns fit a phone viewport and remain interactive in presentation.
                page.set_viewport_size({'width': 390, 'height': 844})
                page.locator('[data-action="presentation"]').click()
                for field in ('priority', 'entities'):
                    group = top_group(page, field)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    option = group.locator('input[data-top-filter]').first
                    expect(option).to_be_visible()
                    bounds = option.bounding_box()
                    assert bounds and bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= 390, bounds
                close_top_groups(page)

                page.set_viewport_size({'width': 1440, 'height': 1100})
                page.locator('.view-tabs [data-view="overview"]').click()
                page.locator('#presentation-search').fill('')
                page.locator('[data-top-select="scope"]').select_option('all')
                page.locator('[data-top-select="localBudget"]').select_option('all')
                row_count(page, 7)
                page.locator('[data-top-select="scope"]').select_option('local')
                top_group(page, 'years')
                page.screenshot(path='/tmp/data-visualization-tool-presentation-filters.png', full_page=True)
                page.emulate_media(media='print')
                expect(bar).not_to_be_visible()
                expect(page.locator('.kpi-grid')).to_be_visible()
                page.emulate_media(media='screen')
                expect(bar).to_be_visible()

                # The selected series determines ordering and the largest annual bar.
                store.create(ranking_workbook(), 'ranking.xlsx', 'Ranking project')
                page.reload()
                row_count(page, 7)
                assert_scope(page, 'all')
                expect(page.locator('.domain-row').first).to_have_attribute('data-domain', 'Governance')
                expect(page.locator('.owner-row').first).to_have_attribute('data-owner', 'Supplier A')
                page.locator('[data-top-select="scope"]').select_option('global')
                expect(page.locator('.domain-row').first).to_have_attribute('data-domain', 'Security')
                expect(page.locator('.owner-row').first).to_have_attribute('data-owner', 'Supplier B')
                assert page.locator('.annual-chart [data-year="2028"] .stacked-bar').evaluate(
                    '(element) => parseFloat(element.style.height)') == 100
                page.locator('#budget-legend-domain-local').click()
                assert_scope(page, 'all')
                page.locator('#budget-legend-year-global').click()
                assert_scope(page, 'local')
                expect(page.locator('.domain-row').first).to_have_attribute('data-domain', 'Governance')
                expect(page.locator('.owner-row').first).to_have_attribute('data-owner', 'Supplier A')
                assert page.locator('.annual-chart [data-year="2027"] .stacked-bar').evaluate(
                    '(element) => parseFloat(element.style.height)') == 100
                row_count(page, 7)
                assert not errors, errors
                browser.close()
                print('PRESENTATION FILTERS PASS: placement, bidirectional sync, all/none/mixed, '
                      'focus and scroll, presentation search/budget, all views, Escape, '
                      'shared Global/Local legends, chart totals/scales, PPT and CSV scope, '
                      'offline export without network, mobile and print')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    main()
