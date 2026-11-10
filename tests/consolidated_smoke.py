"""Consolidated attributes and note popup, verified using fictional workbook data."""
import csv
from io import StringIO
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from app.server import WorkbookStore,ExplorerServer
from consolidated_fixtures import make_consolidated_workbook
from test_workbook import edited_cell
from playwright.sync_api import sync_playwright,expect
from pptx import Presentation


def group(page,field):
    element=page.locator(f'.view-filters [data-top-group="{field}"]')
    if not element.evaluate('(e)=>e.open'):element.locator('summary').click()
    return element


def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);shutil.copytree(ROOT/'web',root/'web')
        source=edited_cell(make_consolidated_workbook(),4,'K1',text='2027 CMA Priority');source=edited_cell(source,4,'K3',text='N/A');store=WorkbookStore(root)
        project=store.create(source,'consolidated.xlsx','Synthetic consolidated')['project']['id']
        server=ExplorerServer(('127.0.0.1',0),store)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1920,'height':1080});errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('.kpi-value').nth(0)).to_have_text('11.022 €')
                expect(page.locator('.kpi-value').nth(3)).to_have_text('07')
                expect(page.locator('[data-top-filter="priority"][value="na"]')).to_have_count(1)
                expect(page.locator('[data-top-group="priority"] summary')).to_contain_text('2027 CMA Priority')
                for field in ('risk','impact','riskLevel'):
                    expect(page.locator(f'[data-top-filter="{field}"][value="Non specificato"]')).to_have_count(0)
                expect(page.locator('[data-top-filter="impact"][value="Economic"]')).to_have_count(1)
                expect(page.locator('[data-top-filter="impact"][value="High"]')).to_have_count(0)
                page.locator('.view-tabs [data-view="risk-map"]').click()
                page.locator('[data-risk-step="0"][data-risk-value="2027"]').click()
                page.locator('[data-risk-step="1"][data-risk-value="Capex"]').click()
                expect(page.locator('[role="dialog"]')).to_have_count(0)
                page.locator('[data-risk-step="2"][data-risk-value="Governance"]').click()
                page.locator('[data-risk-detail="All Remediations:2"]').click()
                expect(page.locator('.detail-drawer')).to_contain_text('Economic, Regulatory')
                expect(page.locator('.detail-drawer')).to_contain_text('Risk Level')
                expect(page.locator('.detail-drawer')).to_contain_text('If implemented on an automated platform.')
                expect(page.locator('.detail-drawer')).to_contain_text('Note Capex/Opex')
                page.locator('#close-detail').click()
                expect(page.locator('[data-risk-step="4"]')).to_have_count(2)
                expect(page.locator('[data-risk-step="5"]')).to_have_count(2)
                expect(page.locator('[data-risk-edge="remediation-impact"]')).to_have_count(2)
                expect(page.locator('[data-risk-edge="remediation-risk"]')).to_have_count(2)
                for view in ('map','owner-map','risk-map'):
                    page.locator(f'.view-tabs [data-view="{view}"]').click()
                    content=page.locator('#view-content')
                    texts=content.locator('.map-node text').all_text_contents()
                    assert not any('righe' in text.lower() or 'riga ' in text.lower() or 'Remediations' in text or 'Risk Level:' in text for text in texts),texts
                    paths=content.locator('.map-edge').evaluate_all('(nodes)=>nodes.map(node=>node.getAttribute("d"))')
                    assert paths and all('C' in path and not any(command in path for command in (' H',' V',' L')) for path in paths),paths
                page.locator('[data-action="presentation"]').click()
                page.locator('[data-risk-step="1"][data-risk-value="Opex"]').click()
                expect(page.locator('[role="dialog"]')).to_have_count(0)
                page.locator('[data-risk-step="2"][data-risk-value="Security"]').click()
                page.locator('[data-risk-detail="All Remediations:5"]').click()
                expect(page.locator('.detail-drawer .capex-note-section')).to_have_count(0)
                page.locator('#close-detail').click()
                page.locator('[data-action="presentation"]').click()
                page.locator('[data-risk-step="1"][data-risk-value="Capex"]').click()
                page.locator('[data-risk-step="2"][data-risk-value="Governance"]').click()
                page.locator('[data-risk-detail="All Remediations:2"]').click()
                page.locator('#close-detail').click()
                # OR within a field, AND between fields; budgets count source keys once.
                risk=group(page,'risk');risk.locator('[data-top-filter-all]').uncheck()
                risk.locator('[data-top-filter][value="Cyber"]').check()
                risk.locator('[data-top-filter][value="Compliance"]').check()
                expect(page.locator('.kpi-value').nth(3)).to_have_text('06')
                expect(page.locator('.kpi-value').nth(0)).to_have_text('10.142 €')
                impact=group(page,'impact');impact.locator('[data-top-filter-all]').uncheck()
                impact.locator('[data-top-filter][value="Economic"]').check()
                expect(page.locator('.kpi-value').nth(3)).to_have_text('02')
                level=group(page,'riskLevel');level.locator('[data-top-filter-all]').uncheck()
                level.locator('[data-top-filter][value="High"]').check()
                expect(page.locator('.kpi-value').nth(0)).to_have_text('2380 €')
                level.locator('summary').click()
                with page.expect_download() as transfer:page.locator('[data-action="pptx"]').click()
                target=root/'filtered.pptx';transfer.value.save_as(target)
                deck=Presentation(target);assert len(deck.slides)<=15
                notes=' '.join(slide.notes_slide.notes_text_frame.text for slide in deck.slides)
                assert 'riskTypes' in notes and 'impactTypes' in notes and 'automated platform' in notes
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as transfer:page.locator('[data-action="csv"]').click()
                target=root/'filtered.csv';transfer.value.save_as(target)
                records=list(csv.DictReader(StringIO(target.read_text(encoding='utf-8-sig')),delimiter=';'))
                assert len(records)==1 and records[0]['Risk Level']=='High'
                assert records[0]['Impact Type']=='Economic | Regulatory'
                assert records[0]['Foglio sorgente']=='All Remediations'
                page.locator('[data-action="export-menu"]').click()
                with page.expect_download() as transfer:page.locator('[data-action="html"]').click()
                target=root/'offline.html';transfer.value.save_as(target)
                offline=browser.new_page();offline.route('http://**/*',lambda route:route.abort());offline.route('https://**/*',lambda route:route.abort())
                offline.set_content(target.read_text(),wait_until='load')
                expect(offline.locator('.kpi-value').nth(0)).to_have_text('2380 €')
                offline.locator('[data-risk-detail="All Remediations:2"]').click()
                expect(offline.locator('.detail-drawer')).to_contain_text('automated platform')
                offline.keyboard.press('Escape')
                assert not errors,errors
                browser.close()
            assert store.source(project)[0]==source
        finally:server.shutdown();server.server_close()
    print('CONSOLIDATED PASS: multi-attribute budgets once, source tracing, independent edges, notes in remediation details/no popup/clean nodes/curved edges/presentation, CSV/PPT/offline, original bytes unchanged')

if __name__=='__main__':main()
