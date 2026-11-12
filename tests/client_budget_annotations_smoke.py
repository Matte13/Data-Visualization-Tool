"""Client-facing views omit estimate badges while budgets stay unchanged."""
import os,sys,tempfile,threading,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from app.server import WorkbookStore,ExplorerServer
from fixtures import make_semantic_workbook
from playwright.sync_api import sync_playwright,expect


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);shutil.copytree(ROOT/'web',root/'web')
        store=WorkbookStore(root);source=make_semantic_workbook();store.create(source,'synthetic.xlsx','Client views')
        server=ExplorerServer(('127.0.0.1',0),store);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1600,'height':1000});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                original=page.locator('.kpi-value').all_text_contents()
                for presentation in (False,True):
                    if presentation:page.locator('[data-action="presentation"]').click()
                    for view in ('overview','map','owner-map','risk-map','risk-first-map','remediation-map','table','countries'):
                        page.locator(f'.view-tabs [data-view="{view}"]').click()
                        expect(page.locator('.budget-partial,.data-notice')).to_have_count(0)
                        text=page.locator('body').inner_text().lower()
                        for phrase in ('stime mancanti','stima mancante','stima incompleta','stime disponibili','importi disponibili','stima parziale','somma disponibile'):
                            assert phrase not in text,(view,phrase)
                        assert page.locator('.kpi-value').all_text_contents()==original
                page.locator('[data-action="presentation"]').click()
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as transfer:page.locator('[data-action="html"]').click()
                target=root/'offline.html';transfer.value.save_as(target)
                offline=browser.new_page();offline.set_content(target.read_text(),wait_until='load')
                expect(offline.locator('.budget-partial,.data-notice')).to_have_count(0)
                assert not errors,errors
                browser.close()
        finally:server.shutdown();server.server_close()
    print('CLIENT VIEWS PASS: estimate badges absent in every view, presentation and offline; budgets unchanged')

if __name__=='__main__':main()
