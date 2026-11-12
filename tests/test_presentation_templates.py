"""Source artwork, dates, randomized ordering and fixed closing are retained."""
from datetime import datetime, timezone
from io import BytesIO
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pptx import Presentation
from pptx.oxml.ns import qn
from app.presentation import create_presentation
from app.presentation_templates import TEMPLATE_PATH, BACKGROUND_PATH, export_date
from test_presentation import report_fixture, titles


class TemplateExportTests(unittest.TestCase):
    def test_source_designs_once_with_current_date_and_exact_closing(self):
        source=Presentation(TEMPLATE_PATH)
        deck=Presentation(BytesIO(create_presentation(report_fixture())))
        dividers=[slide for slide in deck.slides if any(shape.name=='dvt-export-date' for shape in slide.shapes)]
        self.assertEqual(len(dividers),4)
        self.assertEqual({sh.name for slide in dividers for sh in slide.shapes if sh.name.startswith('dvt-separator-background-')},
                         {f'dvt-separator-background-{i}' for i in range(1,5)})
        for slide in dividers:
            date=next(shape.text for shape in slide.shapes if shape.name=='dvt-export-date')
            self.assertEqual(date,datetime.now(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y'))
            picture=next(sh for sh in slide.shapes if sh.name.startswith('dvt-separator-background-'))
            design=int(picture.name.rsplit('-',1)[1])
            self.assertEqual(picture.image.blob,(BACKGROUND_PATH/f'separator-{design:02}.png').read_bytes())
        closing=next(sh for sh in deck.slides[-1].shapes if sh.name=='dvt-closing-background')
        self.assertEqual(closing.image.blob,(BACKGROUND_PATH/'closing.png').read_bytes())
        self.assertEqual(len(deck.slide_masters),1)
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
        a=[next(sh.name for sh in s.shapes if sh.name.startswith('dvt-separator-background-')) for s in first.slides if any(sh.name=='dvt-export-date' for sh in s.shapes)]
        b=[next(sh.name for sh in s.shapes if sh.name.startswith('dvt-separator-background-')) for s in second.slides if any(sh.name=='dvt-export-date' for sh in s.shapes)]
        self.assertEqual(a,list(reversed(b)))

    def test_windows_without_timezone_database_still_exports_with_rome_date(self):
        with patch('app.presentation_templates.ZoneInfo',side_effect=ZoneInfoNotFoundError('Europe/Rome')):
            for instant,expected in [(datetime(2026,1,1,23,30,tzinfo=timezone.utc),'02/01/2026'),
                                     (datetime(2026,7,1,22,30,tzinfo=timezone.utc),'02/07/2026'),
                                     (datetime(2026,3,29,0,30,tzinfo=timezone.utc),'29/03/2026'),
                                     (datetime(2026,10,25,23,30,tzinfo=timezone.utc),'26/10/2026')]:
                self.assertEqual(export_date(instant),expected)
            deck=Presentation(BytesIO(create_presentation(report_fixture())))
            self.assertLessEqual(len(deck.slides),15)
            self.assertEqual(sum(any(sh.name=='dvt-export-date' for sh in slide.shapes) for slide in deck.slides),4)
