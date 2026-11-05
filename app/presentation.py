"""Editable, deterministic PowerPoint export for the filtered workbook snapshot.

The layout and typography use the supplied reference slide themes. The corporate
font is referenced by family name; font packaging is handled separately.
"""
from __future__ import annotations

from collections import defaultdict
from io import BytesIO
import json
import math

from .presentation_style import apply_presentation_style
from .presentation_brand import (add_background, add_brand_details, add_footer,
                                 add_icon, gradient_fill)
from .presentation_summary import (combine_groups, compact_groups, compact_years,
                                   compact_countries)

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
    'blue': '1E49E2', 'purple': '7213EA', 'global': '7213EA', 'local': '1E49E2',
    'ink': '0C233C', 'muted': '647789', 'line': 'DFE4F2', 'light': 'F3F1FC',
    'white': 'FFFFFF', 'amber': '94640F',
    'years': ['7213EA', '1E49E2', '007BA8', '510DBC', '00338D'],
}
MAX_SLIDES = 15
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


def _tone(slide, key):
    """Per-slide colors keep concurrent exports independent of each other."""
    dark = {'ink': 'FFFFFF', 'muted': 'E0DDFB', 'global': 'C8A9FF',
            'local': 'ACEAFF', 'amber': 'FFDF96'}
    return dark.get(key, THEME[key]) if getattr(slide, '_dvt_dark', False) else THEME[key]


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
        paragraph.font.bold = bold; paragraph.font.color.rgb = _rgb(color or _tone(slide, 'ink'))
        paragraph.line_spacing = line_spacing
    return box


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = str(text)


def _slide(prs, report, title, subtitle='', *, section='', dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide._dvt_dark = dark
    add_background(slide, W, H, dark=dark)
    heading = _text(slide, title, MARGIN, .4722, W - 2 * MARGIN, .5833,
          size=40 if len(title)<85 else 36, color=_tone(slide, 'ink'), bold=False,
          font=THEME['title_font'], line_spacing=.70)
    heading.name = 'dvt-title'
    heading.text_frame.margin_left = heading.text_frame.margin_right = 0
    heading.text_frame.margin_top = heading.text_frame.margin_bottom = 0
    for paragraph in heading.text_frame.paragraphs:
        gradient_fill(paragraph._p.get_or_add_pPr().get_or_add_defRPr(),
                      ('FFFFFF', 'ACEAFF') if dark else ('7213EA', '00338D'))
    if subtitle:
        subheading = _text(slide, subtitle, MARGIN, 1.08, W - 2 * MARGIN, .30, size=12, color=_tone(slide, 'muted'))
        subheading.name = 'dvt-subtitle'
    add_brand_details(slide, cover=section == 'Riepilogo', dark=dark)
    add_footer(slide, len(prs.slides), dark=dark)
    return slide


def _divider(prs, report, title):
    """Section title only; the corporate footer remains on every slide."""
    slide = _slide(prs, report, title, section='Separatore', dark=True)
    heading = next(shape for shape in slide.shapes if shape.name == 'dvt-title')
    heading.top = Inches(2.65); heading.height = Inches(1.5)
    for paragraph in heading.text_frame.paragraphs:
        paragraph.font.size = Pt(72 if len(title) < 25 else 60)
        paragraph.line_spacing = .90
    _notes(slide, _source_notes(report))
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
    dark = getattr(slide, '_dvt_dark', False)
    _shape(slide, x, y, width, 1.23, THEME['light'], radius=True,
           gradient=('4520AD', '17399A') if dark else None)
    _shape(slide, x, y, .045, 1.23, THEME['local'],
           gradient=('C8A9FF', 'ACEAFF') if dark else ('7213EA', '1E49E2'))
    kind = ('global' if 'global' in label.lower() else 'local' if 'local' in label.lower()
            else 'remediation' if 'remediation' in label.lower() else 'domain' if label == 'Domini'
            else 'owner' if label == 'Owner' else 'budget')
    accent = _tone(slide, kind) if kind in ('global', 'local') else _tone(slide, 'muted')
    add_icon(slide, kind, _x(x + width - .64), y + .15, .34, dark=dark)
    _text(slide, label, x + .18, y + .13, width - .95, .27, size=12, color=accent)
    value_text = _money(value) if isinstance(value, (float, int)) or value is None else str(value)
    _text(slide, value_text, x + .18, y + .43, width - .36, .48,
          size=32 if len(value_text) < 17 else 25, color=_tone(slide, 'ink'), font=THEME['title_font'], line_spacing=.8)
    if note:
        _text(slide, note, x + .18, y + .98, width - .36, .18, size=9, color=_tone(slide, 'muted'))


def _breakdown_value(breakdown, component, kind):
    suffix = 'Ot' if kind == 'ot' else 'Base'
    count = breakdown.get('otCount' if kind == 'ot' else 'baseCount', 0)
    missing = breakdown.get('missing' + component.capitalize() + suffix, 0)
    return None if count and missing == count else breakdown.get(component + suffix, 0)


def _category_value(category, component=None):
    missing = category.get(component + 'Missing', 0) if component else category.get('missing', 0)
    known = category.get(component + 'Known', 0) if component else category.get('known', 0)
    return None if missing and not known else category.get(component or 'total', 0)


def _reconciliation_strip(slide, breakdown, scope):
    """Four compact editable cards distinguish source base, OT and LE categories."""
    cards = []
    if scope != 'local':
        base = _breakdown_value(breakdown, 'global', 'base')
        delta = _breakdown_value(breakdown, 'global', 'ot')
        total = None if breakdown.get('rowCount') and breakdown.get('missingGlobal') == breakdown['rowCount'] else breakdown.get('global', 0)
        cards.append(('Global di gruppo', total, base, delta, THEME['global']))
    if scope != 'global':
        if breakdown.get('classificationAvailable'):
            colors = {'complete-ot': THEME['blue'], 'complete': '007BA8',
                      'business': THEME['purple'], 'unclassified': THEME['muted']}
            for category in breakdown.get('categories', []):
                if category['id'] == 'unclassified' and not category.get('entityCount'):
                    continue
                label = category['label'] + f' · {category.get("entityCount", 0)} LE'
                cards.append((label, _category_value(category), _category_value(category, 'base'),
                              _category_value(category, 'ot'), colors.get(category['id'], THEME['local'])))
        else:
            base = _breakdown_value(breakdown, 'local', 'base')
            delta = _breakdown_value(breakdown, 'local', 'ot')
            total = None if breakdown.get('rowCount') and breakdown.get('missingLocal') == breakdown['rowCount'] else breakdown.get('localTotal', 0)
            cards.append(('Local complessivo', total, base, delta, THEME['local']))
    if not cards:
        return
    _text(slide, 'Base e delta OT nel perimetro selezionato', MARGIN, 4.72, 12.17, .22,
          size=11, color=THEME['navy'], bold=True)
    gap = .15
    width = (W - 2 * MARGIN - gap * (len(cards) - 1)) / len(cards)
    for index, (label, total, base, delta, color) in enumerate(cards):
        x = MARGIN + index * (width + gap)
        _shape(slide, x, 5.03, width, 1.08, THEME['light'], radius=True)
        _shape(slide, x, 5.03, .04, 1.08, color)
        _text(slide, label, x + .12, 5.13, width - .24, .25,
              size=10 if len(cards) < 5 else 9, color=color, bold=True)
        _text(slide, _money(total), x + .12, 5.43, width - .24, .32,
              size=22 if len(cards) < 5 else 18, color=THEME['ink'], font=THEME['title_font'])
        _text(slide, f'Base {_money(base)} · Δ OT {_money(delta)}', x + .12, 5.84, width - .24, .19,
              size=8 if len(cards) > 3 else 9, color=THEME['muted'])
    if scope != 'global':
        parts = ['Global non ripartito alle legal entity.'] if scope == 'all' else []
        if breakdown.get('unallocated'):
            parts.append('Local senza attribuzione certa: ' + _money(breakdown['unallocated']) + '.')
        if breakdown.get('missingLocal') or breakdown.get('missingAllocationCount'):
            parts.append('Le stime mancanti restano distinte da zero.')
        if not breakdown.get('classificationAvailable'):
            parts.append('Classificazione Complete/Business non dichiarata nel file.')
        _text(slide, ' '.join(parts), MARGIN, 6.27, 12.17, .24,
              size=9, color=THEME['muted'])


def _source_notes(report, extra=''):
    source = report.get('source', {})
    return '\n'.join([
        'Data Visualization Tool — esportazione deterministica dei dati filtrati.',
        f'Progetto: {report.get("projectName", "")}',
        f'File sorgente: {source.get("filename", "")}',
        f'SHA-256: {source.get("sha256", "")}',
        'Filtri: ' + json.dumps(report.get('filters', {}), ensure_ascii=False, sort_keys=True),
        'Base, delta OT e categorie Local: ' + json.dumps(report.get('budgetBreakdown', {}), ensure_ascii=False, sort_keys=True),
        f'Livello rappresentato: {report.get("scope", "all")}', extra,
    ])


def _filter_lines(report):
    filters = report.get('filters', {})
    names = [('sheets', 'Fogli'), ('years', 'Anni'), ('domains', 'Domini'), ('owners', 'Owner'),
             ('entities', 'Country / legal entity'), ('nis2', 'NIS2'), ('priority', 'Priorità'), ('capexOpex', 'Capex/Opex'), ('risk', 'Rischi'), ('impact', 'Impatto')]
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
        add_icon(slide, 'domain' if title == 'Domini' else 'owner', _x(x), y + .015, .25, dark=False)
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
        _shape(slide, bx, by, bar_width, .15, 'E9EAF5', radius=True)
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
    chart.value_axis.major_gridlines.format.line.color.rgb = _rgb('DFE4F2')
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
    plot.data_labels.font.color.rgb = _rgb(THEME['white'])
    return chart


def _short(value, length):
    text = str(value or '')
    return text if len(text) <= length else text[:length - 1] + '…'


def _count_bars(slide, groups, title, x, y, width, height, color):
    # Ranking by row count is separate from ranking by investment.
    counts = [{'label': group['label'], 'count': group.get('count', 0),
               'global': group.get('count', 0), 'local': 0,
               'selected': group.get('count', 0)} for group in groups]
    shown = compact_groups(counts, limit=6, scope='global', other_label='Altri')
    _text(slide, title, x, y, width, .35, size=22, font=THEME['title_font'], color=color)
    maximum = max([group['count'] for group in shown] + [1])
    row_height = min(.49, (height - .50) / max(1, len(shown)))
    for index, group in enumerate(shown):
        yy = y + .53 + index * row_height
        _text(slide, _short(group['label'], 40), x, yy, width * .49, row_height,
              size=12, valign=MSO_ANCHOR.MIDDLE)
        bx = x + width * .51; bar_width = width * .35
        _shape(slide, bx, yy + row_height / 2 - .07, bar_width, .14, 'E9EAF5', radius=True)
        if group['count']:
            _shape(slide, bx, yy + row_height / 2 - .07,
                   bar_width * group['count'] / maximum, .14, color)
        _text(slide, str(group['count']), x + width * .89, yy, width * .11, row_height,
              size=13, bold=True, align=PP_ALIGN.RIGHT, valign=MSO_ANCHOR.MIDDLE)


def _tint(color, amount):
    amount = min(1, max(0, amount))
    return ''.join(f'{round(255 + (int(color[index:index + 2], 16) - 255) * amount):02X}'
                   for index in (0, 2, 4))


def _country_cell_group(country, column):
    members = set(column.get('members', [column['label']]))
    groups = [group for group in country.get('byYear', []) if str(group['label']) in members]
    return combine_groups(groups, column['label']) if groups else None


def _country_matrix(slide, countries, columns, maximum):
    label_width, total_width = 3.15, 1.75
    column_width = (12.17 - label_width - total_width) / max(1, len(columns))
    _text(slide, 'Country / legal entity', MARGIN, 1.65, label_width, .25,
          size=11, color=THEME['muted'])
    for index, column in enumerate(columns):
        x = MARGIN + label_width + index * column_width
        _text(slide, column['label'], x + .08, 1.65, column_width - .16, .25,
              size=12, bold=True, color=THEME['years'][index % len(THEME['years'])])
    total_x = MARGIN + 12.17 - total_width
    _text(slide, 'Totale Local', total_x, 1.65, total_width - .10, .25,
          size=11, bold=True, color=THEME['navy'], align=PP_ALIGN.RIGHT)
    row_height = .39
    for row_index, country in enumerate(countries):
        y = 2.02 + row_index * row_height
        _shape(slide, MARGIN, y, 12.17, .36, 'F8F9FC', radius=True)
        _text(slide, _short(country.get('name', country.get('id', '')), 40),
              MARGIN + .09, y + .035, label_width - .18, .28,
              size=12 if len(country.get('name', '')) < 30 else 10, color=THEME['navy'])
        for index, column in enumerate(columns):
            x = MARGIN + label_width + index * column_width
            color = THEME['years'][index % len(THEME['years'])]
            group = _country_cell_group(country, column)
            value = _known_value(group, 'local') if group else None
            partial = bool(group and value is not None and group.get('missingLocal'))
            text = '—' if not group else 'n.d.' if value is None else _money(value) + (' †' if partial else '')
            fraction = max(0, value or 0) / maximum
            _shape(slide, x + .025, y, column_width - .05, .36,
                   _tint(color, .04 + .22 * min(fraction, 1)), radius=True)
            if fraction > 0:
                _shape(slide, x + .06, y + .325, (column_width - .12) * min(fraction, 1), .022, color)
            _text(slide, text, x + .08, y + .035, column_width - .16, .28,
                  size=12 if len(columns) <= 3 else 10, color=THEME['ink'])
        totals = country.get('totals', {})
        total = _known_value(totals, 'local')
        _text(slide, _money(total) + (' †' if total is not None and totals.get('missingLocal') else ''),
              total_x, y + .035, total_width - .10, .28,
              size=12, bold=True, color=THEME['navy'], align=PP_ALIGN.RIGHT)


def _row_investment(row, scope):
    values = ([row.get('globalBudget')] if scope == 'global' else [row.get('displayLocal')]
              if scope == 'local' else [row.get('globalBudget'), row.get('displayLocal')])
    known = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return sum(known) if known else None


def _remediation_list(slide, rows, scope):
    ranked = sorted(rows, key=lambda row: (_row_investment(row, scope) is None,
                    -(_row_investment(row, scope) or 0), str(row.get('key', ''))))
    for label, x, color in [('Global', 8.95, THEME['global']), ('Local selezionato', 10.78, THEME['local'])]:
        _text(slide, label, x, 1.63, 1.75, .22, size=10, bold=True, color=color)
    for index, row in enumerate(ranked[:6]):
        y = 1.97 + index * .73
        _shape(slide, MARGIN, y, 12.17, .67, THEME['light'], radius=True)
        _shape(slide, MARGIN, y, .04, .67, THEME['purple'])
        name = str(row.get('name', ''))
        _text(slide, _short(name, 125), .78, y + .055, 7.84, .37,
              size=13 if len(name) < 85 else 11, bold=True, color=THEME['navy'])
        _text(slide, _short(f'{row.get("year") or "Anno non specificato"} · '
              f'{row.get("domain") or "Dominio non specificato"} · '
              f'{row.get("id") or "ID assente"} · {row.get("key", "")}', 115),
              .78, y + .46, 7.84, .16, size=8.5, color=THEME['muted'])
        _text(slide, _money(row.get('globalBudget')), 8.95, y + .22, 1.68, .28,
              size=13, bold=True, color=THEME['global'])
        _text(slide, _money(row.get('displayLocal')), 10.78, y + .22, 1.75, .28,
              size=13, bold=True, color=THEME['local'])


def create_presentation(report: dict) -> bytes:
    """Export an executive deck of at most 15 slides, with full source notes.

    The cap is structural: 1 cover + 4 dividers + 3 budget + up to 3 years +
    up to 2 country matrices + 2 remediation slides. Extra categories are
    combined explicitly; no original source row is removed from the notes.
    """
    rows = report.get('rows') or []
    if not rows:
        raise ValueError('Non ci sono remediation da esportare con i filtri selezionati.')
    prs = Presentation(); prs.slide_width = Inches(W); prs.slide_height = Inches(H)
    _apply_reference_theme(prs)
    prs.core_properties.title = (report.get('projectName') or 'Progetto') + ' — Piano di remediation'
    prs.core_properties.subject = 'Sintesi dei dati filtrati: budget, anni, country e remediation'
    prs.core_properties.author = 'Data Visualization Tool'
    scope = report.get('scope', 'all'); totals = report.get('totals', {})
    source = report.get('source', {})
    annual = report.get('byYear') or _groups_from_rows(rows, 'year', scope)
    domains = report.get('byDomain') or _groups_from_rows(rows, 'domain', scope)
    owners = report.get('byOwner') or _groups_from_rows(rows, 'owner', scope)

    slide = _slide(prs, report, 'Piano di remediation',
                   f'{report.get("projectName", "Progetto")} · {_scope_label(scope)}',
                   section='Riepilogo', dark=True)
    cover_title = next(shape for shape in slide.shapes if shape.name == 'dvt-title')
    cover_title.left = Inches(1.08); cover_title.top = Inches(1.60)
    cover_title.width = Inches(6.50); cover_title.height = Inches(2.75)
    cover_title.text_frame.text = 'Piano di\nremediation'
    for paragraph in cover_title.text_frame.paragraphs:
        paragraph.font.name = THEME['title_font']; paragraph.font.size = Pt(88)
        paragraph.font.color.rgb = _rgb('FFFFFF'); paragraph.line_spacing = .75
        gradient_fill(paragraph._p.get_or_add_pPr().get_or_add_defRPr(), ('FFFFFF', 'ACEAFF'))
    cover_subtitle = next(shape for shape in slide.shapes if shape.name == 'dvt-subtitle')
    cover_subtitle.top = Inches(4.50); cover_subtitle.width = Inches(6.60); cover_subtitle.height = Inches(.66)
    for paragraph in cover_subtitle.text_frame.paragraphs:
        paragraph.font.size = Pt(19)
    _stat(slide, 8.46, 1.64, 4.30, 'Budget selezionato', _selected_value(totals, scope))
    _stat(slide, 8.46, 3.08, 4.30, 'Budget Global', _known_value(totals, 'global'), 'Importo di gruppo')
    _stat(slide, 8.46, 4.52, 4.30, 'Budget Local', _known_value(totals, 'local'), 'Totale disponibile')
    _text(slide, 'DATA VISUALIZATION TOOL', MARGIN, .63, 7.3, .28, size=13, color='ACEAFF')
    _text(slide, f'{len(rows)} righe di remediation · {len(report.get("countries", []))} entità · {len(annual)} annualità',
          MARGIN, 5.36, 7.3, .35, size=14)
    for index, (label, kind) in enumerate([('Global / Local', 'budget'), ('Anni', 'year'), ('Country', 'global')]):
        x = MARGIN + index * 2.45
        add_icon(slide, kind, _x(x), 5.90, .30)
        _text(slide, label, x + .42, 5.91, 1.70, .24, size=11, color='ACEAFF')
        if index < 2:
            _text(slide, '›', x + 2.06, 5.89, .23, .28, size=16, color='ACEAFF')
    _text(slide, 'Fonte: ' + _short(source.get('filename', ''), 100), MARGIN, 6.31, 7.6, .23,
          size=10, color=_tone(slide, 'muted'))
    if totals.get('missingGlobal') or totals.get('missingLocal'):
        _text(slide, 'Totali sulle stime disponibili; attribuzioni incerte separate.', MARGIN, 6.62,
              W - MARGIN * 2, .22, size=10, color=_tone(slide, 'amber'))
    _notes(slide, _source_notes(report, '\n'.join(_filter_lines(report))))

    _divider(prs, report, 'Budget')
    annual_overview = compact_years(annual, limit=8, scope=scope)
    slide = _slide(prs, report, 'Budget per anno', 'Importi disponibili nel perimetro selezionato')
    reconciliation = report.get('budgetBreakdown')
    _annual_chart(slide, annual_overview, .75, 1.80, 11.8, 2.75 if reconciliation else 4.60, scope)
    if reconciliation:
        _reconciliation_strip(slide, reconciliation, scope)
    _text(slide, 'Global: budget di gruppo. Local: importo complessivo o attribuito alle entità selezionate.',
          MARGIN, 6.55, 12.1, .23, size=10, color=THEME['muted'])
    _notes(slide, _source_notes(report, 'Budget annuali completi: ' + json.dumps(annual, ensure_ascii=False, default=str)))
    for groups, title, other in [(domains, 'Budget per dominio', 'Altri domini'),
                                 (owners, 'Budget per owner', 'Altri owner')]:
        shown = compact_groups(groups, limit=8, scope=scope, other_label=other)
        subtitle = _scope_label(scope) + (' · 7 voci principali e altre aggregate' if len(groups) > 8 else '')
        slide = _slide(prs, report, title, subtitle)
        _legend(slide, MARGIN, 1.64, scope=scope)
        _bars(slide, shown, MARGIN, 2.15, W - MARGIN * 2, 4.40, scope=scope)
        _notes(slide, _source_notes(report, 'Gruppi completi: ' + json.dumps(groups, ensure_ascii=False, default=str)))

    _divider(prs, report, 'Anni')
    for year_group in compact_years(annual, limit=3, scope=scope):
        year = str(year_group.get('label', 'Anno non specificato'))
        year_rows = year_group.get('rows') or []
        members = year_group.get('members', [year])
        if not year_rows:
            year_rows = [row for row in rows if str(row.get('year') or 'Non specificato') in members]
        year_domains = _groups_from_rows(year_rows, 'domain', scope)
        year_owners = _groups_from_rows(year_rows, 'owner', scope)
        subtitle = f'{year_group.get("count", len(year_rows))} righe selezionate'
        if len(members) > 1:
            subtitle += f' · {len(members)} annualità aggregate; dettaglio nelle note'
        slide = _slide(prs, report, f'{year} · Budget e remediation', subtitle)
        _stat(slide, MARGIN, 1.64, 3.93, 'Budget selezionato', _selected_value(year_group, scope))
        _stat(slide, 4.70, 1.64, 3.93, 'Global', _known_value(year_group, 'global'))
        _stat(slide, 8.82, 1.64, 3.93, 'Local', _known_value(year_group, 'local'))
        _bars(slide, compact_groups(year_domains, limit=6, scope=scope, other_label='Altri domini'),
              MARGIN, 3.22, 5.95, 3.33, scope=scope, title='Domini')
        _bars(slide, compact_groups(year_owners, limit=6, scope=scope, other_label='Altri owner'),
              6.95, 3.22, 5.79, 3.33, scope=scope, title='Owner')
        _notes(slide, _source_notes(report, json.dumps({'years': members, 'domains': year_domains,
                  'owners': year_owners,
                  'budgetBreakdowns': [group.get('budgetBreakdown') for group in annual if group['label'] in members]},
                  ensure_ascii=False, default=str)))

    _divider(prs, report, 'Country / legal entity')
    countries = report.get('countries', [])
    shown_countries = compact_countries(countries, limit=22)
    # A per-entity Local-budget filter can include rows absent from the group
    # overview. Build country columns from those actual associations as well.
    country_years = defaultdict(list)
    for country in countries:
        for group in country.get('byYear', []):
            country_years[str(group['label'])].append(group)
    matrix_years = [combine_groups(groups, label) for label, groups in country_years.items()]
    columns = compact_years(matrix_years or annual, limit=5, scope='local')
    maximum = max([_known_value(group, 'local') or 0 for country in shown_countries
                   for column in columns for group in [_country_cell_group(country, column)] if group] + [1])
    country_pages = _chunks(shown_countries, 11) or [[]]
    for index, page in enumerate(country_pages):
        subtitle = f'{len(countries)} entità nel perimetro · {index + 1}/{len(country_pages)}'
        slide = _slide(prs, report, 'Budget Local per country e anno', subtitle)
        if page:
            _country_matrix(slide, page, columns, maximum)
        else:
            _text(slide, 'Nessuna attribuzione per country nel perimetro selezionato.',
                  MARGIN, 2.40, 12.17, .60, size=20, color=THEME['navy'])
        _text(slide, 'Il budget Global resta di gruppo. — nessuna voce · n.d. stima assente · † importo parziale. '
              'Attribuzioni incerte escluse.', MARGIN, 6.55, 12.17, .23, size=9, color=THEME['muted'])
        _notes(slide, _source_notes(report, 'Dettaglio completo delle country:\n' +
                  json.dumps(countries if index == 0 else page, ensure_ascii=False, default=str)))

    _divider(prs, report, 'Remediation')
    cut = (len(rows) + 1) // 2
    marker = 'RIGHE ORIGINALI COMPLETE — nessuna deduplicazione o modifica dei testi:\n'
    slide = _slide(prs, report, 'Remediation per anno e dominio', 'Numero di voci nel perimetro selezionato')
    _stat(slide, MARGIN, 1.64, 3.93, 'Voci di remediation', str(len(rows)))
    _stat(slide, 4.70, 1.64, 3.93, 'Domini', str(len(domains)))
    _stat(slide, 8.82, 1.64, 3.93, 'Owner', str(len(owners)))
    _count_bars(slide, annual, 'Anni', MARGIN, 3.22, 5.95, 3.22, THEME['purple'])
    _count_bars(slide, domains, 'Domini', 6.95, 3.22, 5.79, 3.22, THEME['blue'])
    _text(slide, 'Tutte le voci e i testi originali sono conservati nelle note delle ultime due slide.',
          MARGIN, 6.55, 12.17, .23, size=10, color=THEME['muted'])
    _notes(slide, _source_notes(report, marker + json.dumps(rows[:cut], ensure_ascii=False, indent=2, default=str)))

    slide = _slide(prs, report, 'Remediation per investimento',
                   f'{min(6, len(rows))} di {len(rows)} voci · Ordinate per budget selezionato ({_scope_label(scope)})')
    _remediation_list(slide, rows, scope)
    _text(slide, 'Sintesi dei dati filtrati. Filtri, note della fonte e testi completi sono nelle note della presentazione.',
          MARGIN, 6.55, 12.17, .23, size=10, color=THEME['muted'])
    method = '\n'.join(_filter_lines(report)) + '\nNote della fonte: ' + json.dumps(report.get('notes', []), ensure_ascii=False)
    _notes(slide, _source_notes(report, method + '\n' + marker +
                               json.dumps(rows[cut:], ensure_ascii=False, indent=2, default=str)))

    if len(prs.slides) > MAX_SLIDES:
        raise ValueError('La presentazione supera il limite di 15 slide.')
    output = BytesIO(); prs.save(output)
    return apply_presentation_style(output.getvalue())
