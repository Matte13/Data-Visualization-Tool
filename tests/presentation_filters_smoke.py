"""Browser checks for synchronized presentation filters using fictional data."""
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
from fixtures import make_workbook
from playwright.sync_api import expect, sync_playwright


FIELDS = ('sheets', 'years', 'domains', 'owners', 'entities', 'nis2', 'priority')
VIEWS = ('overview', 'map', 'owner-map', 'table', 'countries')


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

                # Presentation restores search, budget scope and Local filters too.
                page.locator('[data-action="presentation"]').click()
                expect(page.locator('.sidebar')).not_to_be_visible()
                expect(bar).to_be_visible()
                expect(page.locator('#presentation-search')).to_be_visible()
                page.locator('#presentation-search').fill('Review backup')
                row_count(page, 1)
                page.locator('[data-top-select="scope"]').select_option('global')
                amount(page, 2000)
                page.locator('[data-top-select="scope"]').select_option('local')
                amount(page, 1000)
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
                page.locator('[data-top-select="localBudget"]').select_option('all')
                row_count(page, 7)
                top_group(page, 'years')
                page.screenshot(path='/tmp/data-visualization-tool-presentation-filters.png', full_page=True)
                page.emulate_media(media='print')
                expect(bar).not_to_be_visible()
                expect(page.locator('.kpi-grid')).to_be_visible()
                page.emulate_media(media='screen')
                expect(bar).to_be_visible()
                assert not errors, errors
                browser.close()
                print('PRESENTATION FILTERS PASS: placement, bidirectional sync, all/none/mixed, '
                      'focus and scroll, presentation search/budget, all views, Escape, '
                      'offline export without network, mobile and print')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == '__main__':
    main()
