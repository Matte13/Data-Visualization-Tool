import unittest
from app.workbook import parse_workbook
from consolidated_fixtures import make_rated_impact_workbook, make_consolidated_workbook
from test_workbook import edited_cell


class RatedImpactsTests(unittest.TestCase):
    def test_latest_columns_and_budget_invariants(self):
        latest=parse_workbook(make_rated_impact_workbook(),'latest.xlsx')
        old=parse_workbook(make_consolidated_workbook(),'old.xlsx')
        self.assertEqual(len(latest['rows']),len(old['rows']))
        for new,previous in zip(latest['rows'],old['rows']):
            for field in ('globalBudget','localTotal','localFormula','allocations','riskTypes','riskLevel','capexOpex','capexOpexNote'):
                self.assertEqual(new[field],previous[field],field)
            self.assertEqual(new['impactLevels'],{'Reputational':'Low','Regulatory':'High','Economic':'Medium','Operational':'High'})
            self.assertEqual(new['impactTypes'],list(new['impactLevels']))

    def test_column_o_has_no_effect_and_missing_rating_is_not_inferred(self):
        content=make_rated_impact_workbook()
        changed=edited_cell(content,4,'O2',text='PRIVATE REASONING IGNORE')
        self.assertEqual(parse_workbook(content,'x.xlsx')['rows'],parse_workbook(changed,'x.xlsx')['rows'])
        changed=edited_cell(changed,4,'P2',text='')
        row=parse_workbook(changed,'x.xlsx')['rows'][0]
        self.assertEqual(row['impactLevels']['Reputational'],'')
        self.assertEqual(row['riskLevel'],'High')
