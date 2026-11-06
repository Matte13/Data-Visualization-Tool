"""Real browser drilldown and shared optional-field filters, synthetic data only."""
from pathlib import Path
import os,shutil,sys,tempfile,threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from app.server import WorkbookStore,ExplorerServer
from test_investment_fields import investment_workbook
from test_workbook import edited_cell
from playwright.sync_api import sync_playwright,expect
from pptx import Presentation


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        shutil.copytree(Path(__file__).resolve().parents[1]/'web',root/'web')
        store=WorkbookStore(root)
        content=edited_cell(investment_workbook(),1,'A2',text='Italia - ITF')
        content=edited_cell(content,1,'A3',text='Paesi Bassi & Belgio')
        store.create(content,'synthetic.xlsx','Investments')
        server=ExplorerServer(('127.0.0.1',0),store)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1600,'height':1000})
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                for field in ('capexOpex','risk','impact'):
                    expect(page.locator(f'[data-top-filter="{field}"][value="Non specificato"]')).to_have_count(0)
                    expect(page.locator(f'[data-filter="{field}"][value="Non specificato"]')).to_have_count(0)
                expect(page.locator('.kpi-value').nth(0)).to_have_text('11.090 €')
                page.locator('.view-tabs [data-view="risk-map"]').click()
                expect(page.locator('.investment-map [role="status"]')).to_contain_text('5 righe escluse')
                expect(page.locator('[data-risk-value="Non specificato"]')).to_have_count(0)
                for step,value in enumerate(['2027','Capex','Governance']):
                    node=page.locator(f'[data-risk-step="{step}"][data-risk-value="{value}"]')
                    node.scroll_into_view_if_needed()
                    node.focus();page.keyboard.press('Enter')
                leaf=page.locator('#view-content [data-risk-detail="Remediations:4"]')
                expect(leaf).to_have_count(1)
                expect(leaf).to_have_class('map-node leaf')
                expect(leaf.locator('rect')).to_have_attribute('width','440')
                leaf.click()
                expect(page.locator('.detail-drawer')).to_contain_text('Cyber')
                expect(page.locator('.detail-drawer')).to_contain_text('Alto')
                for code in ('it','nl','be'):
                    expect(page.locator(f'.allocation-list [data-country-code="{code}"]')).to_have_count(1)
                page.locator('#close-detail').click()
                page.locator('[data-risk-step="4"][data-risk-value="Cyber"]').click()
                expect(page.locator('[data-risk-step="5"][data-risk-value="Alto"]')).to_have_count(1)
                for view in ('map','owner-map'):
                    page.locator(f'.view-tabs [data-view="{view}"]').click()
                    attribute='data-map-domain' if view=='map' else 'data-owner-map-domain'
                    page.locator(f'[{attribute}="Governance"]').click()
                    page.locator('#view-content [data-detail="Remediations:4"]').click()
                    expect(page.locator('.allocation-list [data-country-code="it"]')).to_have_count(1)
                    page.locator('#close-detail').click()
                page.locator('.view-tabs [data-view="risk-map"]').click()
                page.set_viewport_size({'width':2560,'height':1440})
                page.locator('[data-action="presentation"]').click()
                for view in ('map','owner-map','risk-map'):
                    page.locator(f'.view-tabs [data-view="{view}"]').click()
                    geometry=page.locator('.map-panel').evaluate('''panel=>{
                      const box=panel.getBoundingClientRect(),scroll=panel.querySelector('.map-scroll');
                      const svg=scroll.querySelector('svg').getBoundingClientRect();
                      return {left:box.left,right:innerWidth-box.right,overflow:scroll.scrollWidth-scroll.clientWidth,svg:svg.width,available:scroll.clientWidth};
                    }''')
                    assert geometry['left']<=20 and geometry['right']<=20,geometry
                    assert geometry['overflow']<=1 and geometry['svg']<=geometry['available']+1,geometry
                page.locator('[data-action="presentation"]').click()
                page.set_viewport_size({'width':1600,'height':1000})
                group=page.locator('.view-filters [data-top-group="capexOpex"]')
                group.locator('summary').click()
                group.locator('[data-top-filter-all]').uncheck()
                group.locator('[data-top-filter][value="Capex"]').check()
                expect(page.locator('.kpi-value').nth(0)).to_have_text('2380 €')
                expect(page.locator('.sidebar [data-filter="capexOpex"][value="Capex"]')).to_be_checked()
                group.locator('[data-top-filter-all]').check()
                expect(page.locator('.kpi-value').nth(0)).to_have_text('11.090 €')
                group.locator('[data-top-filter-all]').uncheck()
                expect(page.locator('.kpi-value').nth(3)).to_have_text('00')
                group.locator('[data-top-filter][value="Capex"]').check()
                expect(page.locator('.kpi-value').nth(0)).to_have_text('2380 €')
                page.screenshot(path='/tmp/dvt-investment-map.png',full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                expect(page.locator('.investment-map')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.set_viewport_size({'width':1600,'height':1000})
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
                expect(offline_page.locator('#view-content [data-risk-detail="Remediations:4"]')).to_have_count(1)
                expect(offline_page.locator('.kpi-value').nth(0)).to_have_text('2380 €')
                offline_page.close()
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown();server.server_close()
    print('INVESTMENT MAP PASS: five drilldown levels, exact edges, keyboard, source detail, shared filters and budget totals')

if __name__=='__main__': main()
