"""Browser reconciliation checks using a fictional, semantically classified Excel."""
import csv
from io import StringIO
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from app.budget_breakdown import budget_breakdown
from app.presentation_data import build_presentation_data
from app.server import ExplorerServer, WorkbookStore
from fixtures import make_semantic_workbook
from playwright.sync_api import expect, sync_playwright
from pptx import Presentation


def expected_rows(document, selection=None, sheets=None):
    """Independent membership selection, preserving unresolved source records."""
    return [row for row in document['rows']
            if (sheets is None or row['sheet'] in sheets)
            and (selection is None or row['allocationStatus'] != 'mapped'
                 or any(a['entityId'] in selection for a in row['allocations']))]


def check_calculators(page, document, selection=None, sheets=None):
    rows = expected_rows(document, selection, sheets)
    expected = budget_breakdown(rows, document['entities'], selection)
    actual = page.evaluate('''input => window.RemediationModel.budgetBreakdown(
        input.rows, input.entities, input.selection)''',
        {'rows': rows, 'entities': document['entities'], 'selection': selection})
    for key in ('globalBase', 'globalOt', 'global', 'localBase', 'localOt', 'localTotal',
                'unallocatedBase', 'unallocatedOt', 'unallocated', 'unresolvedSource',
                'missingGlobal', 'missingLocal'):
        assert math.isclose(actual[key], expected[key], abs_tol=.000001), (key, actual, expected)
    assert actual['classificationAvailable'] == expected['classificationAvailable']
    by_category = {item['id']: item for item in actual['categories']}
    for item in expected['categories']:
        for key in ('entityCount', 'base', 'ot', 'total', 'missing'):
            assert math.isclose(by_category[item['id']][key], item[key], abs_tol=.000001), (item['id'],key)
    return expected


def euro(page, amount):
    return page.evaluate('value => window.RemediationModel.money(value)', amount)


def assert_category_cards(page, expected):
    for item in expected['categories']:
        card = page.locator(f'.budget-category[data-local-category="{item["id"]}"]')
        if not item['entityCount']:
            expect(card).to_have_count(0)
            continue
        expect(card).to_be_visible()
        for key in ('base', 'ot', 'total'):
            expect(card.locator(f'[data-budget-part="{key}"]')).to_have_text(euro(page,item[key]))


def open_top(page, field):
    group = page.locator(f'.view-filters [data-top-group="{field}"]')
    if not group.evaluate('(element) => element.open'):
        group.locator('summary').click()
    return group


def reset(page):
    page.locator('.view-filters [data-action="reset"]').click()


def select_entity(page, identifier):
    group = open_top(page,'entities')
    group.locator('[data-top-filter-all="entities"]').uncheck()
    group.locator(f'[data-top-filter="entities"][value="{identifier}"]').check()


def main():
    with tempfile.TemporaryDirectory(prefix='dvt-semantic-browser-') as directory:
        root = Path(directory)
        shutil.copytree(ROOT/'web',root/'web')
        source = make_semantic_workbook(name_prefix='Semantic')
        store = WorkbookStore(root)
        created = store.create(source,'semantic.xlsx','Semantic project')
        identifier = created['project']['id']
        document = store.snapshot(identifier)
        server = ExplorerServer(('127.0.0.1',0),store)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        address = f'http://127.0.0.1:{server.server_port}'
        errors, offline_requests, presentations = [], [], []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),
                    args=['--no-sandbox'])
                page = browser.new_page(viewport={'width':1440,'height':1100})
                page.on('pageerror',lambda error: errors.append(str(error)))
                def record_request(request):
                    if request.url.endswith('/api/presentation'):
                        presentations.append(request.post_data_json)
                page.on('request',record_request)
                page.goto(address)
                expect(page.locator('.budget-reconciliation')).to_be_visible()
                assert page.locator('.view-filters').evaluate('''element => Boolean(
                    element.compareDocumentPosition(document.querySelector('.kpi-grid'))
                    & Node.DOCUMENT_POSITION_FOLLOWING)''')
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(page,11090))
                expect(page.locator('.kpi-value').nth(3)).to_have_text('07')
                expected = check_calculators(page,document)
                assert expected['globalBase']==6400 and expected['globalOt']==1200
                assert expected['localBase']==3190 and expected['localOt']==300
                assert expected['unallocated']==810
                counts={item['id']:item['entityCount'] for item in expected['categories']}
                assert counts['complete-ot']==6 and counts['complete']==7 and counts['business']==8
                assert_category_cards(page,expected)
                expect(page.locator('.budget-residual')).to_contain_text(euro(page,810))

                # Owner is a display alias; branding and the uploaded bytes are preserved.
                assert any(row['owner']=='Advisor' and row['sourceOwner'].strip().casefold()=='kpmg'
                           for row in document['rows'])
                owner_group=open_top(page,'owners')
                expect(owner_group.locator('[data-top-filter="owners"][value="Advisor"]')).to_be_checked()
                expect(owner_group.locator('[data-top-filter="owners"][value="KPMG"]')).to_have_count(0)
                assert page.locator('.brand').get_attribute('aria-label').startswith('KPMG')
                assert page.request.get(address+'/api/source?projectId='+identifier).body()==source
                page.locator('.view-tabs [data-view="overview"]').click()

                # OT is a selectable delta, not another copy of Complete's base cost.
                sheets=open_top(page,'sheets')
                sheets.locator('[data-top-filter="sheets"][value="OT"]').uncheck()
                expect(page.locator('.kpi-value').nth(3)).to_have_text('05')
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(page,9590))
                without_ot=check_calculators(page,document,sheets=['Remediations'])
                assert without_ot['globalOt']==0 and without_ot['localOt']==0
                assert_category_cards(page,without_ot)
                sheets.locator('[data-top-filter="sheets"][value="OT"]').check()
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(page,11090))

                # One Business entity receives only its own known amounts; ambiguous rows stay unresolved.
                business=next(entity['id'] for entity in document['entities'] if entity['localCategory']=='business')
                select_entity(page,business)
                # Global stays group-wide, including rows whose explicit BO share is zero.
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(page,6410))
                selected=check_calculators(page,document,[business])
                assert selected['localBase']==10 and selected['localOt']==0
                assert selected['unallocated']==0 and selected['unresolvedSource']==810
                assert_category_cards(page,selected)
                reset(page)

                # The existing Global/Local scope applies to reconciliation presentation too.
                page.locator('[data-top-select="scope"]').select_option('global')
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(page,7600))
                expect(page.locator('.budget-category')).to_have_count(0)
                page.locator('[data-top-select="scope"]').select_option('local')
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(page,3490))
                assert_category_cards(page,expected)
                page.locator('[data-top-select="scope"]').select_option('all')

                # Actual downloads contain the same source selection and authoritative reconciliation.
                with page.expect_download(timeout=30000) as download:
                    page.locator('[data-action="pptx"]').click()
                path=root/'semantic.pptx';download.value.save_as(path)
                deck=Presentation(str(path))
                assert len(deck.slides)<=15
                assert presentations and len(presentations[-1]['rowKeys'])==7
                report=build_presentation_data(document,presentations[-1])
                assert report['budgetBreakdown']==expected
                all_text='\n'.join(shape.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame)
                notes='\n'.join(slide.notes_slide.notes_text_frame.text for slide in deck.slides)
                assert 'Advisor' in all_text+'\n'+notes
                assert 'KPMG' in all_text  # Footer branding remains.
                assert 'globalOt' in notes and 'localOt' in notes and 'unallocated' in notes

                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as download:
                    page.locator('[data-action="csv"]').click()
                csv_file=root/'semantic.csv';download.value.save_as(csv_file)
                records=list(csv.DictReader(StringIO(csv_file.read_text(encoding='utf-8-sig')),delimiter=';'))
                assert len(records)==7 and any(row['Owner']=='Advisor' for row in records)
                advisor=next(row for row in records if row['Owner']=='Advisor')
                assert advisor['Owner nel file originale']==' KpMg '

                page.locator('[data-top-select="scope"]').select_option('local')
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as download:
                    page.locator('[data-action="html"]').click()
                html=root/'semantic-offline.html';download.value.save_as(html)
                offline=browser.new_page(viewport={'width':1280,'height':1000})
                offline.on('pageerror',lambda error: errors.append(str(error)))
                offline.route('http**/*',lambda route:(offline_requests.append(route.request.url),route.abort()))
                offline.set_content(html.read_text())
                expect(offline.locator('.budget-reconciliation')).to_be_visible()
                expect(offline.locator('.kpi-value').nth(0)).to_have_text(euro(offline,3490))
                assert_category_cards(offline,expected)
                offline.locator('[data-action="presentation"]').click()
                expect(offline.locator('.view-filters')).to_be_visible()
                select_entity(offline,business)
                expect(offline.locator('.kpi-value').nth(0)).to_have_text(euro(offline,10))
                assert_category_cards(offline,selected)
                offline.emulate_media(media='print')
                expect(offline.locator('.view-filters')).not_to_be_visible()
                expect(offline.locator('.budget-reconciliation')).to_be_visible()
                assert not offline_requests,offline_requests
                offline.close()

                page.set_viewport_size({'width':390,'height':844})
                page.locator('[data-action="presentation"]').click()
                expect(page.locator('.view-filters')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path='/tmp/data-visualization-tool-semantic-budgets.png',full_page=True)
                assert not errors,errors
                browser.close()
                print('SEMANTIC BUDGET PASS: top filters, category counts, independent JS/Python '
                      'reconciliation, one-time OT, unresolved duplicates, Advisor alias, source integrity, '
                      'entity selection, Global/Local, PPT/CSV/offline, presentation, mobile and print')
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':
    main()
