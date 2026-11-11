"""The last CMA row is included independently of companion summary formulas."""
from io import BytesIO
import re
import unittest
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET

from app.workbook import parse_workbook
from app.presentation_data import build_presentation_data
from consolidated_fixtures import make_rated_impact_workbook


def last_row_workbook(year):
    namespace='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    tag=lambda name:f'{{{namespace}}}{name}'
    output=BytesIO()
    with ZipFile(BytesIO(make_rated_impact_workbook())) as src, ZipFile(output,'w',ZIP_DEFLATED) as dest:
        for item in src.infolist():
            content=src.read(item.filename)
            settings={'xl/worksheets/sheet2.xml':('4','M'), 'xl/worksheets/sheet4.xml':('2','H')}
            if item.filename in settings:
                old,year_column=settings[item.filename]
                tree=ET.fromstring(content);data=tree.find(tag('sheetData'))
                row=next(row for row in data if row.get('r')==old)
                data.remove(row);row.set('r','63');data.append(row)
                for cell in row:
                    cell.set('r',re.sub(r'\d+$','63',cell.get('r')))
                    formula=cell.find(tag('f'))
                    if formula is not None:
                        formula.text=re.sub(r'([A-Z]+)'+old+r'\b',r'\g<1>63',formula.text)
                    if cell.get('r')==year_column+'63':cell.find(tag('v')).text=str(year)
                content=ET.tostring(tree)
            dest.writestr(item,content)
    return output.getvalue()


class CmaFinalRowTests(unittest.TestCase):
    def test_last_row_survives_import_and_filtered_presentation_in_all_cma_years(self):
        for year in (2027,2028,2029):
            with self.subTest(year=year):
                document=parse_workbook(last_row_workbook(year),'synthetic-final.xlsx')
                document['project']={'id':'regression','name':'Synthetic'}
                self.assertEqual(len(document['rows']),7)
                last=next(row for row in document['rows'] if row['key']=='All Remediations:63')
                self.assertEqual(last['detailSources'],[{'sheet':'CMA, WIFI, VA Remediations','excelRow':63}])
                self.assertEqual((last['year'],last['capexOpex'],last['globalBudget'],last['localComplete'],last['localBusiness']),
                                 (year,'Capex',1000,100,10))
                report=build_presentation_data(document,{'projectId':'regression','rowKeys':[last['key']],
                    'entities':None,'scope':'all','filters':{'years':[str(year)],'capexOpex':['Capex']}})
                self.assertEqual((report['totals']['global'],report['totals']['local'],report['totals']['selected']),
                                 (1000,1380,2380))
                self.assertEqual(report['byYear'][0]['label'],str(year))
