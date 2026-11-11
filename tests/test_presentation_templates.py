"""Source artwork, dates, randomized ordering and fixed closing are retained."""
from datetime import datetime
from io import BytesIO
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
from pptx import Presentation
from pptx.oxml.ns import qn
from app.presentation import create_presentation
from app.presentation_templates import TEMPLATE_PATH
from test_presentation import report_fixture, titles


class TemplateExportTests(unittest.TestCase):
    def test_source_designs_once_with_current_date_and_exact_closing(self):
        source=Presentation(TEMPLATE_PATH)
        deck=Presentation(BytesIO(create_presentation(report_fixture())))
        dividers=[slide for slide in deck.slides if any(shape.name=='dvt-export-date' for shape in slide.shapes)]
        self.assertEqual(len(dividers),4)
        self.assertEqual({slide.slide_layout.name for slide in dividers},{s.slide_layout.name for s in list(source.slides)[:-1]})
        for slide in dividers:
            date=next(shape.text for shape in slide.shapes if shape.name=='dvt-export-date')
            self.assertEqual(date,datetime.now(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y'))
            self.assertTrue(any(sh.shape_type==13 for sh in slide.slide_layout.shapes))
        self.assertEqual([sh.text for sh in deck.slides[-1].shapes if sh.has_text_frame],
                         [sh.text for sh in source.slides[-1].shapes if sh.has_text_frame])
        self.assertEqual(deck.slides[-1].slide_layout.name,source.slides[-1].slide_layout.name)
        self.assertLessEqual(len(deck.slides),15)
        # All r:id/r:embed references still point to real package relationships.
        for part in deck.part.package.iter_parts():
            if hasattr(part,'_element'):
                for node in part._element.iter():
                    for attr,value in node.attrib.items():
                        if attr in (qn('r:id'),qn('r:embed'),qn('r:link')):
                            self.assertIn(value,part.rels)

    def test_shuffle_controls_design_order_without_changing_section_order(self):
        with patch('app.presentation_templates.SystemRandom.shuffle',lambda self,items:None):
            first=Presentation(BytesIO(create_presentation(report_fixture())))
        with patch('app.presentation_templates.SystemRandom.shuffle',lambda self,items:items.reverse()):
            second=Presentation(BytesIO(create_presentation(report_fixture())))
        self.assertEqual(titles(first),titles(second))
        a=[s.slide_layout.name for s in first.slides if any(sh.name=='dvt-export-date' for sh in s.shapes)]
        b=[s.slide_layout.name for s in second.slides if any(sh.name=='dvt-export-date' for sh in s.shapes)]
        self.assertEqual(a,list(reversed(b)))
