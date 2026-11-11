"""Import the supplied editable separator designs and fixed closing slide."""
from datetime import datetime
from pathlib import Path
from random import SystemRandom
from zoneinfo import ZoneInfo

from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.opc.packuri import PackURI
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from lxml import etree

TEMPLATE_PATH = Path(__file__).with_name('assets') / 'export-separators.pptx'


class ExportTemplates:
    def __init__(self, presentation):
        self.presentation = presentation
        self.source = Presentation(TEMPLATE_PATH)
        self.parts = {}
        self.order = list(range(len(self.source.slides) - 1))
        SystemRandom().shuffle(self.order)
        self.date = datetime.now(ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y')

    def _part(self, source):
        if source in self.parts:
            return self.parts[source]
        package = self.presentation.part.package
        name = PackURI(f'/ppt/dvt-template/part{len(self.parts)+1}{source.partname.ext and "."+source.partname.ext}')
        target = source.__class__.load(name, source.content_type, package, source.blob)
        self.parts[source] = target  # Masters/layouts have cyclic relationships.
        mapping = {}
        for rel in source.rels.values():
            if rel.reltype in (RT.NOTES_SLIDE, RT.TAGS):
                continue
            destination = rel.target_ref if rel.is_external else self._part(rel.target_part)
            mapping[rel.rId] = target.relate_to(destination, rel.reltype, is_external=rel.is_external)
        if hasattr(target, '_element'):
            for element in target._element.iter():
                for attribute, value in list(element.attrib.items()):
                    if attribute.startswith('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}') and value in mapping:
                        element.set(attribute, mapping[value])
        return target

    def _slide(self, index):
        # Each source design is used once, so imported slide parts stay distinct.
        part = self._part(self.source.slides[index].part)
        master = part.slide_layout.slide_master.part
        prs = self.presentation
        if not any(rel.reltype == RT.SLIDE_MASTER and rel.target_part is master for rel in prs.part.rels.values()):
            rid = prs.part.relate_to(master, RT.SLIDE_MASTER)
            masters = prs._element.sldMasterIdLst
            node = etree.SubElement(masters, qn('p:sldMasterId'))
            node.set('id', str(max(int(child.get('id')) for child in masters[:-1]) + 1))
            node.set(qn('r:id'), rid)
        for shape in part.slide_layout.shapes:
            for field in shape._element.iter(qn('a:fld')):
                if field.get('type') == 'slidenum':
                    for text in field.iter(qn('a:t')):
                        text.text = str(len(prs.slides) + 1)
        rid = prs.part.relate_to(part, RT.SLIDE)
        prs.slides._sldIdLst.add_sldId(rid)
        return part.slide

    def divider(self, title):
        slide = self._slide(self.order.pop())
        # The source's blank dividers inherit their artwork from the layout.
        # Use its original title/date region, leaving photographs and footer intact.
        title_box = slide.shapes.add_textbox(Inches(1.41), Inches(2.62), Inches(5.74), Inches(2.59))
        title_box.name = 'dvt-title'
        title_box.text = title
        title_box.text_frame.word_wrap = True
        paragraph = title_box.text_frame.paragraphs[0]
        paragraph.font.name = 'KPMG Bold'; paragraph.font.size = Pt(56 if len(title) < 25 else 44)
        paragraph.font.color.rgb = RGBColor(255, 255, 255)
        date_box = slide.shapes.add_textbox(Inches(1.41), Inches(5.52), Inches(5.74), Inches(.56))
        date_box.name = 'dvt-export-date'; date_box.text = self.date
        paragraph = date_box.text_frame.paragraphs[0]
        paragraph.font.name = 'Arial'; paragraph.font.size = Pt(18)
        paragraph.font.color.rgb = RGBColor(255, 255, 255)
        return slide

    def closing(self):
        return self._slide(len(self.source.slides) - 1)
