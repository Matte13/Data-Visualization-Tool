"""Independent reconciliation cases: OT deltas, special recipients and unknowns."""
from copy import deepcopy
import unittest

from app.budget_breakdown import budget_breakdown


def fixture():
    entities = [
        {'id': 'Complete OT', 'localCategory': 'complete-ot'},
        {'id': 'Complete', 'localCategory': 'complete'},
        {'id': 'Business', 'localCategory': 'business'},
    ]
    def row(key, global_, local, allocations=(), *, sheet='Remediations', status='mapped', ident=None):
        return {'key': key, 'id': ident, 'sheet': sheet, 'globalBudget': global_, 'localTotal': local,
                'allocationStatus': status,
                'allocations': [{'entityId': entity, 'amount': amount} for entity, amount in allocations]}
    rows = [
        row('Remediations:4', 100, 60, [('Complete OT', 10), ('Complete', 20), ('Business', 30)]),
        # A special Complete-column rate also applies to an entity classified Business.
        row('Remediations:5', 0, 16, [('Complete', 8), ('Business', 8)]),
        row('OT:2', 50, 12, [('Complete OT', 12)], sheet='OT'),
        row('Remediations:26', 70, 72, status='ambiguous', ident='R.23'),
        row('Remediations:27', 70, 252, status='ambiguous', ident='R.23'),
        row('Remediations:29', None, 0, [('Complete OT', None), ('Complete', None), ('Business', 0)]),
        row('Remediations:30', None, None, status='unavailable'),
    ]
    return rows, entities


class BudgetBreakdownTests(unittest.TestCase):
    def test_source_totals_and_ot_delta_are_each_counted_once(self):
        rows, entities = fixture()
        result = budget_breakdown(rows, entities)
        self.assertEqual((result['globalBase'], result['globalOt'], result['global']), (240, 50, 290))
        self.assertEqual((result['localBase'], result['localOt'], result['localTotal']), (400, 12, 412))
        self.assertEqual((result['baseCount'], result['otCount']), (6, 1))
        categories = {item['id']: item for item in result['categories']}
        self.assertEqual((categories['complete-ot']['base'], categories['complete-ot']['ot'], categories['complete-ot']['total']), (10, 12, 22))
        self.assertEqual(categories['complete']['total'], 28)
        self.assertEqual(categories['business']['total'], 38)
        self.assertEqual(sum(item['total'] for item in result['categories']) + result['unallocated'], 412)

    def test_same_id_rows_stay_in_totals_but_uncertain_geography_is_unallocated(self):
        rows, entities = fixture()
        result = budget_breakdown(rows, entities)
        self.assertEqual(result['unallocatedBase'], 324)
        self.assertEqual(result['unallocatedOt'], 0)
        self.assertEqual(result['unresolvedSource'], 324)
        self.assertEqual(result['rowCount'], len(rows))
        self.assertEqual(result['globalBase'], 100 + 70 + 70)

    def test_business_category_follows_entity_not_cost_column(self):
        rows, entities = fixture()
        result = budget_breakdown(rows, entities, ['Business'])
        business = next(item for item in result['categories'] if item['id'] == 'business')
        self.assertEqual(business['base'], 30 + 8)
        self.assertEqual(business['entityCount'], 1)
        self.assertEqual(result['localTotal'], 38)
        self.assertEqual(result['global'], 290)
        self.assertEqual(result['unallocated'], 0)
        self.assertEqual(result['unresolvedSource'], 324)

    def test_missing_and_real_zero_remain_distinct(self):
        rows, entities = fixture()
        unknown = budget_breakdown([rows[5]], entities, ['Complete OT'])
        category = unknown['categories'][0]
        self.assertEqual((category['missing'], category['known']), (1, 0))
        self.assertEqual(unknown['missingGlobal'], 1)
        zero = budget_breakdown([rows[5]], entities, ['Business'])
        category = next(item for item in zero['categories'] if item['id'] == 'business')
        self.assertEqual((category['missing'], category['known'], category['total']), (0, 1, 0))
        unavailable = budget_breakdown([rows[6]], entities)
        self.assertEqual(unavailable['missingLocal'], 1)

    def test_legacy_entities_are_not_classified_by_multipliers(self):
        rows, entities = fixture()
        for entity in entities:
            entity.pop('localCategory')
        result = budget_breakdown(rows, entities)
        self.assertFalse(result['classificationAvailable'])
        category = next(item for item in result['categories'] if item['id'] == 'unclassified')
        self.assertEqual(category['entityCount'], 3)
        self.assertEqual(category['total'], 88)
        self.assertEqual(result['unallocated'], 324)

    def test_filtered_subset_retains_global_and_only_its_allocated_ot(self):
        rows, entities = fixture()
        result = budget_breakdown(rows[:3], entities, ['Complete', 'Business'])
        self.assertEqual((result['globalBase'], result['globalOt']), (100, 50))
        self.assertEqual((result['localBase'], result['localOt']), (66, 0))
        self.assertEqual(sum(item['entityCount'] for item in result['categories']), 2)
        no_ot = budget_breakdown([row for row in rows if row['sheet'] != 'OT'], entities)
        self.assertEqual(no_ot['globalOt'], 0)
        self.assertEqual(no_ot['localOt'], 0)

    def test_inputs_are_not_mutated(self):
        rows, entities = fixture()
        before = deepcopy((rows, entities))
        result = budget_breakdown(rows, entities)
        result['categories'][0]['base'] = 999
        self.assertEqual((rows, entities), before)
