"""Financial and metadata invariants of the new consolidated input."""
from hashlib import sha256
import unittest
from app.workbook import parse_workbook
from consolidated_fixtures import make_consolidated_workbook
from test_workbook import edited_cell


class ConsolidatedWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content=make_consolidated_workbook()
        cls.document=parse_workbook(cls.content,'consolidated.xlsx')

    def test_consolidated_is_the_only_financial_source(self):
        d=self.document
        self.assertEqual(len(d['rows']),7)
        self.assertEqual(sum(x['globalBudget'] or 0 for x in d['rows']),7340)
        self.assertEqual(sum(x['localTotal'] or 0 for x in d['rows']),3682)
        self.assertEqual(d['source']['sha256'],sha256(self.content).hexdigest())
        self.assertEqual(d['totals']['OT']['rows'],2)
        self.assertTrue(all(r['sourceSheet']=='All Remediations' for r in d['rows']))

    def test_multiple_attributes_remain_on_one_row_with_source_notes(self):
        row=self.document['rows'][0]
        self.assertEqual(row['riskTypes'],['Cyber','Compliance'])
        self.assertEqual(row['impactTypes'],['Economic','Regulatory'])
        self.assertEqual(row['riskLevel'],'High')
        self.assertEqual(row['impact'],'')
        self.assertEqual(row['capexOpex'],'Capex')
        self.assertEqual(row['owner'],'Advisor')
        self.assertEqual(row['capexOpexNote'],'If implemented on an automated platform.')
        self.assertEqual(row['globalDescription'],'Original global text 4')
        self.assertEqual(row['detailSources'],[{'sheet':'CMA, WIFI, VA Remediations','excelRow':4}])

    def test_annual_duplicate_ids_keep_both_years_and_unallocated_group_totals(self):
        rows=[r for r in self.document['rows'] if r['id']=='R.N']
        self.assertEqual([r['year'] for r in rows],[2027,2028])
        self.assertEqual(sum(r['globalBudget']+r['localTotal'] for r in rows),332)
        self.assertTrue(all(not r['allocations'] for r in rows))
        self.assertEqual(len({r['key'] for r in rows}),2)

    def test_country_allocations_follow_groups_and_keep_real_formula(self):
        first=self.document['rows'][0]
        self.assertEqual(sum(a['amount'] for a in first['allocations']),1380)
        self.assertEqual(first['localFormula'],'=E2*13+F2*8')
        ot=next(r for r in self.document['rows'] if r['id']=='R.OT.1')
        self.assertEqual(len(ot['allocations']),6)
        self.assertEqual(sum(a['amount'] for a in ot['allocations']),120)

    def test_bad_formula_cache_rejects_and_cross_row_reference_never_allocates(self):
        wrong=edited_cell(self.content,4,'G2',formula='E2*13+F2*8',value=1)
        with self.assertRaisesRegex(ValueError,'non coincide'):
            parse_workbook(wrong,'bad.xlsx')
        linked=edited_cell(self.content,4,'G8',formula='$E$7*7+F8*1',value=96)
        d=parse_workbook(linked,'cross-row.xlsx')
        row=next(r for r in d['rows'] if r['excelRow']==8)
        self.assertEqual(row['localTotal'],96)
        self.assertEqual(row['allocations'],[])
        self.assertTrue(any(i['code']=='cross-row-local-formula' for i in d['issues']))

    def test_persisted_current_source_reopens_without_changing_original_bytes(self):
        from pathlib import Path
        import tempfile
        from app.server import WorkbookStore
        with tempfile.TemporaryDirectory() as directory:
            store=WorkbookStore(Path(directory))
            key=store.create(self.content,'consolidated.xlsx','Consolidated')['project']['id']
            restarted=WorkbookStore(Path(directory))
            self.assertEqual(restarted.source(key),(self.content,'consolidated.xlsx'))
            self.assertEqual(restarted.snapshot(key)['rows'],self.document['rows'])

    def test_impact_types_do_not_determine_risk_level(self):
        changed=edited_cell(self.content,4,'O2',text='Low')
        row=parse_workbook(changed,'low.xlsx')['rows'][0]
        self.assertEqual(row['riskLevel'],'Low')
        self.assertEqual(row['impactTypes'],['Economic','Regulatory'])
        self.assertEqual(row['globalBudget'],1000)
