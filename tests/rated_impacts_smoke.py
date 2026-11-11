"""Latest impact schema in both maps, detail, CSV and offline export."""
import re,os,sys,tempfile,threading,shutil,csv
from pathlib import Path
from io import StringIO
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from app.server import WorkbookStore,ExplorerServer
from consolidated_fixtures import make_rated_impact_workbook
from playwright.sync_api import sync_playwright,expect


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);shutil.copytree(ROOT/'web',root/'web')
        store=WorkbookStore(root);store.create(make_rated_impact_workbook(),'latest.xlsx','Synthetic impacts')
        server=ExplorerServer(('127.0.0.1',0),store)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1920,'height':1080});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('.kpi-value').nth(0)).to_have_text('11.022 €')
                for view,path in [('risk-map',['2027','Capex','Governance','All Remediations:2']),('risk-first-map',['2027','Cyber','All Remediations:2']),('remediation-map',['2027','All Remediations:2','Cyber'])]:
                    page.locator(f'.view-tabs [data-view="{view}"]').click()
                    for step,value in enumerate(path):
                        node=page.locator(f'[data-risk-step="{step}"][data-risk-value="{value}"]')
                        node.scroll_into_view_if_needed();node.focus();page.keyboard.press('Space' if value.startswith('All ') else 'Enter')
                    expect(page.locator('[data-risk-detail="All Remediations:2"]')).to_contain_text(re.compile(r'Global 1K\s€ · Local 1,38K\s€'))
                    for kind,level,color in [('Reputational','Low','#32835c'),('Regulatory','High','#c64545'),('Economic','Medium','#b8840a'),('Operational','High','#c64545')]:
                        node=page.locator(f'.impact-node[data-risk-value="{kind}"]')
                        expect(node).to_contain_text(level)
                        assert '€' not in node.text_content()
                        assert node.evaluate('(e)=>e.style.getPropertyValue("--impact-color")')==color
                    page.locator('[data-risk-detail="All Remediations:2"]').focus();page.keyboard.press('Enter')
                    expect(page.locator('.detail-drawer')).to_contain_text('Reputational Impact')
                    expect(page.locator('.detail-drawer .risk-level-low')).to_have_text('Low')
                    page.locator('#close-detail').click()
                page.locator('[data-risk-step="2"][data-risk-value="Cyber"]').focus();page.keyboard.press('Enter')
                expect(page.locator('.map-col-label')).to_have_text(['01 / ANNO','02 / REMEDIATION','03 / RISK TYPE','04 / IMPACT TYPE'])
                page.locator('[data-risk-value="Regulatory"]').focus();page.keyboard.press('Enter')
                expect(page.locator('[data-risk-step="4"][data-risk-value="Capex"]')).to_have_count(1)
                for view,attribute in [('map','data-map-domain'),('owner-map','data-owner-map-domain')]:
                    page.locator(f'.view-tabs [data-view="{view}"]').click()
                    page.locator(f'[{attribute}="Governance"]').click()
                    expect(page.locator('[data-detail="All Remediations:2"]')).to_contain_text(re.compile(r'Global 1K\s€ · Local 1,38K\s€'))
                page.locator('.view-tabs [data-view="remediation-map"]').click()
                for action in ('csv','html'):
                    page.locator('[data-action="export-menu"]').click()
                    with page.expect_download() as transfer:page.locator(f'[data-action="{action}"]').click()
                    target=root/f'export.{action}';transfer.value.save_as(target)
                    if action=='csv':
                        rows=list(csv.DictReader(StringIO(target.read_text(encoding='utf-8-sig')),delimiter=';'))
                        assert rows[0]['Reputational Impact']=='Low'
                        assert rows[0]['Operational Impact']=='High'
                    else:
                        offline=browser.new_page();offline.set_content(target.read_text(),wait_until='load')
                        expect(offline.locator('.impact-node[data-risk-value="Regulatory"]')).to_contain_text('High')
                        offline.close()
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                assert not errors,errors
                browser.close()
        finally:server.shutdown();server.server_close()
    print('RATED IMPACTS PASS: maps, individual colors and levels, details, CSV, offline, mobile')

if __name__=='__main__':main()
