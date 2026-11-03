"""Public parser regression suite generated entirely from fictional workbooks."""
from io import BytesIO
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from app.workbook import parse_workbook
from fixtures import make_workbook

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def edited_cell(data, sheet, coordinate, *, text=None, value=None, formula=None, remove_cache=False):
    """Patch test OOXML without destroying unrelated formula caches."""
    output = BytesIO()
    with ZipFile(BytesIO(data)) as source, ZipFile(output, 'w', ZIP_DEFLATED) as dest:
        for info in source.infolist():
            content = source.read(info.filename)
            if info.filename == f'xl/worksheets/sheet{sheet}.xml':
                document = ET.fromstring(content)
                cell = document.find(f'.//{{{NS}}}c[@r="{coordinate}"]')
                if cell is None:
                    row_number = ''.join(c for c in coordinate if c.isdigit())
                    row = document.find(f'.//{{{NS}}}row[@r="{row_number}"]')
                    assert row is not None
                    cell = ET.SubElement(row, f'{{{NS}}}c', {'r': coordinate})
                if text is not None:
                    cell.clear(); cell.set('r', coordinate); cell.set('t', 'inlineStr')
                    ET.SubElement(ET.SubElement(cell, f'{{{NS}}}is'), f'{{{NS}}}t').text = text
                else:
                    if formula is not None:
                        f = cell.find(f'{{{NS}}}f')
                        if f is None:
                            f = ET.SubElement(cell, f'{{{NS}}}f')
                        f.text = formula
                    v = cell.find(f'{{{NS}}}v')
                    if remove_cache:
                        if v is not None:
                            cell.remove(v)
                    elif value is not None:
                        if v is None:
                            v = ET.SubElement(cell, f'{{{NS}}}v')
                        v.text = str(value)
                content = ET.tostring(document, encoding='utf-8')
            dest.writestr(info, content)
    return output.getvalue()


class WorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = make_workbook()
        cls.result = parse_workbook(cls.data, 'demo.xlsx')
        cls.rows = {r['key']: r for r in cls.result['rows']}

    def test_source_totals_and_annual_split(self):
        summary = self.result['totals']['Remediations']
        self.assertEqual((summary['rows'], summary['globalBudget'], summary['localTotal']), (5, 6400, 3190))
        self.assertEqual(summary['byYear']['2027'], {'rows': 1, 'globalBudget': 1000, 'localTotal': 1380})
        self.assertEqual(summary['byYear']['2028'], {'rows': 2, 'globalBudget': 5000, 'localTotal': 1810})
        self.assertEqual(summary['byYear']['2029'], {'rows': 2, 'globalBudget': 400, 'localTotal': 0})
        self.assertTrue(summary['reference']['matches'])

    def test_hidden_and_idless_rows_survive(self):
        self.assertIn('Remediations:5', self.rows)
        self.assertIsNone(self.rows['Remediations:7']['id'])
        self.assertEqual(self.rows['Remediations:7']['globalBudget'], 400)

    def test_duplicate_id_kept_as_distinct_interventions(self):
        a = self.rows['Remediations:5']; b = self.rows['Remediations:6']
        self.assertEqual(a['id'], b['id'])
        self.assertNotEqual(a['key'], b['key'])
        self.assertEqual(a['globalBudget'] + b['globalBudget'], 5000)
        self.assertTrue(any(i['code'] == 'duplicate-id' for i in self.result['issues']))

    def test_country_conflict_has_no_invented_allocations(self):
        record = self.rows['Remediations:6']
        self.assertEqual(record['allocationStatus'], 'ambiguous')
        self.assertEqual(record['allocations'], [])
        self.assertEqual(self.result['totals']['Remediations']['ambiguousLocal'], 810)
        self.assertEqual(self.result['totals']['Remediations']['mappedLocal'], 2380)

    def test_standard_mapping_does_not_distribute_global_budget(self):
        record = self.rows['Remediations:4']
        amounts = {a['entityId']: a['amount'] for a in record['allocations']}
        self.assertEqual(len(amounts), 21)
        self.assertEqual(amounts['Demo Entity 01'], 100)
        self.assertEqual(amounts['Demo Entity 21'], 10)
        self.assertEqual(sum(v or 0 for v in amounts.values()), record['localTotal'])
        self.assertEqual(record['globalBudget'], 1000)

    def test_special_group_and_zero_budget_memberships(self):
        record = self.rows['Remediations:5']
        allocations = record['allocations']
        self.assertEqual(len(allocations), 13)
        self.assertEqual(sum(a['amount'] > 0 for a in allocations), 5)
        self.assertEqual(sum(a['amount'] == 0 for a in allocations), 8)
        self.assertEqual(sum(a['amount'] or 0 for a in allocations), 1000)

    def test_zero_local_rows_remain_attributable(self):
        record = self.rows['Remediations:7']
        self.assertEqual(record['localTotal'], 0)
        self.assertEqual(record['allocationStatus'], 'mapped')
        self.assertEqual(len(record['allocations']), 21)
        self.assertTrue(all(a['amount'] == 0 for a in record['allocations']))

    def test_missing_unit_estimates_are_null_per_entity(self):
        record = self.rows['Remediations:8']
        amounts = {a['entityId']: a['amount'] for a in record['allocations']}
        self.assertIsNone(record['globalBudget'])
        self.assertIsNone(record['localComplete'])
        self.assertEqual(record['localTotal'], 0)
        self.assertIsNone(amounts['Demo Entity 01'])
        self.assertEqual(amounts['Demo Entity 21'], 0)
        self.assertEqual(sum(amount is None for amount in amounts.values()), 13)
        self.assertIn('non è specificata', record['allocationNote'])

    def test_ot_scope_separate(self):
        summary = self.result['totals']['OT']
        self.assertEqual((summary['rows'], summary['globalBudget'], summary['localTotal']), (2, 1200, 300))
        record = self.rows['OT:2']
        self.assertEqual(record['owner'], '')
        self.assertEqual(len(record['allocations']), 6)

    def test_missing_and_no_and_source_placeholders_stay_distinct(self):
        self.assertEqual(self.rows['Remediations:5']['priority'], 'no')
        self.assertEqual(self.rows['Remediations:6']['priority'], '')
        self.assertEqual(self.rows['Remediations:8']['globalDescription'], 'METTERE DESCRIZIONE')
        self.assertEqual(self.rows['Remediations:8']['localDescription'], '')
        self.assertEqual(self.result['totals']['Remediations']['missingGlobalEstimates'], 1)

    def test_headers_checked(self):
        changed = edited_cell(self.data, 2, 'I3', text='Budget')
        with self.assertRaisesRegex(ValueError, 'Budget Global'):
            parse_workbook(changed, 'invalid.xlsx')

    def test_entity_group_count_checked(self):
        changed = edited_cell(self.data, 1, 'C2', text='')
        with self.assertRaisesRegex(ValueError, 'gruppo 6 contiene 5'):
            parse_workbook(changed, 'invalid.xlsx')

    def test_unknown_formula_never_executed(self):
        changed = edited_cell(self.data, 2, 'L4', formula='HYPERLINK("https://example.invalid",1380)')
        result = parse_workbook(changed, 'unknown.xlsx')
        record = next(r for r in result['rows'] if r['key'] == 'Remediations:4')
        self.assertEqual(record['localTotal'], 1380)
        self.assertEqual(record['allocationStatus'], 'unavailable')
        self.assertEqual(record['allocations'], [])

    def test_wrong_row_reference_never_attributed(self):
        changed = edited_cell(self.data, 2, 'L4', formula='J5*13+K4*8')
        result = parse_workbook(changed, 'wrong-reference.xlsx')
        self.assertEqual(result['rows'][0]['allocationStatus'], 'unavailable')

    def test_missing_numeric_formula_cache_rejected(self):
        changed = edited_cell(self.data, 2, 'L4', remove_cache=True)
        with self.assertRaisesRegex(ValueError, 'formula senza risultato salvato'):
            parse_workbook(changed, 'no-cache.xlsx')

    def test_stale_local_formula_cache_rejected(self):
        changed = edited_cell(self.data, 2, 'L4', value=999)
        with self.assertRaisesRegex(ValueError, 'non coincide con la formula'):
            parse_workbook(changed, 'stale-cache.xlsx')

    def test_stale_reference_total_rejected(self):
        changed = edited_cell(self.data, 2, 'I9', value=1)
        with self.assertRaisesRegex(ValueError, 'totali salvati'):
            parse_workbook(changed, 'stale-total.xlsx')

    def test_invalid_file_rejected(self):
        for data in [b'', b'not-an-excel-file']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_workbook(data, 'invalid.xlsx')


class MultipleProjectSchemaTests(unittest.TestCase):
    def setUp(self):
        self.data = make_workbook(compact=True)

    def test_dynamic_groups_and_overlaps(self):
        result = parse_workbook(self.data, 'compact.xlsx')
        self.assertEqual(len(result['entities']), 3)
        self.assertEqual(result['entities'][0]['groups'], [1, 2, 3])
        amounts = {a['entityId']: a['amount'] for a in result['rows'][0]['allocations']}
        self.assertEqual(amounts, {'Demo Entity 01': 110, 'Demo Entity 02': 100, 'Demo Entity 03': 100})
        self.assertEqual(sum(amounts.values()), result['rows'][0]['localTotal'])
        # Group1 overlaps group3; an unknown J estimate must stay null even when K=0.
        missing = next(r for r in result['rows'] if r['key'] == 'Remediations:8')
        self.assertTrue(all(a['amount'] is None for a in missing['allocations']))

    def test_descriptive_group_headers_ending_in_integer(self):
        changed = edited_cell(self.data, 1, 'C1', text='Business oriented 1')
        changed = edited_cell(changed, 1, 'D1', text='Backup2')
        changed = edited_cell(changed, 1, 'E1', text='Complete 3')
        result = parse_workbook(changed, 'label-groups.xlsx')
        self.assertEqual(result['rows'][0]['allocationStatus'], 'mapped')
        self.assertEqual(result['rows'][0]['localTotal'], 310)

    def test_optional_ot(self):
        result = parse_workbook(make_workbook(compact=True, include_ot=False), 'main-only.xlsx')
        self.assertEqual(result['sheets'], ['LE_List', 'Remediations'])
        self.assertTrue(all(r['sheet'] == 'Remediations' for r in result['rows']))
        self.assertEqual(result['totals']['OT']['rows'], 0)

    def test_different_project_entities_and_data_do_not_leak(self):
        a = parse_workbook(make_workbook(seed=10, name_prefix='Alpha', compact=True), 'alpha.xlsx')
        b = parse_workbook(make_workbook(seed=20, name_prefix='Beta', compact=True), 'beta.xlsx')
        self.assertNotEqual(a['source']['sha256'], b['source']['sha256'])
        self.assertEqual(a['totals']['Remediations']['globalBudget'], 6410)
        self.assertEqual(b['totals']['Remediations']['globalBudget'], 6420)
        self.assertFalse({e['id'] for e in a['entities']} & {e['id'] for e in b['entities']})
        self.assertTrue(all('Beta' in r['name'] for r in b['rows']))

    def _duplicate_group(self, conflicting=False):
        changed = edited_cell(self.data, 1, 'F1', text='Alternate 2')
        for row in range(2, 5):
            member = row in ([2, 4] if conflicting else [2, 3])
            changed = edited_cell(changed, 1, f'F{row}', text='x' if member else '')
        return changed

    def test_duplicate_cardinality_identical_membership_allowed(self):
        result = parse_workbook(self._duplicate_group(), 'duplicate-same.xlsx')
        self.assertEqual(result['entities'][0]['groups'], [1, 2, 3])
        self.assertEqual(result['rows'][0]['localTotal'], 310)

    def test_duplicate_cardinality_different_membership_rejected(self):
        with self.assertRaisesRegex(ValueError, 'due gruppi con moltiplicatore 2'):
            parse_workbook(self._duplicate_group(conflicting=True), 'duplicate-conflict.xlsx')

    def test_formula_unknown_group_not_inferred_from_other_project(self):
        changed = edited_cell(self.data, 2, 'L4', formula='J4*13+K4*8')
        result = parse_workbook(changed, 'unknown-group.xlsx')
        record = result['rows'][0]
        self.assertEqual(record['allocationStatus'], 'unavailable')
        self.assertEqual(record['allocations'], [])

    def test_nonpositive_and_fractional_group_headers_rejected(self):
        for header in ['0', '-2', '2.5', 'Not a cardinality']:
            changed = edited_cell(self.data, 1, 'C1', text=header)
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, 'intestazione numerica positiva'):
                parse_workbook(changed, 'invalid-group.xlsx')


if __name__ == '__main__':
    unittest.main()
