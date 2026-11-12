"""Confirmed eight-entity NIS2 scope, never inferred from multipliers alone."""
from copy import deepcopy
import unittest
from app.consolidated import _confirmed_nis2_allocation
from app.budget_breakdown import budget_breakdown


class ConfirmedNis2AllocationTests(unittest.TestCase):
    def entities(self):
        return [{'id':name,'groups':[],'localCategory':category} for name,category in [
            ('Germania','complete'),('Spagna - Lacer','complete-ot'),('Spagna - ITF','complete-ot'),
            ('Grecia','complete'),('Francia','complete'),('Paesi Bassi & Belgio','complete'),
            ('Portogallo','complete'),('Svezia','business')]]

    def row(self,year):
        number=31 if year==2027 else 32
        return {'key':f'All Remediations:{number}','excelRow':number,'id':'R.23','sheet':'Remediations',
                'name':'NIS2 Alignment','year':year,'globalBudget':0,'localTotal':96000,
                'localComplete':12000,'localBusiness':12000,
                'localFormula':f'=$E${number}*7+F{number}*1','allocationFormula':f'=J{number}*7+K{number}*1',
                'applicableCountries':'Specific Countries:\nGermany, Spain Lacer, Spain ITF, Greece, France, Benelux, Portugal, Sweden'}

    def test_both_years_keep_source_and_assign_sweden_only_to_business(self):
        rows=[self.row(2027),self.row(2028)];entities=self.entities();original=deepcopy(rows)
        for record in rows:
            self.assertTrue(_confirmed_nis2_allocation(record,entities))
            self.assertEqual(len(record['allocations']),8)
            self.assertEqual(sum(a['amount'] for a in record['allocations']),96000)
            self.assertEqual(next(a['amount'] for a in record['allocations'] if a['entityId']=='Svezia'),12000)
        for record,previous in zip(rows,original):
            for field,value in previous.items():self.assertEqual(record[field],value)
        summary=budget_breakdown(rows,entities)
        self.assertEqual(summary['localTotal'],192000)
        self.assertEqual(summary['unallocated'],0)
        categories={c['id']:c['total'] for c in summary['categories']}
        self.assertEqual(categories['complete-ot'],48000)
        self.assertEqual(categories['complete'],120000)
        self.assertEqual(categories['business'],24000)

    def test_other_scopes_and_unconfirmed_geography_are_not_overridden(self):
        for changes in ({'id':'R.other'},{'year':2029},{'allocationFormula':'=J31*13+K31*8'},
                        {'applicableCountries':'All'},{'applicableCountries':'Germany, Sweden'}):
            record={**self.row(2027),**changes};before=deepcopy(record)
            self.assertFalse(_confirmed_nis2_allocation(record,self.entities()))
            self.assertEqual(record,before)
        self.assertFalse(_confirmed_nis2_allocation(self.row(2027),self.entities()[:-1]))

    def test_wrong_total_is_not_silently_reallocated(self):
        record={**self.row(2027),'localTotal':1}
        with self.assertRaisesRegex(ValueError,'totale Local'):_confirmed_nis2_allocation(record,self.entities())
