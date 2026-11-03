"""PPTX structure, editable charts, exact amounts and complete source notes."""
from copy import deepcopy
from io import BytesIO
import json
import unittest
from zipfile import ZipFile

from pptx import Presentation

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


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=report_fixture()
        cls.content=create_presentation(cls.report)
        cls.presentation=Presentation(BytesIO(cls.content))

    def test_standard_widescreen_pptx_and_all_shapes_fit(self):
        self.assertTrue(self.content.startswith(b'PK'))
        with ZipFile(BytesIO(self.content)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn('ppt/presentation.xml',archive.namelist())
        self.assertAlmostEqual(self.presentation.slide_width / self.presentation.slide_height,16/9,places=5)
        for slide in self.presentation.slides:
            for shape in slide.shapes:
                self.assertGreaterEqual(shape.left,0);self.assertGreaterEqual(shape.top,0)
                self.assertLessEqual(shape.left+shape.width,self.presentation.slide_width+3)
                self.assertLessEqual(shape.top+shape.height,self.presentation.slide_height+3)

    def test_drilldown_order_is_group_then_year_then_country_then_appendix(self):
        titles=[slide.shapes[1].text if len(slide.shapes)>1 and slide.shapes[1].has_text_frame else '' for slide in self.presentation.slides]
        self.assertEqual(titles[0].replace('\n',' '),'Piano di remediation')
        self.assertLess(titles.index('Budget per anno'),titles.index('2027 · Budget e remediation'))
        self.assertLess(titles.index('2029 · Budget e remediation'),titles.index('Country · Budget Local per anno'))
        self.assertLess(titles.index('Country · Budget Local per anno'),titles.index('Remediation selezionate'))

    def test_native_editable_annual_chart_preserves_cents_and_missing(self):
        charts=[shape.chart for slide in self.presentation.slides for shape in slide.shapes if shape.has_chart]
        self.assertTrue(charts)
        chart=charts[0]
        self.assertEqual([series.name for series in chart.series],['Global','Local'])
        self.assertEqual(list(chart.series[0].values),[1000.15,5000.0,None])
        self.assertEqual(list(chart.series[1].values),[1380.25,1000.0,0.0])
        self.assertEqual([c.label for c in chart.plots[0].categories],['2027','2028','2029'])
        self.assertFalse(any(shape.shape_type==13 for slide in self.presentation.slides for shape in slide.shapes))

    def test_every_row_and_all_original_text_are_retained_in_appendix_notes(self):
        appendix=[slide for slide in self.presentation.slides if 'Remediation selezionate' in texts(slide)]
        source_rows=[]
        for slide in appendix:
            note=slide.notes_slide.notes_text_frame.text
            source_rows.extend(json.loads(note.split('RIGHE ORIGINALI COMPLETE — nessuna deduplicazione o modifica dei testi:\n',1)[1]))
        self.assertEqual(source_rows,self.report['rows'])
        notes='\n'.join(slide.notes_slide.notes_text_frame.text for slide in appendix)
        self.assertEqual(notes.count('"id": "R.2"'),2)
        self.assertEqual(notes.count('EXACT_SOURCE_WORD'),600)
        self.assertIn('Original Global text αβ',notes)
        for field in ['localComplete','localBusiness','localFormula','applicableCountries']:
            self.assertIn(field,notes)

    def test_country_does_not_get_a_fabricated_global_budget(self):
        country_slide=next(slide for slide in self.presentation.slides if 'Country · Budget Local per anno' in texts(slide))
        body=texts(country_slide)
        self.assertIn('Global resta di gruppo',body)
        self.assertIn('Budget Local',body)
        self.assertNotIn('1.000,15 €',body)
        self.assertIn('Entity 01',body)

    def test_scopes_change_annual_series_without_changing_source_notes(self):
        for scope,name in [('global','Global'),('local','Local')]:
            report=deepcopy(self.report);report['scope']=scope
            for group in report['byYear']:
                group['selected']=group[scope]
            content=create_presentation(report);prs=Presentation(BytesIO(content))
            chart=next(shape.chart for slide in prs.slides for shape in slide.shapes if shape.has_chart)
            self.assertEqual([series.name for series in chart.series],[name])
            all_notes='\n'.join(slide.notes_slide.notes_text_frame.text for slide in prs.slides)
            self.assertIn('EXACT_SOURCE_WORD',all_notes)

    def test_many_categories_years_and_countries_are_paginated(self):
        report=report_fixture()
        extra=[]
        for index in range(20):
            row=deepcopy(report['rows'][0]);row.update(key=f'OT:{index+1}',name=f'Extra remediation {index}',domain=f'Domain {index}',owner=f'Owner {index}',year=2030+index)
            extra.append(row)
        report['rows']+=extra;report['totals']=_summary(report['rows'])
        for key,field in [('byYear','year'),('byDomain','domain'),('byOwner','owner')]:report[key]=_group(report['rows'],field)
        content=create_presentation(report);prs=Presentation(BytesIO(content))
        appendix_notes='\n'.join(slide.notes_slide.notes_text_frame.text for slide in prs.slides if 'Remediation selezionate' in texts(slide))
        for row in report['rows']:self.assertIn('"key": "'+row['key']+'"',appendix_notes)
        chart_years=[category.label for slide in prs.slides for shape in slide.shapes if shape.has_chart for category in shape.chart.plots[0].categories]
        self.assertEqual(set(chart_years),{str(row['year']) for row in report['rows']})
        self.assertEqual(len(chart_years),23)

    def test_export_theme_uses_reference_fonts_and_palette(self):
        from lxml import etree
        ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
        with ZipFile(BytesIO(self.content)) as archive:
            theme=etree.fromstring(archive.read('ppt/theme/theme1.xml'))
        self.assertEqual(theme.find('.//a:majorFont/a:latin',ns).get('typeface'),'KPMG Bold')
        self.assertEqual(theme.find('.//a:minorFont/a:latin',ns).get('typeface'),'Arial')
        self.assertEqual(theme.find('.//a:clrScheme/a:accent2/a:srgbClr',ns).get('val'),'00B8F5')
        self.assertEqual(theme.find('.//a:clrScheme/a:accent3/a:srgbClr',ns).get('val'),'7213EA')

    def test_reference_typography_and_content_title_position(self):
        title=self.presentation.slides[1].shapes[1]
        self.assertAlmostEqual(title.left/914400,1.083,places=3)
        self.assertAlmostEqual(title.top/914400,.472,places=3)
        self.assertAlmostEqual(title.width/914400,11.167,places=3)
        self.assertEqual(title.text_frame.paragraphs[0].font.name,'KPMG Bold')
        self.assertEqual(title.text_frame.paragraphs[0].font.size.pt,48)
        cover=self.presentation.slides[0].shapes[1]
        self.assertEqual(cover.text_frame.paragraphs[0].font.size.pt,96)
        self.assertAlmostEqual(cover.top/914400,1.469,places=3)

    def test_partial_rows_preserve_available_selected_total(self):
        summary={'count':2,'global':100,'local':50,'selected':150,
                 'missingGlobal':1,'missingLocal':1,'missingSelected':2,'selectedUnknown':False}
        self.assertEqual(_selected_value(summary,'all'),150)
        summary={'count':1,'global':0,'local':0,'selected':0,
                 'missingGlobal':1,'missingLocal':0,'missingSelected':1,'selectedUnknown':False}
        self.assertEqual(_selected_value(summary,'all'),0)
        summary.update(missingLocal=1,selectedUnknown=True)
        self.assertIsNone(_selected_value(summary,'all'))

    def test_empty_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Non ci sono remediation'):
            create_presentation({'rows':[]})


if __name__=='__main__':unittest.main()
