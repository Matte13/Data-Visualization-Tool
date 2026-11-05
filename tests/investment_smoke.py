"""Real browser drilldown and shared optional-field filters, synthetic data only."""
from pathlib import Path
import os,shutil,sys,tempfile,threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from app.server import WorkbookStore,ExplorerServer
from test_investment_fields import investment_workbook
from playwright.sync_api import sync_playwright,expect
from pptx import Presentation


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        shutil.copytree(Path(__file__).resolve().parents[1]/'web',root/'web')
        store=WorkbookStore(root)
        store.create(investment_workbook(),'synthetic.xlsx','Investments')
        server=ExplorerServer(('127.0.0.1',0),store)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1600,'height':1000})
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.locator('.view-tabs [data-view="risk-map"]').click()
                for step,value in enumerate(['2027','Capex','Cyber','Alto','Governance']):
                    node=page.locator(f'[data-risk-step="{step}"][data-risk-value="{value}"]')
                    node.scroll_into_view_if_needed()
                    node.focus();page.keyboard.press('Enter')
                leaf=page.locator('#view-content [data-detail="Remediations:4"]')
                expect(leaf).to_have_count(1)
                expect(page.locator('#view-content svg path[marker-end]')).to_have_count(6)
                leaf.click()
                expect(page.locator('.detail-drawer')).to_contain_text('Cyber')
                expect(page.locator('.detail-drawer')).to_contain_text('Alto')
                page.locator('#close-detail').click()
                group=page.locator('.view-filters [data-top-group="capexOpex"]')
                group.locator('summary').click()
                group.locator('[data-top-filter-all]').uncheck()
                group.locator('[data-top-filter][value="Capex"]').check()
                expect(page.locator('.kpi-value').nth(0)).to_have_text('2380 €')
                expect(page.locator('.sidebar [data-filter="capexOpex"][value="Capex"]')).to_be_checked()
                page.screenshot(path='/tmp/dvt-investment-map.png',full_page=True)
                group.locator('summary').click()
                with page.expect_download() as transfer:
                    page.locator('[data-action="pptx"]').click()
                deck=root/'filtered.pptx'
                transfer.value.save_as(deck)
                presentation=Presentation(deck)
                assert len(presentation.slides)<=15
                texts=' '.join(shape.text for slide in presentation.slides for shape in slide.shapes if shape.has_text_frame)
                notes=' '.join(slide.notes_slide.notes_text_frame.text for slide in presentation.slides)
                assert 'Capex' in notes,notes
                assert '2.380' in texts,texts
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as transfer:
                    page.locator('[data-action="html"]').click()
                offline=root/'offline.html'
                transfer.value.save_as(offline)
                offline_page=browser.new_page()
                offline_page.route('http://**/*',lambda route:route.abort())
                offline_page.route('https://**/*',lambda route:route.abort())
                offline_page.set_content(offline.read_text(),wait_until='load')
                expect(offline_page.locator('#view-content [data-detail="Remediations:4"]')).to_have_count(1)
                expect(offline_page.locator('.kpi-value').nth(0)).to_have_text('2380 €')
                offline_page.close()
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown();server.server_close()
    print('INVESTMENT MAP PASS: five drilldown levels, exact edges, keyboard, source detail, shared filters and budget totals')

if __name__=='__main__': main()
