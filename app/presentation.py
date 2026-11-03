"""Editable, deterministic PowerPoint export for the filtered workbook snapshot.

The layout and typography use the supplied reference slide themes. The corporate
font is referenced by family name; font packaging is handled separately.
"""
from __future__ import annotations

from collections import defaultdict
from io import BytesIO
import json
import math
import textwrap

from .presentation_style import apply_presentation_style
from .presentation_brand import (add_background, add_brand_details, add_footer,
                                 add_icon, gradient_fill)

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree

THEME = {
    'font': 'Arial', 'title_font': 'KPMG Bold', 'navy': '00338D',
    'blue': '1E49E2', 'purple': '7213EA', 'global': 'C8A9FF', 'local': 'ACEAFF',
    'ink': 'FFFFFF', 'muted': 'E0DDFB', 'line': '8D80E8', 'light': '3824A3',
    'white': 'FFFFFF', 'amber': 'FFDF96',
    'years': ['D7BEFF', 'ACEAFF', 'AEBFFF', 'C8A9FF', '76D2FF', 'E3D7FF'],
}
W, H = 13.333333, 7.5
MARGIN, BODY_TOP, BODY_BOTTOM = .58, 1.58, 6.76
# Global Cyber Pitch: title x=.8385in, y=.4722in, width=11.6163in.
# Keep a logical grid for charts/cards and map it into that same content area.
REFERENCE_MARGIN = .8385
CONTENT_SCALE = 11.6163 / (W - 2 * MARGIN)


def _x(value):
    return value if value == 0 else REFERENCE_MARGIN + (value - MARGIN) * CONTENT_SCALE


def _width(value, x):
    return value if x == 0 else value * CONTENT_SCALE


def _apply_reference_theme(prs):
    """Use reference theme fonts/colors for newly edited charts and shapes too."""
    part=prs.part.part_related_by(RT.THEME)
    theme=parse_xml(part.blob)
    theme.set('name','Data Visualization Tool')
    font_scheme=theme.find('.//' + qn('a:fontScheme'))
    font_scheme.find(qn('a:majorFont')).find(qn('a:latin')).set('typeface',THEME['title_font'])
    font_scheme.find(qn('a:minorFont')).find(qn('a:latin')).set('typeface',THEME['font'])
    colors={'dk2':'00338D','lt2':'1E49E2','accent1':'0C233C','accent2':'00B8F5',
            'accent3':'7213EA','accent4':'FD349C','accent5':'76D2FF','accent6':'ACEAFF',
            'hlink':'00B8F5','folHlink':'510DBC'}
    scheme=theme.find('.//' + qn('a:clrScheme'))
    for name,value in colors.items():
        color=scheme.find(qn('a:'+name))
        for old in list(color):color.remove(old)
        element=OxmlElement('a:srgbClr');element.set('val',value);color.append(element)
    part._blob=etree.tostring(theme,encoding='UTF-8',xml_declaration=True,standalone=True)


def _money(value):
    if value is None:
        return 'Non stimato'
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return 'Non stimato'
    decimals = 0 if float(value).is_integer() else 2
    text = f'{value:,.{decimals}f}'.replace(',', '\0').replace('.', ',').replace('\0', '.')
    return text + ' €'


def _known_value(summary, field):
    value = summary.get(field)
    count = summary.get('count', 0)
    missing = summary.get('missing' + field.capitalize(), 0)
    return None if count and missing == count else value


def _selected_value(summary, scope='all'):
    if summary.get('selected') is None:
        return None
    count = summary.get('count', 0)
    if summary.get('selectedUnknown') is True:
        return None
    if scope == 'global':
        return _known_value(summary, 'global')
    if scope == 'local':
        return _known_value(summary, 'local')
    if count and summary.get('missingGlobal') == count and summary.get('missingLocal') == count:
        return None
    return summary.get('selected', (summary.get('global') or 0) + (summary.get('local') or 0))


def _chunks(values, size):
    return [values[index:index + size] for index in range(0, len(values), size)]


def _rgb(value):
    return RGBColor.from_string(value)


def _shape(slide, x, y, width, height, fill, *, line=None, radius=False, gradient=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                   Inches(_x(x)), Inches(y), Inches(_width(width, x)), Inches(height))
    shape.fill.solid(); shape.fill.fore_color.rgb = _rgb(fill)
    if line:
        shape.line.color.rgb = _rgb(line); shape.line.width = Pt(.7)
    else:
        shape.line.fill.background()
    # Avoid the default Office theme's inherited drop shadow on every rectangle.
    effect_reference = shape._element.find('.//' + qn('a:effectRef'))
    if effect_reference is not None:
        effect_reference.set('idx', '0')
    shape._element.spPr.append(OxmlElement('a:effectLst'))
    if gradient:
        gradient_fill(shape._element.spPr, gradient)
    if radius:
        try:
            shape.adjustments[0] = .025
        except (AttributeError, IndexError):
            pass
    return shape


def _text(slide, text, x, y, width, height, *, size=16, color=None, bold=False,
          align=PP_ALIGN.LEFT, font=None, valign=MSO_ANCHOR.TOP, line_spacing=1.08):
    box = slide.shapes.add_textbox(Inches(_x(x)), Inches(y), Inches(_width(width, x)), Inches(height))
    frame = box.text_frame; frame.clear(); frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(.01)
    frame.margin_top = frame.margin_bottom = Inches(.015)
    frame.vertical_anchor = valign
    for index, line in enumerate(str(text if text is not None else '').split('\n')):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line; paragraph.alignment = align
        paragraph.space_before = Pt(0); paragraph.space_after = Pt(0)
        paragraph.font.name = font or THEME['font']; paragraph.font.size = Pt(size)
        paragraph.font.bold = bold; paragraph.font.color.rgb = _rgb(color or THEME['ink'])
        paragraph.line_spacing = line_spacing
    return box


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = str(text)


def _slide(prs, report, title, subtitle='', *, section=''):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, W, H)
    heading = _text(slide, title, MARGIN, .4722, W - 2 * MARGIN, .5833,
          size=40 if len(title)<85 else 36, color=THEME['white'], bold=False,
          font=THEME['title_font'], line_spacing=.70)
    heading.name = 'dvt-title'
    heading.text_frame.margin_left = heading.text_frame.margin_right = 0
    heading.text_frame.margin_top = heading.text_frame.margin_bottom = 0
    for paragraph in heading.text_frame.paragraphs:
        gradient_fill(paragraph._p.get_or_add_pPr().get_or_add_defRPr(), ('FFFFFF', 'ACEAFF'))
    if subtitle:
        subheading = _text(slide, subtitle, MARGIN, 1.08, W - 2 * MARGIN, .30, size=12, color=THEME['muted'])
        subheading.name = 'dvt-subtitle'
    add_brand_details(slide, cover=section == 'Riepilogo')
    add_footer(slide, len(prs.slides))
    return slide


def _legend(slide, x, y, *, scope='all'):
    labels = []
    if scope != 'local': labels.append(('Global', THEME['global']))
    if scope != 'global': labels.append(('Local', THEME['local']))
    for label, color in labels:
        _shape(slide, x, y + .045, .11, .11, color)
        _text(slide, label, x + .18, y, 1.1, .25, size=11, color=THEME['muted'])
        x += 1.30


def _stat(slide, x, y, width, label, value, note=''):
    _shape(slide, x, y, width, 1.23, THEME['light'], radius=True,
           gradient=('4520AD', '17399A'))
    _shape(slide, x, y, .045, 1.23, THEME['local'], gradient=('C8A9FF', 'ACEAFF'))
    kind = 'global' if 'global' in label.lower() else 'local' if 'local' in label.lower() else 'budget'
    accent = THEME.get(kind, THEME['white'])
    add_icon(slide, kind, _x(x + width - .64), y + .15, .34)
    _text(slide, label, x + .18, y + .13, width - .95, .27, size=12, color=accent)
    value_text = _money(value) if isinstance(value, (float, int)) or value is None else str(value)
    _text(slide, value_text, x + .18, y + .43, width - .36, .48,
          size=32 if len(value_text) < 17 else 25, color=THEME['white'], font=THEME['title_font'], line_spacing=.8)
    if note:
        _text(slide, note, x + .18, y + .98, width - .36, .18, size=9, color=THEME['muted'])


def _source_notes(report, extra=''):
    source = report.get('source', {})
    return '\n'.join([
        'Data Visualization Tool — esportazione deterministica dei dati filtrati.',
        f'Progetto: {report.get("projectName", "")}',
        f'File sorgente: {source.get("filename", "")}',
        f'SHA-256: {source.get("sha256", "")}',
        'Filtri: ' + json.dumps(report.get('filters', {}), ensure_ascii=False, sort_keys=True),
        f'Livello rappresentato: {report.get("scope", "all")}', extra,
    ])


def _filter_lines(report):
    filters = report.get('filters', {})
    names = [('sheets', 'Fogli'), ('years', 'Anni'), ('domains', 'Domini'), ('owners', 'Owner'),
             ('entities', 'Country / legal entity'), ('nis2', 'NIS2'), ('priority', 'Priorità')]
    lines = []
    for key, label in names:
        value = filters.get(key)
        if isinstance(value, list):
            shown = ', '.join(str(item) for item in value) if value else 'nessuna selezione'
        elif value in (None, 'all'):
            shown = 'tutti'
        else:
            shown = str(value)
        lines.append(f'{label}: {shown}')
    if filters.get('query'):
        lines.append('Ricerca: ' + str(filters['query']))
    if filters.get('localBudget') not in (None, 'all'):
        lines.append('Budget Local: ' + {'positive': 'positivo', 'zero': 'zero', 'missing': 'non determinato'}.get(filters['localBudget'], str(filters['localBudget'])))
    return lines


def _scope_label(scope):
    return {'all': 'Global e Local', 'global': 'Global', 'local': 'Local'}.get(scope, 'Global e Local')


def _groups_from_rows(rows, field, scope='all'):
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field) or 'Non specificato')].append(row)
    result = []
    for label, records in grouped.items():
        global_values = [row.get('globalBudget') for row in records]
        local_values = [row.get('displayLocal') for row in records]
        global_sum = sum(value for value in global_values if isinstance(value, (int, float)))
        local_sum = sum(value for value in local_values if isinstance(value, (int, float)))
        result.append({'label': label, 'global': global_sum, 'local': local_sum,
                       'selected': global_sum if scope == 'global' else local_sum if scope == 'local' else global_sum + local_sum,
                       'count': len(records), 'missingGlobal': sum(value is None for value in global_values),
                       'missingLocal': sum(value is None for value in local_values), 'rows': records})
    return sorted(result, key=lambda entry: -(entry.get('selected') or 0))


def _bars(slide, groups, x, y, width, height, *, scope='all', row_height=None, title=None, scale_max=None):
    """Editable rectangles and exact labels, using one scale per comparison chart."""
    if title:
        add_icon(slide, 'domain' if title == 'Domini' else 'owner', _x(x), y + .015, .25)
        _text(slide, title, x + .37, y, width - .37, .32, size=19,
              font=THEME['title_font'], color=THEME['local'])
        y += .47; height -= .47
    if not groups:
        _text(slide, 'Nessuna voce per i filtri selezionati.', x, y + .1, width, .6, size=14, color=THEME['muted'])
        return
    row_height = row_height or min(.58, height / len(groups))
    max_value = max(scale_max or 0, 1) if scale_max is not None else max([(_selected_value(group, scope) or 0) for group in groups] + [1])
    label_width = width * .34
    amount_width = 1.50
    bar_width = max(.45, width - label_width - amount_width - .25)
    for index, group in enumerate(groups):
        yy = y + index * row_height
        label = str(group.get('label', 'Non specificato'))
        _text(slide, label, x, yy, label_width - .12, row_height - .02,
              size=12 if len(label) > 38 else 13, color=THEME['ink'], valign=MSO_ANCHOR.MIDDLE)
        bx = x + label_width
        by = yy + max(.09, (row_height - .15) / 2)
        _shape(slide, bx, by, bar_width, .15, '453CB1', radius=True)
        global_value = 0 if scope == 'local' else group.get('global') or 0
        local_value = 0 if scope == 'global' else group.get('local') or 0
        current = bx
        for value, color in [(global_value, THEME['global']), (local_value, THEME['local'])]:
            if value > 0:
                segment = bar_width * value / max_value
                _shape(slide, current, by, segment, .15, color)
                current += segment
        _text(slide, _money(_selected_value(group, scope)), bx + bar_width + .12, yy,
              amount_width, row_height - .02, size=12, color=THEME['ink'], align=PP_ALIGN.RIGHT,
              valign=MSO_ANCHOR.MIDDLE)


def _annual_chart(slide, groups, x, y, width, height, scope):
    data = CategoryChartData()
    data.categories = [str(group.get('label', 'Non specificato')) for group in groups]
    if scope != 'local':
        data.add_series('Global', [_known_value(group, 'global') for group in groups])
    if scope != 'global':
        data.add_series('Local', [_known_value(group, 'local') for group in groups])
    chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(_x(x)), Inches(y), Inches(_width(width, x)), Inches(height), data).chart
    chart.has_legend = True; chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.name = THEME['font']; chart.legend.font.size = Pt(12)
    chart.legend.font.color.rgb = _rgb(THEME['ink'])
    chart.chart_style = 10
    # Office chart styles otherwise introduce a white canvas on the brand base.
    for parent in (chart._chartSpace, chart._chartSpace.find(qn('c:chart')).find(qn('c:plotArea'))):
        properties = parent.find(qn('c:spPr'))
        if properties is None:
            properties = OxmlElement('c:spPr')
            # c:spPr precedes c:txPr/externalData in CT_ChartSpace.
            next_node = next((node for node in parent if node.tag in
                              {qn('c:txPr'), qn('c:externalData'), qn('c:printSettings'), qn('c:extLst')}), None)
            if next_node is None: parent.append(properties)
            else: parent.insert(list(parent).index(next_node), properties)
        for child in list(properties): properties.remove(child)
        properties.append(OxmlElement('a:noFill'))
        line = OxmlElement('a:ln'); line.append(OxmlElement('a:noFill')); properties.append(line)
    chart.category_axis.tick_labels.font.name = THEME['font']; chart.category_axis.tick_labels.font.size = Pt(15)
    chart.category_axis.tick_labels.font.color.rgb = _rgb(THEME['ink'])
    chart.value_axis.tick_labels.font.name = THEME['font']; chart.value_axis.tick_labels.font.size = Pt(10)
    chart.value_axis.tick_labels.font.color.rgb = _rgb(THEME['muted'])
    chart.value_axis.tick_labels.number_format = '#,##0" €"'
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = _rgb('8F80E1')
    chart.value_axis.major_gridlines.format.line.width = Pt(.45)
    chart.value_axis.format.line.fill.background(); chart.category_axis.format.line.color.rgb = _rgb(THEME['line'])
    plot = chart.plots[0]; plot.gap_width = 95
    colors = [THEME['global'], THEME['local']] if scope == 'all' else [THEME['global'] if scope == 'global' else THEME['local']]
    for series, color in zip(chart.series, colors):
        series.format.fill.solid(); series.format.fill.fore_color.rgb = _rgb(color)
        series.format.line.fill.background()
    plot.has_data_labels = True
    plot.data_labels.position = XL_LABEL_POSITION.CENTER
    plot.data_labels.number_format = '#,##0.##" €";-#,##0.##" €";'
    plot.data_labels.font.name = THEME['font']; plot.data_labels.font.size = Pt(11)
    plot.data_labels.font.color.rgb = _rgb(THEME['navy'])
    return chart


def _country_card(slide, country, x, y, width, height, years, year_colors, domain_max):
    totals = country.get('totals', {})
    _shape(slide, x, y, width, height, THEME['light'], line=THEME['line'], radius=True,
           gradient=('4420A7', '2238A4'))
    add_icon(slide, 'global', _x(x + .20), y + .20, .33)
    _text(slide, country.get('name', country.get('id', 'Country')), x + .68, y + .17, width - 2.53, .65,
          size=21 if len(country.get('name', '')) < 38 else 17 if len(country.get('name', '')) < 65 else 13,
          color=THEME['white'], font=THEME['title_font'])
    _text(slide, 'Budget Local', x + width - 1.82, y + .15, 1.60, .20, size=10, color=THEME['muted'], align=PP_ALIGN.RIGHT)
    _text(slide, _money(_known_value(totals, 'local')), x + width - 2.14, y + .41, 1.92, .40,
          size=24, color=THEME['local'], font=THEME['title_font'], align=PP_ALIGN.RIGHT)
    by_year = {str(group.get('label', '')): group for group in country.get('byYear', [])}
    blocks = max(1, len(years)); gap = .11
    block_width = (width - .4 - gap * (blocks - 1)) / blocks
    for index, year in enumerate(years):
        bx = x + .2 + index * (block_width + gap); by = y + .98
        group = by_year.get(year)
        value = _known_value(group, 'local') if group else None
        _shape(slide, bx, by, block_width, 1.04, '30288B', radius=True)
        _shape(slide, bx, by, block_width, .035, year_colors[year])
        _text(slide, year or 'Anno non specificato', bx + .10, by + .11, block_width - .20, .22, size=11, color=year_colors[year], bold=True)
        _text(slide, _money(value) if group else 'Nessuna voce', bx + .10, by + .43, block_width - .20, .32, size=16 if blocks <= 3 else 13, color=THEME['ink'], bold=True)
        if group and group.get('missingLocal'):
            _text(slide, 'Importo disponibile' if group.get('missingLocal') < group.get('count', 0) else 'Da verificare', bx + .10, by + .79, block_width - .20, .15, size=8, color=THEME['amber'])
    domains = sorted(country.get('byDomain', []), key=lambda group: -(group.get('local') or 0))
    _text(slide, 'Domini · budget Local', x + .20, y + 2.26, width - .40, .24,
          size=11, color=THEME['muted'])
    _bars(slide, domains[:3], x + .20, y + 2.65, width - .40, 1.35,
          scope='local', row_height=.42, scale_max=domain_max)
    if len(domains) > 3:
        _text(slide, f'Altri {len(domains) - 3} domini nelle note della slide.', x + .20, y + 4.04,
              width - .40, .18, size=8, color=THEME['muted'])
    if totals.get('missingLocal'):
        _text(slide, 'Le attribuzioni non determinate sono escluse dagli importi.', x + .20, y + height - .35,
              width - .40, .20, size=9, color=THEME['amber'])


def create_presentation(report: dict) -> bytes:
    """Return a standard editable PPTX. All numbers come from the validated report."""
    rows = report.get('rows') or []
    if not rows:
        raise ValueError('Non ci sono remediation da esportare con i filtri selezionati.')
    prs = Presentation(); prs.slide_width = Inches(W); prs.slide_height = Inches(H)
    _apply_reference_theme(prs)
    prs.core_properties.title = (report.get('projectName') or 'Progetto') + ' — Piano di remediation'
    prs.core_properties.subject = 'Dati filtrati dal workbook: budget Global, Local e country'
    prs.core_properties.author = 'Data Visualization Tool'
    scope = report.get('scope', 'all'); totals = report.get('totals', {})
    source = report.get('source', {})
    years = sorted({str(group.get('label', '')) for group in report.get('byYear', [])})
    year_colors = {year: THEME['years'][index % len(THEME['years'])] for index, year in enumerate(years)}

    slide = _slide(prs, report, 'Piano di remediation', f'{report.get("projectName", "Progetto")} · {_scope_label(scope)}', section='Riepilogo')
    cover_title=next(shape for shape in slide.shapes if shape.name == 'dvt-title')
    cover_title.left=Inches(1.08)
    cover_title.top=Inches(1.60);cover_title.width=Inches(6.50);cover_title.height=Inches(2.75)
    cover_title.text_frame.text='Piano di\nremediation'
    cover_title.text_frame.margin_left=cover_title.text_frame.margin_top=0
    for paragraph in cover_title.text_frame.paragraphs:
        paragraph.font.name=THEME['title_font'];paragraph.font.size=Pt(88)
        paragraph.font.color.rgb=_rgb(THEME['white']);paragraph.line_spacing=.75
        gradient_fill(paragraph._p.get_or_add_pPr().get_or_add_defRPr(), ('FFFFFF', 'ACEAFF'))
    # The cover's project label moves below the large headline, instead of competing with it.
    cover_subtitle=next(shape for shape in slide.shapes if shape.name == 'dvt-subtitle')
    cover_subtitle.top=Inches(4.50);cover_subtitle.width=Inches(6.60);cover_subtitle.height=Inches(.66)
    for paragraph in cover_subtitle.text_frame.paragraphs:
        paragraph.font.size=Pt(19)
    _stat(slide, 8.46, 1.64, 4.30, 'Budget selezionato', _selected_value(totals, scope))
    _stat(slide, 8.46, 3.08, 4.30, 'Budget Global', _known_value(totals, 'global'), 'Importo di gruppo')
    _stat(slide, 8.46, 4.52, 4.30, 'Budget Local', _known_value(totals, 'local'), 'Totale disponibile')
    _text(slide, 'DATA VISUALIZATION TOOL', MARGIN, .63, 7.3, .28, size=13, color=THEME['local'])
    _text(slide, f'{len(rows)} righe di remediation · {len(report.get("countries", []))} entità · {len(years)} annualità', MARGIN, 5.36, 7.3, .35, size=14, color=THEME['ink'])
    for index, (label, kind) in enumerate([('Global / Local', 'budget'), ('Anni', 'year'), ('Country', 'global')]):
        x = MARGIN + index * 2.45
        add_icon(slide, kind, _x(x), 5.90, .30)
        _text(slide, label, x + .42, 5.91, 1.70, .24, size=11, color=THEME['local'])
        if index < 2:
            _text(slide, '›', x + 2.06, 5.89, .23, .28, size=16, color=THEME['local'])
    _text(slide, 'Fonte: ' + source.get('filename', ''), MARGIN, 6.31, 7.6, .23, size=10, color=THEME['muted'])
    if totals.get('missingGlobal') or totals.get('missingLocal'):
        _text(slide, 'Totali sulle stime disponibili; attribuzioni incerte separate.', MARGIN, 6.62, W - MARGIN * 2, .22, size=10, color=THEME['amber'])
    _notes(slide, _source_notes(report, '\n'.join(_filter_lines(report))))

    annual = report.get('byYear', [])
    for index, page in enumerate(_chunks(annual, 8)):
        slide = _slide(prs, report, 'Budget per anno', 'Importi disponibili nel perimetro selezionato' + (f' · {index + 1}' if len(annual) > 8 else ''), section='Anni')
        _annual_chart(slide, page, .75, 1.80, 11.8, 4.60, scope)
        _text(slide, 'Global: budget di gruppo. Local: importo complessivo o attribuito alle entità selezionate.', MARGIN, 6.55, 12.1, .23, size=10, color=THEME['muted'])
        _notes(slide, _source_notes(report, 'Budget annuali: ' + json.dumps(page, ensure_ascii=False, default=str)))

    for field, title in [('byDomain', 'Budget per dominio'), ('byOwner', 'Budget per owner')]:
        groups = report.get(field, [])
        for index, page in enumerate(_chunks(groups, 8)):
            slide = _slide(prs, report, title, _scope_label(scope) + (f' · pagina {index + 1} di {math.ceil(len(groups) / 8)}' if len(groups) > 8 else ''), section='Global / Local')
            _legend(slide, MARGIN, 1.64, scope=scope)
            _bars(slide, page, MARGIN, 2.15, W - MARGIN * 2, 4.45, scope=scope)
            _notes(slide, _source_notes(report, json.dumps(page, ensure_ascii=False, default=str)))

    # Year drilldown: no categories disappear; additional categories get further slides.
    for year_group in annual:
        year_rows = year_group.get('rows') or [row for row in rows if str(row.get('year') or 'Non specificato') == str(year_group.get('label'))]
        domains = _groups_from_rows(year_rows, 'domain', scope)
        owners = _groups_from_rows(year_rows, 'owner', scope)
        domain_pages, owner_pages = _chunks(domains, 7), _chunks(owners, 7)
        count = max(len(domain_pages), len(owner_pages), 1)
        for index in range(count):
            year = str(year_group.get('label', 'Anno non specificato'))
            slide = _slide(prs, report, f'{year} · Budget e remediation', f'{year_group.get("count", len(year_rows))} righe selezionate' + (f' · pagina {index + 1} di {count}' if count > 1 else ''), section='Dettaglio annuale')
            _stat(slide, MARGIN, 1.64, 3.93, 'Budget selezionato', _selected_value(year_group, scope))
            _stat(slide, 4.70, 1.64, 3.93, 'Global', _known_value(year_group, 'global'))
            _stat(slide, 8.82, 1.64, 3.93, 'Local', _known_value(year_group, 'local'))
            _bars(slide, domain_pages[index] if index < len(domain_pages) else [], MARGIN, 3.22, 5.95, 3.45, scope=scope, title='Domini')
            _bars(slide, owner_pages[index] if index < len(owner_pages) else [], 6.95, 3.22, 5.79, 3.45, scope=scope, title='Owner')
            _notes(slide, _source_notes(report, json.dumps({'year': year, 'domains': domains, 'owners': owners}, ensure_ascii=False, default=str)))

    countries = report.get('countries', [])
    if countries:
        # Two wide country cards keep both the entity/year relation and exact values legible.
        country_pages = _chunks(countries, 2)
        year_pages = _chunks(years, 4) or [[]]
        for country_page in country_pages:
            for year_page in year_pages:
                slide = _slide(prs, report, 'Country · Budget Local per anno', 'Solo importi attribuibili alle entità. Il budget Global resta di gruppo.', section='Country / legal entity')
                domain_max=max([group.get('local') or 0 for country in country_page for group in country.get('byDomain', [])]+[1])
                for index, country in enumerate(country_page):
                    _country_card(slide, country, MARGIN + index * 6.20, 1.72, 6.0, 4.62, year_page, year_colors, domain_max)
                _text(slide, 'Barre dei domini sulla stessa scala nella slide. Importi non attribuibili esclusi; dettaglio completo nelle note.', MARGIN, 6.56, 12.1, .23, size=10, color=THEME['muted'])
                _notes(slide, _source_notes(report, 'Dettaglio completo delle country della slide:\n' + json.dumps(country_page, ensure_ascii=False, default=str)))

    # All rows, including duplicate or absent source IDs, remain represented independently.
    # Their long original descriptions and exact fields remain unabridged in speaker notes.
    for index, page in enumerate(_chunks(rows, 3)):
        slide = _slide(prs, report, 'Remediation selezionate', f'Appendice · {index * 3 + 1}–{index * 3 + len(page)} di {len(rows)} · testi completi nelle note', section='Appendice')
        for offset, row in enumerate(page):
            y = 1.65 + offset * 1.66
            _shape(slide, MARGIN, y, 12.17, 1.50, THEME['light'], radius=True,
                   gradient=('4620AC', '2137A3'))
            _shape(slide, MARGIN, y, .045, 1.50, THEME['local'], gradient=('C8A9FF', 'ACEAFF'))
            key = str(row.get('key') or f'{row.get("sheet", "")}:{row.get("excelRow", "")}')
            _text(slide, key + (' · ' + str(row['id']) if row.get('id') else ' · ID assente'), .78, y + .10, 3.1, .22, size=10, color=THEME['muted'])
            name = str(row.get('name', ''))
            _text(slide, name if len(name)<=180 else name[:177]+'…', .78, y + .37, 7.55, .60, size=16 if len(name) < 120 else 12, color=THEME['white'], bold=True)
            _text(slide, f'{row.get("domain") or "Dominio non specificato"} · {row.get("owner") or "Owner non specificato"} · {row.get("year") or "Anno non specificato"}', .78, y + 1.06, 7.60, .28, size=10, color=THEME['muted'])
            _text(slide, 'Global', 8.80, y + .13, 1.68, .19, size=9, color=THEME['muted'])
            _text(slide, _money(row.get('globalBudget')), 8.80, y + .40, 1.68, .30, size=15, color=THEME['global'], bold=True)
            _text(slide, 'Local selezionato', 10.69, y + .13, 1.84, .19, size=9, color=THEME['muted'])
            _text(slide, _money(row.get('displayLocal')), 10.69, y + .40, 1.84, .30, size=15, color=THEME['local'], bold=True)
            _text(slide, 'Complete ' + _money(row.get('localComplete')), 8.80, y + .91, 1.80, .24, size=8.5, color=THEME['muted'])
            _text(slide, 'Business ' + _money(row.get('localBusiness')), 10.69, y + .91, 1.84, .24, size=8.5, color=THEME['muted'])
            if row.get('displayLocal') is None:
                _text(slide, 'Attribuzione / stima da verificare', 8.80, y + 1.19, 3.71, .18, size=8, color=THEME['amber'])
        _notes(slide, _source_notes(report, 'RIGHE ORIGINALI COMPLETE — nessuna deduplicazione o modifica dei testi:\n' + json.dumps(page, ensure_ascii=False, indent=2, default=str)))

    # Short method/filter appendix; long filter values are paginated rather than cut.
    note_lines = _filter_lines(report)
    note_lines += ['Fonte: ' + source.get('filename', ''), 'SHA-256: ' + source.get('sha256', '')]
    note_lines += [str(note) for note in report.get('notes', [])]
    wrapped = []
    for line in note_lines:
        wrapped.extend(textwrap.wrap(line, width=115, replace_whitespace=False) or [''])
        wrapped.append('')
    for index, page in enumerate(_chunks(wrapped, 17)):
        slide = _slide(prs, report, 'Dati e filtri', 'Perimetro dell’esportazione e note della fonte', section='Appendice')
        _text(slide, '\n'.join(page), MARGIN, 1.66, 12.17, 4.99, size=13, color=THEME['ink'])
        _notes(slide, _source_notes(report, '\n'.join(note_lines)))

    output = BytesIO(); prs.save(output)
    return apply_presentation_style(output.getvalue())
