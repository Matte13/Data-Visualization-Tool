"""Optional metadata must not alter the workbook's financial data."""
import unittest
from app.workbook import parse_workbook
from fixtures import make_workbook
from test_workbook import edited_cell


def investment_workbook():
    data = make_workbook()
    for coordinate, value in {'T3':'Capex/Opex','U3':'Rischi','V3':'Impatto',
                               'T4':' CAPEX ','U4':'Cyber','V4':' ALTO ',
                               'T5':'Opex','U5':'Compliance','V5':'Medio'}.items():
        data = edited_cell(data, 2, coordinate, text=value)
    return data


class InvestmentFieldsTests(unittest.TestCase):
    def test_optional_headers_and_values_leave_budgets_unchanged(self):
        original = parse_workbook(make_workbook(), 'old.xlsx')
        result = parse_workbook(investment_workbook(), 'new.xlsx')
        self.assertEqual(result['totals'], original['totals'])
        self.assertEqual(result['entities'], original['entities'])
        self.assertEqual(result['rows'][0]['capexOpex'], 'Capex')
        self.assertEqual(result['rows'][0]['risk'], 'Cyber')
        self.assertEqual(result['rows'][0]['impact'], 'Alto')
        for before, after in zip(original['rows'], result['rows']):
            self.assertEqual({k:v for k,v in before.items() if k not in ('capexOpex','risk','impact')},
                             {k:v for k,v in after.items() if k not in ('capexOpex','risk','impact')})
        self.assertEqual(result['rows'][2]['impact'], '')
        self.assertNotIn('impact', result['rows'][-1])

    def test_duplicate_headers_reject_ambiguous_import(self):
        data = edited_cell(investment_workbook(), 2, 'W3', text='Rischi')
        with self.assertRaisesRegex(ValueError, 'duplicata'):
            parse_workbook(data, 'duplicate.xlsx')

    def test_unknown_source_values_are_preserved(self):
        data = edited_cell(investment_workbook(), 2, 'V4', text='Da validare')
        self.assertEqual(parse_workbook(data,'unknown.xlsx')['rows'][0]['impact'], 'Da validare')
