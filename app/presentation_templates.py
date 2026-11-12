"""Import the supplied editable separator designs and fixed closing slide."""
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import SystemRandom
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

TEMPLATE_PATH = Path(__file__).with_name('assets') / 'export-separators.pptx'
BACKGROUND_PATH = Path(__file__).with_name('assets') / 'ppt-backgrounds'


def export_date(now=None):
    """Rome date even on Windows interpreters without an IANA timezone database."""
    now = now or datetime.now(timezone.utc)
    try:
        local = now.astimezone(ZoneInfo('Europe/Rome'))
    except ZoneInfoNotFoundError:
        # Current EU rules: summer time starts/ends at 01:00 UTC on the
        # last Sunday of March/October. Avoid using the host's timezone.
        def transition(month):
            last = datetime(now.year, month, monthrange(now.year, month)[1], 1, tzinfo=timezone.utc)
            return last - timedelta(days=(last.weekday() + 1) % 7)
        offset = 2 if transition(3) <= now < transition(10) else 1
        local = now.astimezone(timezone(timedelta(hours=offset)))
    return local.strftime('%d/%m/%Y')


class ExportTemplates:
    def __init__(self, presentation):
        self.presentation = presentation
        self.order = list(range(1, 5))
        SystemRandom().shuffle(self.order)
        self.date = export_date()

    def _slide(self, filename, name):
        # Only standard SlidePart/ImagePart resources are written to the deck.
        # Original artwork is flattened once, rather than importing masters,
        # layouts, printer settings, extensions and binary font dependencies.
        prs = self.presentation
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        picture = slide.shapes.add_picture(str(BACKGROUND_PATH / filename), 0, 0,
                                          width=prs.slide_width, height=prs.slide_height)
        picture.name = name
        return slide

    def divider(self, title):
        design = self.order.pop()
        slide = self._slide(f'separator-{design:02}.png', f'dvt-separator-background-{design}')
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
        page = slide.shapes.add_textbox(Inches(11.97), Inches(6.85), Inches(.27), Inches(.16))
        page.name = 'dvt-template-page-number'; page.text = str(len(self.presentation.slides))
        paragraph = page.text_frame.paragraphs[0]
        paragraph.font.name = 'Arial'; paragraph.font.size = Pt(7)
        paragraph.font.color.rgb = RGBColor(255,255,255)
        return slide

    def closing(self):
        return self._slide('closing.png', 'dvt-closing-background')
