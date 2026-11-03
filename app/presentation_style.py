"""Apply the supplied presentation's visual theme and embedded document fonts.

The resource is a newly created, content-free presentation: it contains only the
KPMG color/font settings and editable embedded fonts taken from the user's deck.
Original template slides, notes, charts, images and metadata are not distributed.
"""
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
    """Embed the supplied KPMG Bold font and theme, preserving editable content."""
    with ZipFile(STYLE_PATH) as source, ZipFile(BytesIO(content)) as original:
        resource_pres = ET.fromstring(source.read('ppt/presentation.xml'))
        fonts = resource_pres.find(f'{{{NS_P}}}embeddedFontLst')
        source_rels = ET.fromstring(source.read('ppt/_rels/presentation.xml.rels'))
        resource_rels = {node.attrib['Id']: node for node in source_rels}
        if fonts is None:
            raise ValueError('Il tema PowerPoint non contiene i font richiesti.')
        files = {name: original.read(name) for name in original.namelist()}
        pres = ET.fromstring(files['ppt/presentation.xml'])
        rels = ET.fromstring(files['ppt/_rels/presentation.xml.rels'])
        types = ET.fromstring(files['[Content_Types].xml'])
        known_ids = {node.attrib['Id'] for node in rels}
        existing = pres.find(f'{{{NS_P}}}embeddedFontLst')
        if existing is not None:
            pres.remove(existing)
        embedded = deepcopy(fonts)
        index = 1
        for family in embedded:
            for face in list(family)[1:]:
                source_rel = resource_rels[face.attrib[f'{{{NS_R}}}id']]
                target = source_rel.attrib['Target']
                if source_rel.attrib.get('Type') != FONT_REL or source_rel.attrib.get('TargetMode') == 'External' or not target.startswith('fonts/') or '..' in target:
                    raise ValueError('Il tema PowerPoint contiene un riferimento font non valido.')
                font_bytes = source.read('ppt/' + target)
                while f'rId{index}' in known_ids:
                    index += 1
                relationship_id = f'rId{index}'
                known_ids.add(relationship_id)
                filename = 'fonts/dvt-' + posixpath.basename(target)
                ET.SubElement(rels, f'{{{NS_REL}}}Relationship', {
                    'Id': relationship_id, 'Type': FONT_REL, 'Target': filename,
                })
                face.attrib[f'{{{NS_R}}}id'] = relationship_id
                files['ppt/' + filename] = font_bytes
                index += 1
        # embeddedFontLst precedes defaultTextStyle in the presentation schema.
        insert_before = next((i for i, node in enumerate(pres)
                              if node.tag in {f'{{{NS_P}}}custShowLst', f'{{{NS_P}}}photoAlbum',
                                              f'{{{NS_P}}}custDataLst', f'{{{NS_P}}}kinsoku',
                                              f'{{{NS_P}}}defaultTextStyle', f'{{{NS_P}}}modifyVerifier',
                                              f'{{{NS_P}}}extLst'}), len(pres))
        pres.insert(insert_before, embedded)
        pres.attrib['embedTrueTypeFonts'] = '1'
        if not any(node.attrib.get('Extension') == 'fntdata' for node in types):
            ET.SubElement(types, f'{{{NS_CT}}}Default', {'Extension': 'fntdata', 'ContentType': 'application/x-fontdata'})
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
