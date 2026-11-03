"""Presentation snapshots use fictional source data, never amounts supplied by the UI."""
from copy import deepcopy
import unittest

from app.presentation_data import build_presentation_data
from app.workbook import parse_workbook
from fixtures import make_workbook


class PresentationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = parse_workbook(make_workbook(), 'demo.xlsx')
        cls.document['project'] = {'id': 'project-alpha', 'name': 'Alpha'}

    def document_copy(self):
        return deepcopy(self.document)

    def request(self, **changes):
        payload = {'projectId': 'project-alpha', 'rowKeys': [row['key'] for row in self.document['rows']],
                   'entities': None, 'scope': 'all', 'filters': {}}
        payload.update(changes)
        return payload

    def report(self, **changes):
        return build_presentation_data(self.document, self.request(**changes))

    def test_full_source_totals_and_years_match_visualized_data(self):
        report = self.report()
        self.assertEqual((report['totals']['global'], report['totals']['local'], report['totals']['selected']), (7600, 3490, 11090))
        self.assertEqual(report['totals']['count'], 7)
        self.assertEqual([group['label'] for group in report['byYear']], ['2027', '2028', '2029'])
        self.assertEqual(sum(group['local'] for group in report['byYear']), 3490)
        self.assertEqual(report['projectName'], 'Alpha')
        self.assertEqual(report['source'], self.document['source'])

    def test_budget_scopes_change_selected_amount_not_source_components(self):
        global_report = self.report(scope='global')
        local_report = self.report(scope='local')
        self.assertEqual(global_report['totals']['selected'], 7600)
        self.assertEqual(local_report['totals']['selected'], 3490)
        self.assertEqual(global_report['totals']['local'], local_report['totals']['local'])
        self.assertEqual(len(global_report['rows']), 7)

    def test_subset_entity_local_amount_excludes_uncertain_allocations(self):
        report = self.report(entities=['Demo Entity 01'])
        self.assertEqual(report['totals']['global'], 7600)
        self.assertEqual(report['totals']['local'], 350)
        self.assertEqual(report['totals']['unresolvedLocal'], 810)
        self.assertEqual(report['totals']['missingLocal'], 2)
        row = next(row for row in report['rows'] if row['key'] == 'Remediations:6')
        self.assertIsNone(row['displayLocal'])
        self.assertEqual(row['localTotal'], 810)

    def test_country_budgets_never_allocate_global(self):
        report = self.report()
        country = report['countries'][0]
        self.assertIsNone(country['totals']['global'])
        self.assertEqual(country['totals']['local'], 350)
        self.assertEqual(country['groupGlobal'], 7600)
        self.assertTrue(all(group['global'] is None for group in country['byYear']))
        self.assertTrue(all(group['global'] is None for group in country['byDomain']))
        self.assertEqual(sum(country['totals']['local'] for country in report['countries']), 2680)

    def test_source_duplicate_ids_and_idless_rows_are_preserved(self):
        report = self.report()
        repeated = [row for row in report['rows'] if row['id'] == 'R.2']
        self.assertEqual(len(repeated), 2)
        self.assertNotEqual(repeated[0]['key'], repeated[1]['key'])
        self.assertEqual(len([row for row in report['rows'] if row['id'] is None]), 1)

    def test_all_filtered_rows_export_independent_of_visible_page_or_order(self):
        keys = ['Remediations:7', 'Remediations:5', 'Remediations:4']
        report = self.report(rowKeys=keys, filters={'query': 'test context', 'years': ['2027', '2028', '2029']})
        self.assertEqual(report['rowKeys'], keys)
        self.assertEqual([row['key'] for row in report['rows']], keys)
        self.assertEqual(report['totals']['count'], 3)
        self.assertEqual(report['filters']['query'], 'test context')

    def test_report_ignores_client_numeric_values(self):
        request = self.request(totals={'global': 999999999}, rows=[{'globalBudget': 999999999}])
        report = build_presentation_data(self.document, request)
        self.assertEqual(report['totals']['global'], 7600)
        self.assertEqual(report['rows'][0]['globalBudget'], 1000)

    def test_country_rows_capture_actual_per_entity_budget_filter(self):
        report = self.report(
            rowKeys=['Remediations:4', 'Remediations:5', 'Remediations:6', 'OT:2', 'OT:3'],
            entities=['Demo Entity 01'],
            filters={'localBudget': 'positive'},
            countryRows={'Demo Entity 01': ['Remediations:4', 'Remediations:5', 'OT:2', 'OT:3']},
        )
        country = report['countries'][0]
        self.assertEqual(country['totals']['local'], 350)
        self.assertEqual(country['totals']['missingLocal'], 0)
        self.assertEqual(country['totals']['count'], 4)
        self.assertEqual(country['totals']['global'], None)

    def test_country_rows_can_include_source_outside_top_keys(self):
        report = self.report(rowKeys=['Remediations:4'], entities=['Demo Entity 01'],
                             countryRows={'Demo Entity 01': ['Remediations:8']})
        self.assertEqual(report['totals']['count'], 1)
        self.assertEqual(report['countries'][0]['totals']['count'], 1)
        self.assertEqual(report['countries'][0]['rows'][0]['key'], 'Remediations:8')
        self.assertIsNone(report['countries'][0]['rows'][0]['displayLocal'])

    def test_missing_estimates_and_zero_are_distinct(self):
        report = self.report(rowKeys=['Remediations:7', 'Remediations:8'], entities=['Demo Entity 01'])
        audit, insurance = report['rows']
        self.assertEqual(audit['displayLocal'], 0)
        self.assertIsNone(insurance['displayLocal'])
        self.assertIsNone(insurance['globalBudget'])
        self.assertEqual(report['totals']['missingGlobal'], 1)
        self.assertEqual(report['totals']['missingLocal'], 1)
        self.assertEqual(report['totals']['local'], 0)
        unknown = self.report(rowKeys=['Remediations:8'], entities=['Demo Entity 01'])
        self.assertTrue(unknown['totals']['selectedUnknown'])

    def test_selected_values_preserve_fractional_euros(self):
        document = self.document_copy()
        document['rows'][0]['globalBudget'] = 1000.25
        document['rows'][0]['localTotal'] = 1380.75
        report = build_presentation_data(document, self.request(rowKeys=['Remediations:4']))
        self.assertEqual(report['totals']['global'], 1000.25)
        self.assertEqual(report['totals']['local'], 1380.75)
        self.assertEqual(report['totals']['selected'], 2381)

    def test_original_workbook_and_request_remain_unchanged(self):
        document = self.document_copy()
        request = self.request()
        original_document, original_request = deepcopy(document), deepcopy(request)
        report = build_presentation_data(document, request)
        report['rows'][0]['allocations'][0]['amount'] = 9876
        report['notes'][0]['message'] = 'Changed only in report'
        report['filters']['new'] = 'value'
        self.assertEqual(document, original_document)
        self.assertEqual(request, original_request)

    def test_nonmatching_project_rejected(self):
        with self.assertRaisesRegex(ValueError, 'progetto'):
            self.report(projectId='project-beta')

    def test_missing_or_empty_row_selection_rejected(self):
        for value in (None, [], 'Remediations:4'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.report(rowKeys=value)

    def test_unknown_or_duplicate_row_keys_rejected(self):
        for keys in (['Other:1'], ['Remediations:4', 'Remediations:4']):
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                self.report(rowKeys=keys)

    def test_unknown_duplicate_or_empty_entities_rejected(self):
        for entities in ([], ['Demo Entity 99'], ['Demo Entity 01', 'Demo Entity 01'], 'Demo Entity 01'):
            with self.subTest(entities=entities), self.assertRaises(ValueError):
                self.report(entities=entities)

    def test_unknown_scope_and_invalid_filter_shapes_rejected(self):
        for changes in ({'scope': 'invented'}, {'filters': []}, {'filters': {'years': 2027}}, {'filters': {'owners': [9]}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.report(**changes)

    def test_unknown_missing_or_duplicate_country_references_rejected(self):
        for country_rows in ({'Unknown': []}, {}, {'Demo Entity 01': ['Other:1']},
                             {'Demo Entity 01': ['Remediations:4', 'Remediations:4']}):
            with self.subTest(country_rows=country_rows), self.assertRaises(ValueError):
                self.report(entities=['Demo Entity 01'], countryRows=country_rows)

    def test_nonassociated_mapped_country_reference_rejected(self):
        # Backup uses group5 plus group8, so entity10 has no source budget attribution.
        with self.assertRaisesRegex(ValueError, 'associata'):
            self.report(entities=['Demo Entity 10'], rowKeys=['Remediations:4'],
                        countryRows={'Demo Entity 10': ['Remediations:5']})

    def test_empty_country_reference_is_valid_no_investment(self):
        report = self.report(entities=['Demo Entity 01'], countryRows={'Demo Entity 01': []})
        self.assertEqual(report['countries'][0]['totals']['count'], 0)
        self.assertEqual(report['countries'][0]['totals']['local'], 0)
        self.assertEqual(report['countries'][0]['rows'], [])

    def test_notes_do_not_leak_unrelated_row_details(self):
        report = self.report(rowKeys=['Remediations:4'], entities=['Demo Entity 01'],
                             countryRows={'Demo Entity 01': ['Remediations:4']})
        self.assertTrue(all(not issue['rowKeys'] or issue['rowKeys'] == ['Remediations:4'] for issue in report['notes']))
        self.assertFalse(any(issue['code'] == 'country-formula-conflict' for issue in report['notes']))


if __name__ == '__main__':
    unittest.main()
