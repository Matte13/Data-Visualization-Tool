"""Apply the reference color/font scheme without binary font embedding."""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path
import posixpath
from lxml import etree as ET
from zipfile import ZIP_DEFLATED, ZipFile

NS_P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
NS_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS_CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
FONT_REL = NS_R + '/font'
STYLE_PATH = Path(__file__).with_name('assets') / 'presentation-style.pptx'


def _xml(element):
    return ET.tostring(element, encoding='utf-8', xml_declaration=True)


def apply_presentation_style(content: bytes) -> bytes:
    """Apply the reference theme using installed fonts and standard Office parts."""
    with ZipFile(STYLE_PATH) as source, ZipFile(BytesIO(content)) as original:
        files = {name: original.read(name) for name in original.namelist()}
        pres = ET.fromstring(files['ppt/presentation.xml'])
        rels = ET.fromstring(files['ppt/_rels/presentation.xml.rels'])
        types = ET.fromstring(files['[Content_Types].xml'])
        # Keep typeface references, but no compressed EOT font programs. They
        # are binary resources outside XML validation and vary by Office host.
        embedded = pres.find(f'{{{NS_P}}}embeddedFontLst')
        if embedded is not None:
            pres.remove(embedded)
        for attribute in ('embedTrueTypeFonts', 'saveSubsetFonts'):
            pres.attrib.pop(attribute, None)
        for relationship in list(rels):
            if relationship.get('Type') == FONT_REL:
                rels.remove(relationship)
        for name in list(files):
            if name.startswith('ppt/fonts/'):
                del files[name]
        for entry in list(types):
            if entry.get('Extension') == 'fntdata' or entry.get('PartName', '').startswith('/ppt/fonts/'):
                types.remove(entry)
        # Preserve all chart/source data. Only the font and color scheme change.
        if 'ppt/theme/theme1.xml' in files:
            current_theme = ET.fromstring(files['ppt/theme/theme1.xml'])
            resource_theme = ET.fromstring(source.read('ppt/theme/theme1.xml'))
            current_elements = current_theme.find(f'{{{NS_A}}}themeElements')
            resource_elements = resource_theme.find(f'{{{NS_A}}}themeElements')
            for name in ('clrScheme', 'fontScheme'):
                old = current_elements.find(f'{{{NS_A}}}{name}')
                new = resource_elements.find(f'{{{NS_A}}}{name}')
                position = list(current_elements).index(old)
                current_elements.remove(old)
                current_elements.insert(position, deepcopy(new))
            files['ppt/theme/theme1.xml'] = _xml(current_theme)
        files['ppt/presentation.xml'] = _xml(pres)
        files['ppt/_rels/presentation.xml.rels'] = _xml(rels)
        files['[Content_Types].xml'] = _xml(types)
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as result:
        for name, value in files.items():
            result.writestr(name, value)
    return output.getvalue()
