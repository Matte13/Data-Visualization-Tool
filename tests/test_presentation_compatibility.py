"""Office-compatible chart IDs and lossless bounded notes for large exports."""
from io import BytesIO
import unittest
from zipfile import ZipFile
from lxml import etree
from pptx import Presentation
from pptx.oxml.ns import qn
from app.presentation import _notes, create_presentation
from test_presentation import report_fixture


class PresentationCompatibilityTests(unittest.TestCase):
    def test_large_notes_reopen_with_standard_readers_without_losing_characters(self):
        prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6])
        original='SYNTHETIC '*1_100_000+'\n'+('😀'*17000)+'\nFinal preserved line'
        _notes(slide,original)
        output=BytesIO();prs.save(output)
        with ZipFile(output) as package:
            for name in package.namelist():
                if name.endswith('.xml'):
                    root=etree.fromstring(package.read(name))
                    for node in root.iter(qn('a:t')):
                        self.assertLessEqual(len((node.text or '').encode('utf-16-le'))//2,32767)
        reopened=Presentation(BytesIO(output.getvalue()))
        self.assertEqual(reopened.slides[0].notes_slide.notes_text_frame.text,original)

    def test_axis_definitions_and_cross_references_are_valid_office_identifiers(self):
        for scope in ('all','global','local'):
            report=report_fixture();report['scope']=scope
            prs=Presentation(BytesIO(create_presentation(report)))
            for slide in prs.slides:
                for shape in slide.shapes:
                    if not shape.has_chart:continue
                    xml=shape.chart._chartSpace
                    ids=[int(n.get('val')) for n in xml.iter(qn('c:axId'))]
                    cross=[int(n.get('val')) for n in xml.iter(qn('c:crossAx'))]
                    self.assertTrue(ids)
                    self.assertTrue(all(0<value<=2147483647 for value in ids+cross))
                    self.assertTrue(set(cross).issubset(ids))

    def test_export_uses_only_standard_parts_and_no_embedded_font_programs(self):
        content=create_presentation(report_fixture())
        with ZipFile(BytesIO(content)) as package:
            names=package.namelist()
            self.assertFalse(any('dvt-template' in name or name.startswith('ppt/fonts/') for name in names))
            self.assertFalse(any(name.endswith('.fntdata') for name in names))
            self.assertTrue(any(name.startswith('ppt/media/') and name.endswith('.png') for name in names))
            pres=etree.fromstring(package.read('ppt/presentation.xml'))
            self.assertIsNone(pres.find(qn('p:embeddedFontLst')))
        deck=Presentation(BytesIO(content))
        self.assertEqual(len(deck.slide_masters),1)
        self.assertTrue(any(sh.has_chart for slide in deck.slides for sh in slide.shapes))
