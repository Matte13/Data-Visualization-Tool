"""Fixed map scale, uniform source badges and presentation navigation."""
import os,sys,tempfile,threading,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from app.server import WorkbookStore,ExplorerServer
from consolidated_fixtures import make_rated_impact_workbook
from playwright.sync_api import sync_playwright,expect


def activate(page,selector):
    node=page.locator(selector);node.scroll_into_view_if_needed();node.click()


def check_badges(leaf,scope='CMA, WIFI & VA',budget='CAPEX'):
    expect(leaf.locator('[data-map-tag]')).to_have_count(3)
    expect(leaf.locator('.map-tags')).to_have_text([budget+scope+'NIS2'])
    geometry=leaf.evaluate('''node=>{
      const outer=node.querySelector(':scope > rect').getBBox();
      return [...node.querySelectorAll('.map-tag')].map(tag=>{
        const box=tag.querySelector('rect').getBBox(),text=tag.querySelector('text').getBBox();
        return {width:box.width,height:box.height,inside:box.x>=outer.x&&box.y>=outer.y&&box.x+box.width<=outer.x+outer.width&&box.y+box.height<=outer.y+outer.height,
          textFits:text.x>=box.x-1&&text.x+text.width<=box.x+box.width+1,kind:tag.dataset.mapTag,x:box.x,y:box.y,right:box.x+box.width,outerRight:outer.x+outer.width,outerTop:outer.y,outerBottom:outer.y+outer.height,font:getComputedStyle(tag.querySelector('text')).fontSize};
      });
    }''')
    for tag in geometry:
        if tag['kind'] in ('capex','opex'):assert abs(tag['right']-(tag['outerRight']-14))<.1 and tag['y']==tag['outerBottom']-22
        if tag['kind'] in ('ot','cma'):assert tag['y']==tag['outerTop']+10
    assert all(g['width']==90 and g['height']==16 and g['inside'] and g['textFits'] and g['font']=='8px' for g in geometry),geometry


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);shutil.copytree(ROOT/'web',root/'web')
        store=WorkbookStore(root);store.create(make_rated_impact_workbook(),'synthetic.xlsx','Map graphics')
        server=ExplorerServer(('127.0.0.1',0),store);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1920,'height':1080});errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('.sidebar-footer')).to_contain_text('© 2026 KPMG')
                assert 'Elaborazione locale' not in page.locator('.sidebar-footer').inner_text()
                assert 'Dati locali' not in page.locator('.topbar').inner_text()
                expect(page.locator('[data-top-filter="sheets"][value="Remediations"]').locator('..')).to_have_text('CMA')
                expect(page.locator('[data-filter="sheets"][value="Remediations"]').locator('..')).to_have_text('CMA')
                for presentation in (False,True):
                    if presentation:page.locator('[data-action="presentation"]').click()
                    for view,path in [
                        ('risk-map',['2027','Governance','All Remediations:2']),
                        ('risk-first-map',['2027','Cyber','All Remediations:2']),
                        ('remediation-map',['2027','All Remediations:2','Cyber'])]:
                        page.locator(f'.view-tabs [data-view="{view}"]').click()
                        initial=page.locator('.investment-map svg').evaluate('(svg)=>({width:svg.viewBox.baseVal.width,scale:svg.getScreenCTM().a})')
                        for step,value in enumerate(path):
                            activate(page,f'[data-risk-step="{step}"][data-risk-value="{value}"]')
                            current=page.locator('.investment-map svg').evaluate('(svg)=>({width:svg.viewBox.baseVal.width,scale:svg.getScreenCTM().a})')
                            assert current['width']==initial['width'] and abs(current['scale']-initial['scale'])<.0001,(view,initial,current)
                        assert 'CAPEX/OPEX' not in ' '.join(page.locator('.map-col-label').all_text_contents())
                        check_badges(page.locator('[data-risk-detail="All Remediations:2"]'))
                    for view,attribute in [('map','data-map-domain'),('owner-map','data-owner-map-domain')]:
                        page.locator(f'.view-tabs [data-view="{view}"]').click()
                        before=page.locator('.map-panel .map-scroll > svg').evaluate('(svg)=>svg.getScreenCTM().a')
                        activate(page,f'[{attribute}="Governance"]')
                        after=page.locator('.map-panel .map-scroll > svg').evaluate('(svg)=>svg.getScreenCTM().a')
                        assert abs(before-after)<.0001,(view,before,after)
                        check_badges(page.locator('[data-detail="All Remediations:2"]'))
                if os.environ.get('DVT_SCREENSHOT_DIR'):
                    shots=Path(os.environ['DVT_SCREENSHOT_DIR']);shots.mkdir(parents=True,exist_ok=True)
                    page.locator('[data-detail="All Remediations:2"]').screenshot(path=str(shots/'badges.png'))
                    page.locator('.topbar').screenshot(path=str(shots/'header.png'))
                logo=page.locator('.presentation-logo')
                expect(logo).to_be_visible()
                assert logo.get_attribute('src').startswith('data:image/png;base64,')
                assert logo.evaluate('(img)=>img.complete&&img.naturalWidth>0')
                assert page.locator('.topbar').bounding_box()['height']==54
                assert logo.bounding_box()['height']==28
                # Scope labels change only the UI; internal source identifiers stay intact.
                group=page.locator('[data-top-group="sheets"]');group.locator('summary').click()
                group.locator('[data-top-filter][value="Remediations"]').uncheck()
                page.locator('.view-tabs [data-view="risk-map"]').click()
                for step,value in enumerate(['2027','Security','All Remediations:5']):activate(page,f'[data-risk-step="{step}"][data-risk-value="{value}"]')
                check_badges(page.locator('[data-risk-detail="All Remediations:5"]'),'OT','OPEX')
                page.locator('[data-action="presentation"]').click()
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as transfer:page.locator('[data-action="html"]').click()
                target=root/'offline.html';transfer.value.save_as(target)
                offline=browser.new_page();offline.route('http://**/*',lambda route:route.abort());offline.route('https://**/*',lambda route:route.abort())
                offline.set_content(target.read_text(),wait_until='load')
                check_badges(offline.locator('[data-risk-detail="All Remediations:5"]'),'OT','OPEX')
                offline.locator('[data-action="presentation"]').click()
                expect(offline.locator('.presentation-logo')).to_be_visible()
                assert offline.locator('.presentation-logo').evaluate('(img)=>img.complete&&img.naturalWidth>0')
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                assert not errors,errors
                browser.close()
        finally:server.shutdown();server.server_close()
    print('MAP GRAPHICS PASS: stable scale, uniform badges, NIS2, CMA/OT filters, PNG logo, unchanged header, footer, offline and mobile')

if __name__=='__main__':main()
