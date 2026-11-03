"""Real browser checks using fictional Excel data and a temporary project library."""
import copy
import csv
import json
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
from app.export import standalone_html
from fixtures import make_workbook
from playwright.sync_api import sync_playwright, expect


def main():
    with tempfile.TemporaryDirectory(prefix='atlas-browser-') as directory:
        tmp = Path(directory)
        shutil.copytree(ROOT / 'web', tmp / 'web')
        # No data/base.xlsx: a clean Git checkout must start with a real empty workspace.
        store = WorkbookStore(tmp)
        server = ExplorerServer(('127.0.0.1', 0), store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        address = f'http://127.0.0.1:{server.server_port}'
        alpha = make_workbook(name_prefix='Alpha')
        beta = make_workbook(seed=200, name_prefix='Beta', compact=True, include_ot=False)
        alpha_update = make_workbook(seed=50, name_prefix='Alpha')
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'])
                page = browser.new_page(viewport={'width':1440,'height':1100})
                errors, requests = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))

                def import_file(content, name, project_name=None, creating=True):
                    page.locator('[data-action="new-project"' + ']' if creating else '[data-action="import"]').click()
                    expect(page.locator('.project-dialog')).to_be_visible()
                    if creating:
                        page.locator('#project-name').fill(project_name)
                    page.locator('#project-file').set_input_files({'name':name,'mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':content})
                    page.locator('#submit-project').click()
                    expect(page.locator('.project-dialog')).to_have_count(0)
                    expect(page.locator('.source-line strong')).to_have_text(name)

                def project_id(name):
                    return page.locator('#project-select option').filter(has_text=name).get_attribute('value')

                def euro(value):
                    return page.evaluate('value => window.RemediationModel.money(value)', value)

                def activate(identifier, total):
                    page.locator('#project-select').select_option(identifier)
                    expect(page.locator('#project-select')).to_have_value(identifier)
                    expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(total))

                def reset_filters():
                    page.locator('.chip-row [data-action="reset"]').click()

                def fresh_offline(content):
                    offline = browser.new_page(viewport={'width':1280,'height':1000})
                    offline.on('pageerror', lambda error: errors.append(str(error)))
                    offline.route('http**/*', lambda route: (requests.append(route.request.url), route.abort()))
                    # Managed Chromium may forbid file://; run the exact self-contained document.
                    offline.set_content(content)
                    return offline

                page.goto(address)
                expect(page.locator('.welcome-page')).to_be_visible()
                assert page.request.get(address+'/api/projects').json()['projects'] == []
                import_file(alpha, 'alpha.xlsx', 'Alpha project')
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(9590))
                expect(page.locator('.kpi-value').nth(3)).to_have_text('05')
                first_id = project_id('Alpha project')
                # A failed catalog refresh must not undo a successful project save.
                def unavailable_catalog(route):
                    route.fulfill(status=503, content_type='application/json', body=json.dumps({'error':'Synthetic catalog failure'}))
                page.route('**/api/projects', unavailable_catalog)
                import_file(beta, 'beta.xlsx', 'Beta <"Cliente">')
                expect(page.locator('#toast')).to_contain_text('Il progetto è salvato')
                page.unroute('**/api/projects', unavailable_catalog)
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(7480))
                second_id = project_id('Beta <"Cliente">')
                expect(page.locator('#project-select option:checked')).to_have_text('Beta <"Cliente">')
                assert page.locator('#project-select img').count() == 0
                assert first_id != second_id
                expect(page.locator('.source-line')).to_contain_text('3 entità')
                expect(page.locator('input[data-filter="sheets"][value="OT"]')).to_have_count(0)
                activate(first_id, 9590)
                expect(page.locator('.source-line')).to_contain_text('21 entità')
                page.locator('#search').fill('backup')
                expect(page.locator('.kpi-value').nth(3)).to_have_text('01')
                activate(second_id, 7480)
                expect(page.locator('#search')).to_have_value('')
                expect(page.locator('.kpi-value').nth(3)).to_have_text('05')
                activate(first_id, 9590)
                # Updating one project preserves both the other project and its own initial import.
                import_file(alpha_update, 'alpha-updated.xlsx', creating=False)
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(9640))
                activate(second_id, 7480)
                expect(page.locator('.source-line strong')).to_have_text('beta.xlsx')
                activate(first_id, 9640)
                # Hold a reset response to prove project-changing actions are guarded while busy.
                held_reset = []
                def hold_reset(route):
                    held_reset.append(route)
                page.route('**/api/reset*', hold_reset)
                page.locator('[data-action="restore"]').click()
                expect(page.locator('#project-select')).to_be_disabled()
                expect(page.locator('[data-action="new-project"]')).to_be_disabled()
                expect(page.locator('[data-action="import"]')).to_be_disabled()
                expect(page.locator('[data-action="restore"]')).to_be_disabled()
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(9640))
                assert len(held_reset) == 1
                held_reset[0].continue_()
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(9590))
                expect(page.locator('#project-select')).to_be_enabled()
                expect(page.locator('#project-select')).to_have_value(first_id)
                page.unroute('**/api/reset*', hold_reset)
                expect(page.locator('.source-line strong')).to_have_text('alpha.xlsx')
                # Linked chart drilldown and exact source details.
                page.locator('[data-owner="Supplier B"]').click()
                expect(page.locator('.kpi-value').nth(3)).to_have_text('02')
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(3400))
                page.locator('tbody [data-detail]').first.click()
                expect(page.locator('.detail-drawer')).to_be_visible()
                expect(page.locator('.formula-section code')).to_contain_text('J')
                page.keyboard.press('Escape')
                expect(page.locator('.detail-drawer')).to_have_count(0)
                reset_filters()
                page.locator('details[data-group="entities"]').evaluate('(el) => {el.open = true}')
                page.locator('input[data-filter="entities"][value="Alpha Entity 01"]').check()
                expect(page.locator('details[data-group="entities"]')).to_have_attribute('open','')
                page.locator('[data-scope="local"]').click()
                page.locator('select[data-select="localBudget"]').select_option('zero')
                expect(page.locator('.kpi-value').nth(3)).to_have_text('01')
                reset_filters()
                page.locator('#search').fill('insurance')
                expect(page.locator('.kpi-value').nth(1)).to_have_text('Non stimato')
                page.locator('#search').fill('')
                expect(page.locator('.kpi-value').nth(3)).to_have_text('05')
                page.locator('details[data-group="entities"]').evaluate('(el) => {el.open = true}')
                page.locator('input[data-filter="entities"][value="Alpha Entity 01"]').check()
                expect(page.locator('.context-note')).to_contain_text('810')
                reset_filters()
                page.locator('input[data-filter="sheets"][value="OT"]').check()
                expect(page.locator('.kpi-value').nth(0)).to_have_text(euro(11090))
                expect(page.locator('.kpi-value').nth(3)).to_have_text('07')
                reset_filters()
                page.screenshot(path='/tmp/atlas-multiproject.png',full_page=True)
                # Mappa, PNG, and standalone export of only the active project.
                page.locator('.view-tabs [data-view="map"]').click()
                page.locator('[data-map-year="2028"]').click()
                page.locator('[data-map-domain="Security"]').click()
                with page.expect_download() as event:
                    page.locator('[data-action="png"]').click()
                event.value.save_as(tmp/'map.png')
                assert (tmp/'map.png').stat().st_size > 5000
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as event:
                    page.locator('[data-action="html"]').click()
                exported=tmp/'offline.html';event.value.save_as(exported)
                assert 'Beta Entity' not in exported.read_text()
                offline=fresh_offline(exported.read_text())
                expect(offline.locator('#concept-map')).to_be_visible()
                expect(offline.locator('.map-path')).to_contain_text('2028')
                expect(offline.locator('.map-path')).to_contain_text('Security')
                expect(offline.locator('#project-select')).to_have_count(0)
                expect(offline.locator('[data-action="new-project"]')).to_have_count(0)
                expect(offline.locator('[data-action="import"]')).to_have_count(0)
                offline.locator('.view-tabs [data-view="table"]').click()
                expect(offline.locator('tbody tr')).to_have_count(5)
                offline.locator('[data-action="export-menu"]').click()
                with offline.expect_download() as event:
                    offline.locator('[data-action="csv"]').click()
                csvpath=tmp/'rows.csv';event.value.save_as(csvpath)
                with csvpath.open(encoding='utf-8-sig',newline='') as file:
                    assert len(list(csv.reader(file,delimiter=';'))) == 6
                offline.close()
                cli_html=standalone_html(alpha,'alpha.xlsx')
                offline=fresh_offline(cli_html)
                expect(offline.locator('.kpi-value').nth(0)).to_have_text(euro(9590))
                offline.close()
                # Spreadsheet source strings cannot inject HTML/script into the exported view.
                hostile=copy.deepcopy(store.snapshot())
                hostile['rows'][0]['name']='</script><img src=x onerror="window.INJECTED=true">'
                start=cli_html.index('<script>window.ATLAS_DATA=');end=cli_html.index('</script>',start)
                safe_json=json.dumps(hostile,ensure_ascii=False).replace('<','\\u003c')
                hostile_html=cli_html[:start]+'<script>window.ATLAS_DATA='+safe_json+';'+cli_html[end:]
                offline=fresh_offline(hostile_html)
                expect(offline.locator('.kpi-value').nth(3)).to_have_text('05')
                offline.locator('.view-tabs [data-view="table"]').click()
                expect(offline.locator('.name-cell').first).to_contain_text('</script><img')
                assert offline.evaluate('window.INJECTED') is None
                offline.close()
                assert not requests,requests
                # Invalid upload remains transactional.
                response=page.request.post(address+'/api/workbook?filename=bad.xlsx',data=b'not an xlsx')
                assert response.status == 422
                assert page.request.get(address+'/api/workbook').json()['source']['filename']=='alpha.xlsx'
                # Persisted project selection and source contents survive a store restart.
                reloaded=WorkbookStore(tmp)
                assert reloaded.catalog()['activeProjectId']==first_id
                assert len(reloaded.catalog()['projects'])==2
                assert reloaded.source()==(alpha,'alpha.xlsx')
                reloaded.activate(second_id)
                assert reloaded.source()==(beta,'beta.xlsx')
                # Presentation and mobile controls.
                page.locator('[data-action="presentation"]').click()
                expect(page.locator('body')).to_have_class('presentation')
                page.keyboard.press('Escape')
                page.set_viewport_size({'width':390,'height':844})
                page.locator('[data-action="menu"]').click()
                page.locator('.sidebar [data-view="countries"]').click()
                expect(page.locator('.country-table')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path='/tmp/atlas-multiproject-mobile.png',full_page=True)
                page.set_viewport_size({'width':1440,'height':1100})
                page.locator('.view-tabs [data-view="overview"]').click()
                page.pdf(path='/tmp/atlas-multiproject.pdf',format='A4',landscape=True,print_background=True)
                assert not errors,errors
                browser.close()
                print('UI PASS: empty boot, multiple projects, different LE groups, saved catalog recovery, delayed reset guard, switch/update/reset isolation, filters, map/PNG, offline HTML, CSV, XSS, restart, mobile, PDF')
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':main()
