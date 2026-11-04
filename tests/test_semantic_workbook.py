"""Category-aware import tests generated without client workbook contents."""
from collections import Counter
from hashlib import sha256
from io import BytesIO
import unittest

from openpyxl import load_workbook

from app.workbook import parse_workbook
from fixtures import make_semantic_workbook, make_workbook
from test_workbook import edited_cell


class SemanticWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = make_semantic_workbook()
        cls.document = parse_workbook(cls.data, 'semantic.xlsx')

    def test_explicit_category_partition_keeps_the_source_totals(self):
        document = self.document
        self.assertEqual(len(document['entities']), 21)
        self.assertEqual(Counter(entity['localCategory'] for entity in document['entities']),
                         {'complete-ot': 6, 'complete': 7, 'business': 8})
        self.assertEqual(document['classification'], {
            'available': True, 'source': 'LE_List',
            'counts': {'complete-ot': 6, 'complete': 7, 'business': 8, 'unclassified': 0}})
        self.assertEqual(document['totals']['Remediations']['globalBudget'], 6400)
        self.assertEqual(document['totals']['Remediations']['localTotal'], 3190)
        self.assertEqual(document['totals']['OT']['globalBudget'], 1200)
        self.assertEqual(document['totals']['OT']['localTotal'], 300)
        self.assertTrue(document['totals']['Remediations']['reference']['matches'])
        self.assertTrue(all(entity['otEligible'] == (entity['localCategory'] == 'complete-ot')
                            for entity in document['entities']))

    def test_owner_alias_is_display_only_and_raw_workbook_is_preserved(self):
        first = self.document['rows'][0]
        self.assertEqual(first['owner'], 'Advisor')
        self.assertEqual(first['sourceOwner'], ' KpMg ')
        self.assertEqual(self.document['source']['sha256'], sha256(self.data).hexdigest())
        workbook = load_workbook(BytesIO(self.data), data_only=False)
        try:
            self.assertEqual(workbook['Remediations']['Q4'].value, ' KpMg ')
        finally:
            workbook.close()
        other = next(row for row in self.document['rows'] if row['key'] == 'Remediations:5')
        self.assertEqual((other['owner'], other['sourceOwner']), ('Supplier B', 'Supplier B'))

    def test_annotations_are_not_groups_entities_or_extra_costs(self):
        plain = parse_workbook(make_semantic_workbook(notes=False), 'plain.xlsx')
        self.assertEqual(plain['entities'], self.document['entities'])
        self.assertEqual(plain['rows'], self.document['rows'])
        self.assertEqual(plain['totals'], self.document['totals'])

    def test_normalized_semantic_headers_and_declared_counts(self):
        content = edited_cell(self.data, 1, 'C1', text=' \tOt\u00a0 6 ')
        content = edited_cell(content, 1, 'D1', text='LOCAL \t BUSINESS')
        content = edited_cell(content, 1, 'E1', text='local\u00a0complete 13')
        self.assertEqual(parse_workbook(content, 'normalized.xlsx')['entities'], self.document['entities'])
        wrong = edited_cell(content, 1, 'E1', text='local complete 14')
        with self.assertRaisesRegex(ValueError, 'gruppo 14 contiene 13'):
            parse_workbook(wrong, 'wrong-count.xlsx')

    def test_legacy_numeric_groups_are_valid_without_guessed_categories(self):
        for compact, count in ((False, 21), (True, 3)):
            result = parse_workbook(make_workbook(compact=compact), 'legacy.xlsx')
            self.assertFalse(result['classification']['available'])
            self.assertEqual(result['classification']['counts']['unclassified'], count)
            self.assertTrue(all(entity['localCategory'] is None and entity['otEligible'] is None
                                for entity in result['entities']))

    def test_category_conflicts_are_rejected_without_numeric_guessing(self):
        overlapping = edited_cell(self.data, 1, 'D2', text='x')
        with self.assertRaisesRegex(ValueError, 'devono essere disgiunte'):
            parse_workbook(overlapping, 'overlap.xlsx')
        outside_complete = edited_cell(self.data, 1, 'C15', text='x')
        with self.assertRaisesRegex(ValueError, 'anche a local complete'):
            parse_workbook(outside_complete, 'outside-complete.xlsx')
        incomplete = edited_cell(self.data, 1, 'C1', text='6')
        with self.assertRaisesRegex(ValueError, 'le tre colonne'):
            parse_workbook(incomplete, 'partial-categories.xlsx')

    def test_notes_cannot_hide_orphan_memberships(self):
        content = edited_cell(self.data, 1, 'I2', text='x')
        with self.assertRaisesRegex(ValueError, 'intestazione numerica positiva'):
            parse_workbook(content, 'headerless-x.xlsx')
        content = edited_cell(self.data, 1, 'C26', text='x')
        with self.assertRaisesRegex(ValueError, 'senza nome'):
            parse_workbook(content, 'orphan-x.xlsx')

    def test_special_complete_cost_can_apply_to_business_entities(self):
        content = self.data
        # Seven Complete and two Business entities belong to this specific group.
        members = {1, 2, 3, 4, 5, 6, 7, 14, 15}
        for index in range(1, 22):
            content = edited_cell(content, 1, f'G{index + 1}', text='x' if index in members else '')
        content = edited_cell(content, 2, 'K4', value=0)
        content = edited_cell(content, 2, 'L4', formula='J4*9+K4*8', value=900)
        content = edited_cell(content, 2, 'L9', value=2710)
        result = parse_workbook(content, 'special-applicability.xlsx')
        row = result['rows'][0]
        amounts = {allocation['entityId']: allocation['amount'] for allocation in row['allocations']}
        entities = {entity['id']: entity for entity in result['entities']}
        self.assertEqual(row['allocationStatus'], 'mapped')
        self.assertEqual(row['localBusiness'], 0)
        for index in (14, 15):
            name = f'Demo Entity {index:02}'
            self.assertEqual(entities[name]['localCategory'], 'business')
            self.assertEqual(amounts[name], 100)
        self.assertEqual(sum(amounts.values()), 900)
        self.assertEqual(sum(value for name, value in amounts.items()
                             if entities[name]['localCategory'] == 'business'), 200)

    def test_nis2_like_conflicts_and_duplicate_source_rows_remain_unchanged(self):
        row = next(row for row in self.document['rows'] if row['key'] == 'Remediations:6')
        self.assertEqual(row['allocationStatus'], 'ambiguous')
        self.assertEqual(row['allocations'], [])
        repeated = [row for row in self.document['rows'] if row['id'] == 'R.2']
        self.assertEqual(len(repeated), 2)
        self.assertEqual({row['key'] for row in repeated}, {'Remediations:5', 'Remediations:6'})
        self.assertEqual(sum(row['localTotal'] for row in repeated), 1810)

    def test_ot_never_allocates_to_ineligible_entities_but_subsets_are_valid(self):
        outside = edited_cell(self.data, 3, 'G2', formula='F2*13', value=260)
        parsed = parse_workbook(outside, 'outside-ot.xlsx')
        row = next(row for row in parsed['rows'] if row['key'] == 'OT:2')
        self.assertEqual((row['localTotal'], row['allocationStatus'], row['allocations']),
                         (260, 'ambiguous', []))
        subset = edited_cell(self.data, 3, 'G2', formula='F2*5', value=100)
        parsed = parse_workbook(subset, 'subset-ot.xlsx')
        row = next(row for row in parsed['rows'] if row['key'] == 'OT:2')
        self.assertEqual(row['allocationStatus'], 'mapped')
        self.assertEqual(len(row['allocations']), 5)
        self.assertEqual(sum(allocation['amount'] for allocation in row['allocations']), 100)

    def test_empty_semantic_ot_group_does_not_invent_entities_or_costs(self):
        content = self.data
        for row in range(2, 23):
            content = edited_cell(content, 1, f'C{row}', text='')
        content = edited_cell(content, 3, 'G2', formula='F2*0', value=0)
        content = edited_cell(content, 3, 'G3', formula='F3*0', value=0)
        result = parse_workbook(content, 'no-local-ot.xlsx')
        self.assertEqual(result['classification']['counts'], {
            'complete-ot': 0, 'complete': 13, 'business': 8, 'unclassified': 0})
        self.assertEqual(result['totals']['OT']['localTotal'], 0)
        self.assertEqual(result['totals']['OT']['globalBudget'], 1200)
        self.assertTrue(all(row['allocationStatus'] == 'mapped' and row['allocations'] == []
                            for row in result['rows'] if row['sheet'] == 'OT'))


if __name__ == '__main__':
    unittest.main()
