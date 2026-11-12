"""The portable font/theme package must remain a valid editable Office document."""
from io import BytesIO
import struct
import unittest
from zipfile import ZipFile

from lxml import etree
from pptx import Presentation

from app.presentation_style import (STYLE_PATH, apply_presentation_style, NS_P, NS_A,
                                    NS_R, NS_REL, NS_CT, FONT_REL)


class PresentationStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(100000, 100000, 2000000, 500000).text = 'Original editable content'
        output = BytesIO(); presentation.save(output)
        cls.content = apply_presentation_style(output.getvalue())

    def test_fonts_are_referenced_without_binary_embedding(self):
        with ZipFile(BytesIO(self.content)) as package:
            self.assertIsNone(package.testzip())
            presentation = etree.fromstring(package.read('ppt/presentation.xml'))
            self.assertIsNone(presentation.get('embedTrueTypeFonts'))
            self.assertIsNone(presentation.find(f'{{{NS_P}}}embeddedFontLst'))
            self.assertFalse(any(name.startswith('ppt/fonts/') for name in package.namelist()))
            rels = etree.fromstring(package.read('ppt/_rels/presentation.xml.rels'))
            self.assertFalse(any(rel.get('Type') == FONT_REL for rel in rels))
            parsed = Presentation(BytesIO(self.content))
            self.assertEqual(parsed.slides[0].shapes[0].text, 'Original editable content')

    def test_opc_namespaces_are_canonical_and_resource_has_no_source_slides(self):
        with ZipFile(BytesIO(self.content)) as package, ZipFile(STYLE_PATH) as resource:
            content_types = etree.fromstring(package.read('[Content_Types].xml'))
            relationships = etree.fromstring(package.read('ppt/_rels/presentation.xml.rels'))
            self.assertEqual(content_types.nsmap.get(None), NS_CT)
            self.assertEqual(relationships.nsmap.get(None), NS_REL)
            self.assertFalse(any(name.startswith('ppt/slides/') for name in resource.namelist()))
            self.assertFalse(any(name.startswith('ppt/media/') for name in resource.namelist()))
            theme = etree.fromstring(package.read('ppt/theme/theme1.xml'))
            self.assertEqual(theme.find(f'.//{{{NS_A}}}majorFont/{{{NS_A}}}latin').get('typeface'), 'KPMG Bold')
            self.assertEqual(theme.find(f'.//{{{NS_A}}}minorFont/{{{NS_A}}}latin').get('typeface'), 'Arial')


if __name__ == '__main__':
    unittest.main()
