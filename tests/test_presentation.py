"""PPTX structure, editable charts, exact amounts and complete source notes."""
from copy import deepcopy
from io import BytesIO
import json
import unittest
from zipfile import ZipFile

from pptx import Presentation
from pptx.oxml.ns import qn

from app.presentation import create_presentation, _selected_value


def _summary(rows):
    g = [row.get('globalBudget') for row in rows]
    l = [row.get('displayLocal') for row in rows]
    return {'global': sum(x for x in g if x is not None),
            'local': sum(x for x in l if x is not None),
            'selected': sum(x for x in g+l if x is not None),
            'count': len(rows), 'missingGlobal': sum(x is None for x in g),
            'missingLocal': sum(x is None for x in l), 'unresolvedLocal': 0}


def _group(rows, field):
    labels = list(dict.fromkeys(str(row.get(field) or 'Non specificato') for row in rows))
    return [{'label':label, 'rows':[row for row in rows if str(row.get(field) or 'Non specificato') == label],
             **_summary([row for row in rows if str(row.get(field) or 'Non specificato') == label])}
            for label in labels]


def report_fixture():
    rows = []
    for index, year in enumerate([2027, 2028, 2028, 2029]):
        rows.append({'key':f'Remediations:{index+4}', 'sheet':'Remediations', 'excelRow':index+4,
                     'id':'R.2' if index in (1,2) else None,
                     'name':f'Fictional remediation {index}', 'year':year,
                     'owner':'Supplier A' if index%2 else 'Supplier B',
                     'domain':'Governance' if index%2 else 'Security',
                     'globalBudget':None if index==3 else [1000.15,2000,3000][index],
                     'displayLocal':None if index==2 else [1380.25,1000,0,0][index],
                     'localTotal':810 if index==2 else [1380.25,1000,0,0][index],
                     'localComplete':None if index==3 else 100, 'localBusiness':0,
                     'globalDescription':'Original Global text αβ\n'+'EXACT_SOURCE_WORD '*600 if index==0 else 'Global original',
                     'localDescription':'Local original </script><img> & "quote"',
                     'applicableCountries':'All', 'localFormula':f'=J{index+4}*13+K{index+4}*8',
                     'priority':'yes','nis2':'Yes','allocationStatus':'ambiguous' if index==2 else 'mapped'})
    country_rows=deepcopy(rows)
    for row in country_rows:
        row['displayLocal']=100 if row['displayLocal'] is not None else None
    country_totals=_summary(country_rows);country_totals['global']=None
    country_groups=_group(country_rows,'year')
    for group in country_groups:group['global']=None
    return {'projectName':'Fictional project', 'source':{'filename':'fictional.xlsx','sha256':'a'*64},
            'filters':{'sheets':['Remediations'],'years':['2027','2028','2029'],'entities':['Entity 01']},
            'scope':'all','rows':rows,'totals':_summary(rows),
            'byYear':_group(rows,'year'),'byDomain':_group(rows,'domain'),'byOwner':_group(rows,'owner'),
            'countries':[{'id':'Entity 01','name':'Entity 01','rows':country_rows,'totals':country_totals,
                          'byYear':country_groups,'byDomain':_group(country_rows,'domain')}],
            'notes':['A source ID is repeated; both investments are retained.','An entity allocation is uncertain.']}


def texts(slide):
    return '\n'.join(shape.text for shape in slide.shapes if shape.has_text_frame)


def named_shape(slide, name):
    return next(shape for shape in slide.shapes if shape.name == name)


def contrast(first, second):
    def luminance(value):
        channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
        linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4
                  for channel in channels]
        return sum(channel * weight for channel, weight in zip(linear, (.2126, .7152, .0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + .05) / (dark + .05)


def titles(presentation):
    return [named_shape(slide, 'dvt-title').text for slide in presentation.slides]


def full_bleed_gradient(slide, presentation):
    for shape in slide.shapes:
        if (shape.left, shape.top, shape.width, shape.height) != (
                0, 0, presentation.slide_width, presentation.slide_height):
            continue
        properties = shape._element.find(qn('p:spPr'))
        if properties is not None:
            gradient = properties.find(qn('a:gradFill'))
            if gradient is not None:
                return gradient
    return None


def is_white_base(slide, presentation):
    for shape in slide.shapes:
        if (shape.left, shape.top, shape.width, shape.height) != (
                0, 0, presentation.slide_width, presentation.slide_height):
            continue
        properties = shape._element.find(qn('p:spPr'))
        if properties is not None:
            color = properties.find(qn('a:solidFill'))
            if color is not None and color.find(qn('a:srgbClr')) is not None:
                return color.find(qn('a:srgbClr')).get('val') == 'FFFFFF'
    try:
        return str(slide.background.fill.fore_color.rgb) == 'FFFFFF'
    except (AttributeError, TypeError):
        return False


def original_row_payloads(presentation):
    marker = 'RIGHE ORIGINALI COMPLETE — nessuna deduplicazione o modifica dei testi:\n'
    blocks = []
    for slide in presentation.slides:
        note = slide.notes_slide.notes_text_frame.text
        if marker in note:
            blocks.append(json.loads(note.split(marker, 1)[1]))
    return blocks


def stress_report():
    report = report_fixture()
    for index in range(80):
        row = deepcopy(report['rows'][0])
        row.update(key=f'OT:{index + 1}', name=f'Extra remediation {index}',
                   domain=f'Domain {index}', owner=f'Owner {index}', year=2030 + index,
                   globalDescription=f'Original Global description {index}',
                   localDescription=f'Original Local description {index}')
        report['rows'].append(row)
    report['totals'] = _summary(report['rows'])
    for key, field in [('byYear', 'year'), ('byDomain', 'domain'), ('byOwner', 'owner')]:
        report[key] = _group(report['rows'], field)
    for index in range(99):
        country = deepcopy(report['countries'][0])
        country.update(id=f'Entity {index + 2:03}', name=f'Entity {index + 2:03}')
        report['countries'].append(country)
    return report


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = report_fixture()
        cls.content = create_presentation(cls.report)
        cls.presentation = Presentation(BytesIO(cls.content))

    def test_standard_widescreen_pptx_all_shapes_fit_and_slide_limit(self):
        self.assertTrue(self.content.startswith(b'PK'))
        with ZipFile(BytesIO(self.content)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn('ppt/presentation.xml', archive.namelist())
        self.assertAlmostEqual(self.presentation.slide_width / self.presentation.slide_height, 16 / 9, places=5)
        self.assertLessEqual(len(self.presentation.slides), 15)
        for slide in self.presentation.slides:
            for shape in slide.shapes:
                self.assertGreaterEqual(shape.left, 0)
                self.assertGreaterEqual(shape.top, 0)
                self.assertLessEqual(shape.left + shape.width, self.presentation.slide_width + 3)
                self.assertLessEqual(shape.top + shape.height, self.presentation.slide_height + 3)

    def test_sections_follow_cover_budget_years_country_and_remediation(self):
        headings = titles(self.presentation)
        self.assertEqual(headings[0].replace('\n', ' '), 'Piano di remediation')
        self.assertEqual(headings[1], 'Budget')
        sections = ['Budget', 'Anni', 'Country / legal entity', 'Remediation']
        positions = [headings.index(title) for title in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(positions[0], headings.index('Budget per anno'))
        self.assertLess(headings.index('Budget per owner'), positions[1])
        self.assertLess(positions[1], headings.index('2027 · Budget e remediation'))
        self.assertLess(headings.index('2029 · Budget e remediation'), positions[2])
        self.assertLess(positions[2], headings.index('Budget Local per country e anno'))
        self.assertLess(headings.index('Budget Local per country e anno'), positions[3])
        self.assertLess(positions[3], headings.index('Remediation per anno e dominio'))
        self.assertLess(headings.index('Remediation per anno e dominio'), headings.index('Remediation per investimento'))
        # A separator introduces a section using only its title and the footer.
        footer_names = {'dvt-copyright', 'dvt-classification', 'dvt-page-number'}
        for title in sections:
            slide = self.presentation.slides[headings.index(title)]
            body = [shape.text for shape in slide.shapes
                    if shape.has_text_frame and shape.text.strip() and shape.name not in footer_names]
            self.assertEqual(body, [title])

    def test_native_editable_annual_chart_preserves_cents_and_missing(self):
        charts = [shape.chart for slide in self.presentation.slides for shape in slide.shapes if shape.has_chart]
        self.assertTrue(charts)
        chart = charts[0]
        self.assertEqual([series.name for series in chart.series], ['Global', 'Local'])
        self.assertEqual(list(chart.series[0].values), [1000.15, 5000.0, None])
        self.assertEqual(list(chart.series[1].values), [1380.25, 1000.0, 0.0])
        self.assertEqual([c.label for c in chart.plots[0].categories], ['2027', '2028', '2029'])
        self.assertFalse(any(shape.shape_type == 13 for slide in self.presentation.slides for shape in slide.shapes))

    def test_every_row_and_original_text_are_retained_in_two_remediation_notes(self):
        blocks = original_row_payloads(self.presentation)
        self.assertEqual(len(blocks), 2)
        self.assertEqual([row for block in blocks for row in block], self.report['rows'])
        notes = '\n'.join(json.dumps(block, ensure_ascii=False) for block in blocks)
        self.assertEqual(notes.count('"id": "R.2"'), 2)
        self.assertEqual(notes.count('EXACT_SOURCE_WORD'), 600)
        self.assertIn('Original Global text αβ', notes)
        for field in ['localComplete', 'localBusiness', 'localFormula', 'applicableCountries']:
            self.assertIn(field, notes)

    def test_country_does_not_get_a_fabricated_global_budget(self):
        country_slide = next(slide for slide in self.presentation.slides
                             if named_shape(slide, 'dvt-title').text == 'Budget Local per country e anno')
        body = texts(country_slide)
        self.assertIn('Global resta di gruppo', body)
        self.assertIn('Budget Local', body)
        self.assertNotIn('1.000,15 €', body)
        self.assertIn('Entity 01', body)

    def test_country_year_outside_overview_is_visible_without_fabricating_global(self):
        # Local-budget filtering can select additional source rows per entity.
        # Country columns must follow those actual rows, not just the overview.
        report = report_fixture()
        report['filters']['years'] = None
        report['filters']['localBudget'] = 'positive'
        country = report['countries'][0]
        extra = deepcopy(country['rows'][0])
        extra.update(key='OT:2035', year=2035, id='R.country-extra',
                     name='Source row outside the overview', globalBudget=987654.32,
                     displayLocal=456.78)
        country['rows'].append(extra)
        country['totals'] = _summary(country['rows'])
        country['totals']['global'] = None
        country['totals']['selected'] = country['totals']['local']
        country['byYear'] = _group(country['rows'], 'year')
        country['byDomain'] = _group(country['rows'], 'domain')
        for group in country['byYear'] + country['byDomain']:
            group['global'] = None
            group['selected'] = group['local']
            group['missingGlobal'] = 0
        original = deepcopy(report)
        presentation = Presentation(BytesIO(create_presentation(report)))
        self.assertEqual(report, original)
        self.assertLessEqual(len(presentation.slides), 15)
        country_slide = next(slide for slide in presentation.slides
                             if named_shape(slide, 'dvt-title').text == 'Budget Local per country e anno')
        body = texts(country_slide)
        self.assertIn('2035', body)
        self.assertIn('456,78 €', body)
        self.assertNotIn('987.654,32 €', body)
        self.assertIn('Global resta di gruppo', body)
        self.assertIn('OT:2035', country_slide.notes_slide.notes_text_frame.text)
        chart = next(shape.chart for slide in presentation.slides for shape in slide.shapes if shape.has_chart)
        self.assertNotIn('2035', [category.label for category in chart.plots[0].categories])
        blocks = original_row_payloads(presentation)
        self.assertEqual([row for block in blocks for row in block], report['rows'])

    def test_scopes_change_annual_series_without_changing_source_notes(self):
        for scope, name in [('global', 'Global'), ('local', 'Local')]:
            report = deepcopy(self.report)
            report['scope'] = scope
            for group in report['byYear']:
                group['selected'] = group[scope]
            presentation = Presentation(BytesIO(create_presentation(report)))
            chart = next(shape.chart for slide in presentation.slides for shape in slide.shapes if shape.has_chart)
            self.assertEqual([series.name for series in chart.series], [name])
            blocks = original_row_payloads(presentation)
            self.assertEqual([row for block in blocks for row in block], report['rows'])

    def test_large_projects_stay_within_15_slides_and_preserve_all_source_data(self):
        report = stress_report()
        original = deepcopy(report)
        presentation = Presentation(BytesIO(create_presentation(report)))
        self.assertLessEqual(len(presentation.slides), 15)
        self.assertEqual(report, original)
        blocks = original_row_payloads(presentation)
        self.assertEqual(len(blocks), 2)
        self.assertEqual([row for block in blocks for row in block], report['rows'])
        headings = titles(presentation)
        annual = [heading for heading in headings if '· Budget e remediation' in heading]
        self.assertLessEqual(len(annual), 3)
        self.assertIn('Altri anni · Budget e remediation', annual)
        country_slides = [slide for slide in presentation.slides
                          if named_shape(slide, 'dvt-title').text == 'Budget Local per country e anno']
        self.assertLessEqual(len(country_slides), 2)
        country_notes = '\n'.join(slide.notes_slide.notes_text_frame.text for slide in country_slides)
        for country in report['countries']:
            self.assertIn(country['name'], country_notes)
        chart = next(shape.chart for slide in presentation.slides for shape in slide.shapes if shape.has_chart)
        self.assertLessEqual(len(chart.plots[0].categories), 8)
        self.assertIn('Altri anni', [category.label for category in chart.plots[0].categories])
        self.assertAlmostEqual(sum(value for value in chart.series[0].values if value is not None),
                               report['totals']['global'])
        self.assertAlmostEqual(sum(value for value in chart.series[1].values if value is not None),
                               report['totals']['local'])

    def test_export_theme_uses_reference_fonts_and_palette(self):
        from lxml import etree
        ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        with ZipFile(BytesIO(self.content)) as archive:
            theme = etree.fromstring(archive.read('ppt/theme/theme1.xml'))
        self.assertEqual(theme.find('.//a:majorFont/a:latin', ns).get('typeface'), 'KPMG Bold')
        self.assertEqual(theme.find('.//a:minorFont/a:latin', ns).get('typeface'), 'Arial')
        self.assertEqual(theme.find('.//a:clrScheme/a:accent2/a:srgbClr', ns).get('val'), '00B8F5')
        self.assertEqual(theme.find('.//a:clrScheme/a:accent3/a:srgbClr', ns).get('val'), '7213EA')

    def test_reference_typography_and_content_title_position(self):
        heading = titles(self.presentation).index('Budget per anno')
        title = named_shape(self.presentation.slides[heading], 'dvt-title')
        self.assertAlmostEqual(title.left / 914400, .8385, places=4)
        self.assertAlmostEqual(title.top / 914400, .4722, places=4)
        self.assertAlmostEqual(title.width / 914400, 11.6163, places=4)
        self.assertEqual(title.text_frame.paragraphs[0].font.name, 'KPMG Bold')
        self.assertEqual(title.text_frame.paragraphs[0].font.size.pt, 40)
        cover = named_shape(self.presentation.slides[0], 'dvt-title')
        self.assertEqual(cover.text_frame.paragraphs[0].font.size.pt, 88)
        self.assertAlmostEqual(cover.top / 914400, 1.60, places=3)

    def test_gradient_is_reserved_for_cover_and_section_dividers(self):
        dividers = {'Budget', 'Anni', 'Country / legal entity', 'Remediation'}
        for page, slide in enumerate(self.presentation.slides):
            heading = named_shape(slide, 'dvt-title').text
            dark = page == 0 or heading in dividers
            gradient = full_bleed_gradient(slide, self.presentation)
            with self.subTest(title=heading):
                if dark:
                    self.assertIsNotNone(gradient)
                    stops = gradient.find(qn('a:gsLst'))
                    self.assertEqual([stop.get('pos') for stop in stops], ['0', '100000'])
                    self.assertEqual([stop.find(qn('a:srgbClr')).get('val') for stop in stops],
                                     ['7213EA', '1E49E2'])
                    self.assertEqual(gradient.find(qn('a:lin')).get('ang'), '0')
                else:
                    self.assertIsNone(gradient)
                    self.assertTrue(is_white_base(slide, self.presentation))

    def test_native_text_and_icon_gradients_use_valid_drawingml_order(self):
        gradients = []
        for slide in self.presentation.slides:
            title = named_shape(slide, 'dvt-title')
            for paragraph in title.text_frame.paragraphs:
                properties = paragraph._p.find(qn('a:pPr')).find(qn('a:defRPr'))
                fill = properties.find(qn('a:gradFill'))
                if fill is not None:
                    gradients.append(fill)
                    self.assertLess(list(properties).index(fill),
                                    list(properties).index(properties.find(qn('a:latin'))))
        self.assertTrue(gradients)
        icons = [shape for slide in self.presentation.slides for shape in slide.shapes
                 if shape.name.startswith('dvt-icon-')]
        self.assertTrue(icons)
        for icon in icons:
            self.assertIsNotNone(icon._element.find('.//' + qn('a:custGeom')))
            line = icon._element.find(qn('p:spPr')).find(qn('a:ln'))
            self.assertIsNotNone(line.find(qn('a:gradFill')))

    def test_every_slide_has_reference_footer_in_correct_color(self):
        copyright = ('©2026 Copyright owned by one or more of the KPMG International entities.\n'
                     'KPMG International entities provide no services to clients. All rights reserved.')
        for page, slide in enumerate(self.presentation.slides, 1):
            dark = full_bleed_gradient(slide, self.presentation) is not None
            with self.subTest(page=page):
                logo = named_shape(slide, 'dvt-kpmg-logo')
                self.assertEqual((logo.left, logo.top, logo.width, logo.height),
                                 (766762, 6266996, 484832, 194706))
                self.assertIsNotNone(logo._element.find('.//' + qn('a:custGeom')))
                self.assertIsNotNone(logo._element.find('.//' + qn('a:pathLst')))
                colors = [node.get('val') for node in logo._element.iter(qn('a:srgbClr'))]
                self.assertTrue(colors)
                self.assertEqual(set(colors), {'FFFFFF' if dark else '00338D'})
                footer = named_shape(slide, 'dvt-copyright')
                self.assertEqual(footer.text, copyright)
                self.assertAlmostEqual(footer.left / 914400, 1.4928, places=4)
                self.assertAlmostEqual(footer.top / 914400, 6.8537, places=4)
                self.assertEqual(footer.text_frame.paragraphs[0].font.size.pt, 6)
                self.assertEqual(str(footer.text_frame.paragraphs[0].font.color.rgb),
                                 'FFFFFF' if dark else '808080')
                self.assertNotIn('©2024', texts(slide))
                classification = named_shape(slide, 'dvt-classification')
                self.assertEqual(classification.text, 'Document Classification: KPMG Confidential')
                self.assertAlmostEqual(classification.left / 914400, 10.0655, places=4)
                self.assertAlmostEqual(classification.top / 914400, 6.8849, places=4)
                number = named_shape(slide, 'dvt-page-number')
                self.assertEqual(number.text, str(page))
                self.assertAlmostEqual(number.left / 914400, 12.229605, places=5)
                self.assertAlmostEqual(number.top / 914400, 6.853671, places=5)
                self.assertEqual(number.text_frame.paragraphs[0].font.size.pt, 10)
                self.assertEqual(str(number.text_frame.paragraphs[0].font.color.rgb),
                                 'FFFFFF' if dark else '1E49E2')

    def test_annual_chart_is_transparent_and_labels_contrast_on_white(self):
        chart = next(shape.chart for slide in self.presentation.slides for shape in slide.shapes if shape.has_chart)
        for parent in (chart._chartSpace, chart._chartSpace.find('.//' + qn('c:plotArea'))):
            properties = parent.find(qn('c:spPr'))
            self.assertIsNotNone(properties.find(qn('a:noFill')))
            self.assertIsNone(properties.find(qn('a:solidFill')))
        label_color = str(chart.plots[0].data_labels.font.color.rgb)
        for series in chart.series:
            self.assertGreaterEqual(contrast(label_color, str(series.format.fill.fore_color.rgb)), 4.5)
        for font in (chart.legend.font, chart.category_axis.tick_labels.font,
                     chart.value_axis.tick_labels.font):
            self.assertGreaterEqual(contrast(str(font.color.rgb), 'FFFFFF'), 4.5)

    def test_partial_rows_preserve_available_selected_total(self):
        summary = {'count':2,'global':100,'local':50,'selected':150,
                   'missingGlobal':1,'missingLocal':1,'missingSelected':2,'selectedUnknown':False}
        self.assertEqual(_selected_value(summary, 'all'), 150)
        summary = {'count':1,'global':0,'local':0,'selected':0,
                   'missingGlobal':1,'missingLocal':0,'missingSelected':1,'selectedUnknown':False}
        self.assertEqual(_selected_value(summary, 'all'), 0)
        summary.update(missingLocal=1, selectedUnknown=True)
        self.assertIsNone(_selected_value(summary, 'all'))

    def test_empty_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Non ci sono remediation'):
            create_presentation({'rows':[]})


if __name__ == '__main__':
    unittest.main()
