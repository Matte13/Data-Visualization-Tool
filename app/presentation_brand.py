"""Editable visual elements from the supplied Global Cyber Pitch reference.

No source slide content is included. Backgrounds, icons and the original footer
logo are native DrawingML shapes, so exports stay offline and editable.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

PURPLE, BLUE, CYAN = '7213EA', '1E49E2', 'ACEAFF'
LOGO_PATH = Path(__file__).with_name('assets') / 'kpmg-footer-logo.xml'
COPYRIGHT = ('©2026 Copyright owned by one or more of the KPMG International entities.\n'
             'KPMG International entities provide no services to clients. All rights reserved.')
CLASSIFICATION = 'Document Classification: KPMG Confidential'


def gradient_fill(properties, colors=(PURPLE, BLUE), *, opacity=100000):
    """Replace a DrawingML fill with a real, editable horizontal gradient."""
    for child in list(properties):
        if child.tag in {qn('a:' + tag) for tag in
                         ('noFill', 'solidFill', 'gradFill', 'blipFill', 'pattFill', 'grpFill')}:
            properties.remove(child)
    fill = OxmlElement('a:gradFill')
    fill.set('flip', 'none'); fill.set('rotWithShape', '1')
    stops = OxmlElement('a:gsLst')
    for index, value in enumerate(colors):
        stop = OxmlElement('a:gs'); stop.set('pos', str(round(index * 100000 / (len(colors) - 1))))
        color = OxmlElement('a:srgbClr'); color.set('val', value)
        if opacity != 100000:
            alpha = OxmlElement('a:alpha'); alpha.set('val', str(opacity)); color.append(alpha)
        stop.append(color); stops.append(stop)
    fill.append(stops)
    direction = OxmlElement('a:lin'); direction.set('ang', '0'); direction.set('scaled', '1')
    fill.append(direction); fill.append(OxmlElement('a:tileRect'))
    # Each DrawingML container has its own order: text fills precede font
    # definitions, shape fills follow geometry, line fills precede dash/join.
    if properties.tag in {qn('a:' + tag) for tag in ('rPr', 'defRPr', 'endParaRPr')}:
        later = ('effectLst', 'effectDag', 'highlight', 'uLnTx', 'uLn', 'uFillTx', 'uFill',
                 'latin', 'ea', 'cs', 'sym', 'hlinkClick', 'hlinkMouseOver', 'rtl', 'extLst')
    elif properties.tag == qn('a:ln'):
        later = ('prstDash', 'custDash', 'round', 'bevel', 'miter', 'headEnd', 'tailEnd', 'extLst')
    else:
        later = ('ln', 'effectLst', 'effectDag', 'scene3d', 'sp3d', 'extLst')
    following = {qn('a:' + tag) for tag in later}
    position = next((index for index, child in enumerate(properties) if child.tag in following), len(properties))
    properties.insert(position, fill)
    return fill


def _plain_shape(slide, x, y, width, height, name):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(width), Inches(height))
    shape.name = name
    shape.line.fill.background()
    reference = shape._element.find('.//' + qn('a:effectRef'))
    if reference is not None:
        reference.set('idx', '0')
    shape._element.spPr.append(OxmlElement('a:effectLst'))
    return shape


def add_background(slide, width, height, *, dark=True):
    """Use the gradient on cover/dividers and the reference's white content base."""
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(PURPLE if dark else 'FFFFFF')
    shape = _plain_shape(slide, 0, 0, width, height, 'dvt-brand-background')
    if dark:
        gradient_fill(shape._element.spPr)
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(255, 255, 255)
    return shape


def add_brand_details(slide, *, cover=False, dark=True):
    """A quiet grid and gradient rule, behind content and outside data panels."""
    # The reference's digital grid is decorative; editor guides are not copied.
    # Keep it in the title band so it never interferes with chart labels.
    if dark:
        for index in range(10):
            x = 9.7 + index * .23
            line = _plain_shape(slide, x, .15, .006, 1.20, 'dvt-grid')
            gradient_fill(line._element.spPr, ('B5A1FF', CYAN), opacity=10000)
        for index in range(5):
            line = _plain_shape(slide, 9.7, .2 + index * .23, 2.07, .006, 'dvt-grid')
            gradient_fill(line._element.spPr, ('B5A1FF', CYAN), opacity=10000)
    rule = _plain_shape(slide, .8385, 1.435, 11.6163, .015, 'dvt-header-rule')
    gradient_fill(rule._element.spPr, ('B89BFF', '76D2FF') if dark else (PURPLE, BLUE),
                  opacity=65000 if dark else 35000)
    if cover:
        # A brand accent keeps the cover anchored without adding source content.
        accent = _plain_shape(slide, .8385, 1.53, .075, 3.55, 'dvt-cover-accent')
        gradient_fill(accent._element.spPr, ('ACEAFF', 'B59BFF'))


def _footer_text(slide, name, text, x, y, width, height, size, *, align=PP_ALIGN.LEFT, color='FFFFFF'):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    box.name = name
    frame = box.text_frame; frame.clear(); frame.word_wrap = False
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    for index, line in enumerate(text.split('\n')):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line; paragraph.alignment = align
        paragraph.font.name = 'Arial'; paragraph.font.size = Pt(size)
        paragraph.font.color.rgb = RGBColor.from_string(color)
        paragraph.space_before = paragraph.space_after = Pt(0)
        paragraph.line_spacing = 1.0
    return box


def add_footer(slide, page, *, dark=True):
    """Original footer geometry, vector logo and wording, with copyright 2026."""
    logo = deepcopy(parse_xml(LOGO_PATH.read_bytes()))
    identity = logo.find('.//' + qn('p:cNvPr'))
    identity.set('id', str(slide.shapes._next_shape_id)); identity.set('name', 'dvt-kpmg-logo')
    for color in logo.iter(qn('a:srgbClr')):
        color.set('val', 'FFFFFF' if dark else '00338D')
    slide.shapes._spTree.insert_element_before(logo, 'p:extLst')
    footer_color = 'FFFFFF' if dark else '808080'
    _footer_text(slide, 'dvt-copyright', COPYRIGHT, 1.4928, 6.8537, 3.0176, .2020, 6,
                 color=footer_color)
    _footer_text(slide, 'dvt-classification', CLASSIFICATION,
                 10.0655, 6.8849, 2.0409, .1010, 6, align=PP_ALIGN.RIGHT, color=footer_color)
    _footer_text(slide, 'dvt-page-number', str(page), 12.229605, 6.853671, .265186, .163399,
                 10, align=PP_ALIGN.RIGHT, color='FFFFFF' if dark else BLUE)


# Simple line illustrations, built as native freeform paths rather than images.
# Path coordinates use a 100 × 100 local drawing area.
_CIRCLE = [('M', 50, 8), ('C', 73, 8, 92, 27, 92, 50), ('C', 92, 73, 73, 92, 50, 92),
           ('C', 27, 92, 8, 73, 8, 50), ('C', 8, 27, 27, 8, 50, 8), ('Z',)]
ICONS = {
    'global': [_CIRCLE, [('M', 8, 50), ('L', 92, 50)],
               [('M', 50, 8), ('C', 22, 31, 22, 69, 50, 92), ('C', 78, 69, 78, 31, 50, 8)]],
    'local': [[('M', 15, 88), ('L', 15, 38), ('L', 50, 12), ('L', 85, 38), ('L', 85, 88), ('Z',)],
              [('M', 40, 88), ('L', 40, 59), ('L', 60, 59), ('L', 60, 88)],
              [('M', 29, 42), ('L', 38, 42)], [('M', 61, 42), ('L', 70, 42)]],
    'budget': [[('M', 13, 88), ('L', 13, 64), ('L', 30, 64), ('L', 30, 88)],
               [('M', 42, 88), ('L', 42, 44), ('L', 59, 44), ('L', 59, 88)],
               [('M', 71, 88), ('L', 71, 26), ('L', 88, 26), ('L', 88, 88)],
               [('M', 13, 44), ('L', 51, 17), ('L', 83, 9)],
               [('M', 67, 6), ('L', 85, 8), ('L', 78, 24)]],
    'year': [[('M', 14, 22), ('L', 86, 22), ('L', 86, 88), ('L', 14, 88), ('Z',)],
             [('M', 14, 40), ('L', 86, 40)], [('M', 32, 10), ('L', 32, 29)],
             [('M', 68, 10), ('L', 68, 29)], [('M', 31, 60), ('L', 44, 73), ('L', 69, 51)]],
    'domain': [[('M', 12, 12), ('L', 42, 12), ('L', 42, 42), ('L', 12, 42), ('Z',)],
               [('M', 58, 12), ('L', 88, 12), ('L', 88, 42), ('L', 58, 42), ('Z',)],
               [('M', 12, 58), ('L', 42, 58), ('L', 42, 88), ('L', 12, 88), ('Z',)],
               [('M', 58, 58), ('L', 88, 58), ('L', 88, 88), ('L', 58, 88), ('Z',)]],
    'owner': [[('M', 34, 13), ('C', 17, 13, 17, 43, 34, 43), ('C', 51, 43, 51, 13, 34, 13), ('Z',)],
              [('M', 12, 86), ('L', 12, 73), ('C', 12, 47, 56, 47, 56, 73), ('L', 56, 86)],
              [('M', 70, 20), ('C', 56, 20, 56, 44, 70, 44), ('C', 84, 44, 84, 20, 70, 20), ('Z',)],
              [('M', 65, 57), ('C', 80, 53, 90, 64, 90, 77), ('L', 90, 86)]],
    'remediation': [[('M', 23, 12), ('L', 82, 12), ('L', 82, 90), ('L', 23, 90), ('Z',)],
                    [('M', 35, 32), ('L', 42, 39), ('L', 54, 25)],
                    [('M', 59, 32), ('L', 72, 32)], [('M', 35, 57), ('L', 72, 57)],
                    [('M', 35, 75), ('L', 72, 75)]],
}


def add_icon(slide, kind, x, y, size=.40, *, opacity=100000, dark=True):
    shape = _plain_shape(slide, x, y, size, size, 'dvt-icon-' + kind)
    shape.fill.background()
    properties = shape._element.spPr
    old = properties.find(qn('a:prstGeom')); properties.remove(old)
    geometry = OxmlElement('a:custGeom')
    for name in ('avLst', 'gdLst', 'ahLst', 'cxnLst'):
        geometry.append(OxmlElement('a:' + name))
    rectangle = OxmlElement('a:rect')
    for key, value in [('l', '0'), ('t', '0'), ('r', 'w'), ('b', 'h')]: rectangle.set(key, value)
    geometry.append(rectangle)
    paths = OxmlElement('a:pathLst')
    for commands in ICONS.get(kind, ICONS['global']):
        path = OxmlElement('a:path')
        for key, value in [('w', '100'), ('h', '100'), ('fill', 'none'), ('stroke', '1')]: path.set(key, value)
        for command in commands:
            action, *coordinates = command
            node = OxmlElement('a:' + {'M': 'moveTo', 'L': 'lnTo', 'C': 'cubicBezTo', 'Z': 'close'}[action])
            for index in range(0, len(coordinates), 2):
                point = OxmlElement('a:pt'); point.set('x', str(coordinates[index])); point.set('y', str(coordinates[index + 1])); node.append(point)
            path.append(node)
        paths.append(path)
    geometry.append(paths); properties.insert(1, geometry)
    line = properties.find(qn('a:ln')); line.set('w', str(Pt(1.4))); line.set('cap', 'rnd')
    gradient_fill(line, ('C8A9FF', CYAN) if dark else (PURPLE, BLUE), opacity=opacity)
    return shape
