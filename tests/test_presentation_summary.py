"""Short-deck aggregation must preserve source amounts and missing-value state."""
from collections import Counter
from copy import deepcopy
import unittest

from app.presentation_summary import (combine_groups, compact_groups,
                                      compact_years, detail_years,
                                      compact_countries)


def summary(label, rows, scope='all', *, country=False):
    """Independent fixture summary of original row values, including cached zero."""
    global_values = [row['globalBudget'] for row in rows]
    local_values = [row['displayLocal'] for row in rows]
    selected = [([local] if country or scope == 'local' else [global_] if scope == 'global'
                 else [global_, local]) for global_, local in zip(global_values, local_values)]
    return {
        'label': label,
        'global': None if country else sum(value for value in global_values if value is not None),
        'local': sum(value for value in local_values if value is not None),
        'selected': sum(value for pair in selected for value in pair if value is not None),
        'count': len(rows),
        'missingGlobal': 0 if country else global_values.count(None),
        'missingLocal': local_values.count(None),
        'missingSelected': sum(any(value is None for value in pair) for pair in selected),
        'selectedUnknown': bool(rows) and all(all(value is None for value in pair) for pair in selected),
        'unresolvedLocal': 0,
        'rows': deepcopy(rows),
    }


def source_row(key, global_, local):
    return {'key': key, 'id': 'R.2', 'globalBudget': global_, 'displayLocal': local,
            'name': 'Original text αβ\nPreserve every row'}


def members(groups):
    return [label for group in groups for label in group.get('members', [group['label']])]


class PresentationSummaryTests(unittest.TestCase):
    def test_compaction_preserves_exact_source_totals_for_each_budget_scope(self):
        for scope in ('all', 'global', 'local'):
            with self.subTest(scope=scope):
                records = [source_row(str(index), index * 1.125 if index % 5 else None,
                                      (40 - index) * .25 if index % 7 else None)
                           for index in range(30)]
                groups = [summary(f'Domain {index:02}', [row], scope)
                          for index, row in enumerate(records)]
                compact = compact_groups(groups, limit=8, scope=scope)
                self.assertEqual(len(compact), 8)
                self.assertEqual(compact[-1]['label'], 'Altri')
                for field in ('global', 'local', 'selected', 'count', 'missingGlobal',
                              'missingLocal', 'missingSelected'):
                    self.assertEqual(sum(group[field] for group in compact),
                                     sum(group[field] for group in groups), field)
                self.assertEqual(Counter(row['key'] for group in compact for row in group['rows']),
                                 Counter(row['key'] for row in records))
                self.assertEqual(Counter(members(compact)), Counter(group['label'] for group in groups))

    def test_scope_ranking_uses_the_selected_component_without_changing_either_amount(self):
        groups = [summary('Global investment', [source_row('a', 1000, 1)]),
                  summary('Local investment', [source_row('b', 1, 2000)]),
                  summary('Third', [source_row('c', 2, 2)])]
        for scope, label in [('global', 'Global investment'), ('local', 'Local investment')]:
            result = compact_groups(groups, limit=2, scope=scope)
            self.assertEqual(result[0]['label'], label)
            self.assertEqual(sum(group['global'] for group in result), 1003)
            self.assertEqual(sum(group['local'] for group in result), 2003)

    def test_missing_cached_zero_remains_unknown_and_known_zero_remains_known(self):
        unknown = summary('Unknown', [source_row('a', None, None), source_row('b', None, None)])
        zero = summary('Known zero', [source_row('c', 0, 0)])
        self.assertEqual((unknown['global'], unknown['local'], unknown['selected']), (0, 0, 0))
        combined_unknown = combine_groups([unknown], 'All unknown')
        self.assertTrue(combined_unknown['selectedUnknown'])
        self.assertEqual(combined_unknown['missingGlobal'], combined_unknown['count'])
        self.assertEqual(combined_unknown['missingLocal'], combined_unknown['count'])
        combined = combine_groups([unknown, zero], 'Known and unknown')
        self.assertFalse(combined['selectedUnknown'])
        self.assertEqual((combined['global'], combined['local'], combined['selected']), (0, 0, 0))
        self.assertEqual((combined['count'], combined['missingGlobal'], combined['missingLocal']), (3, 2, 2))
        self.assertEqual(compact_groups([unknown, zero])[0]['label'], 'Known zero')
        explicit_none = {**unknown, 'global': None, 'local': None, 'selected': None}
        none_result = combine_groups([explicit_none], 'No numeric cache')
        self.assertIsNone(none_result['global'])
        self.assertIsNone(none_result['local'])
        self.assertIsNone(none_result['selected'])
        self.assertTrue(none_result['selectedUnknown'])

    def test_partial_estimates_retain_available_amounts_and_missing_counts(self):
        partial = summary('Partial', [source_row('a', 100.25, None), source_row('b', None, 50.5)])
        unknown = summary('Unknown', [source_row('c', None, None)])
        combined = combine_groups([partial, unknown], 'Partial total')
        self.assertEqual((combined['global'], combined['local'], combined['selected']),
                         (100.25, 50.5, 150.75))
        self.assertEqual((combined['count'], combined['missingGlobal'], combined['missingLocal'],
                          combined['missingSelected']), (3, 2, 2, 3))
        self.assertFalse(combined['selectedUnknown'])

    def test_original_rows_including_duplicates_and_text_are_preserved(self):
        first = source_row('same-key', 10, 20)
        second = source_row('same-key', 30, None)
        third = source_row('third', None, 40)
        groups = [summary('A', [first]), summary('B', [second, third])]
        combined = combine_groups(groups, 'Combined')
        self.assertEqual(combined['rows'], [first, second, third])
        self.assertEqual([row['id'] for row in combined['rows']], ['R.2'] * 3)
        self.assertEqual(combined['count'], 3)
        self.assertEqual(combined['rows'][0]['name'], 'Original text αβ\nPreserve every row')

    def test_helpers_do_not_mutate_input_or_share_mutable_output_rows(self):
        groups = [summary(str(2027 + index), [source_row(str(index), index, index * 2)])
                  for index in range(12)]
        original = deepcopy(groups)
        for result in (combine_groups(groups, 'Combined'), *compact_groups(groups),
                       *compact_years(groups), *detail_years(groups)):
            result['rows'][0]['name'] = 'Changed only in the returned value'
        self.assertEqual(groups, original)
        countries = [self.country(index) for index in range(30)]
        original_countries = deepcopy(countries)
        compact = compact_countries(countries)
        compact[0]['rows'][0]['name'] = 'Changed'
        compact[-1]['byYear'][0]['rows'][0]['name'] = 'Changed'
        compact[-1]['members'].append('Additional id')
        self.assertEqual(countries, original_countries)

    def test_twenty_three_years_fit_eight_and_three_groups_without_loss(self):
        groups = [summary(str(2020 + index), [source_row(str(index), index * .125, index * .25)])
                  for index in range(23)]
        for limit, result in ((8, compact_years(reversed(groups))), (3, detail_years(reversed(groups)))):
            with self.subTest(limit=limit):
                self.assertEqual(len(result), limit)
                self.assertEqual(result[-1]['label'], 'Altri anni')
                self.assertEqual([group['label'] for group in result[:-1]],
                                 sorted(group['label'] for group in result[:-1]))
                self.assertEqual(Counter(members(result)), Counter(group['label'] for group in groups))
                for field in ('global', 'local', 'selected', 'count'):
                    self.assertEqual(sum(group[field] for group in result),
                                     sum(group[field] for group in groups))
                self.assertEqual(Counter(row['key'] for group in result for row in group['rows']),
                                 Counter(str(index) for index in range(23)))
        self.assertEqual([group['label'] for group in compact_years(groups[:3])], ['2020', '2021', '2022'])

    @staticmethod
    def country(index):
        rows = [source_row(f'{index}:a', None, index * .25),
                source_row(f'{index}:b', None, None if index % 4 == 0 else index * .5)]
        return {
            'id': f'Entity {index:03}', 'name': f'Entity {index:03}',
            'totals': summary('Totals', rows, country=True), 'rows': deepcopy(rows),
            'byYear': [summary('2027', rows[:1], country=True), summary('2028', rows[1:], country=True)],
            'byDomain': [summary('Security', rows, country=True)],
        }

    def test_one_hundred_countries_fit_twenty_two_rows_without_global_allocation(self):
        countries = [self.country(index) for index in range(100)]
        result = compact_countries(reversed(countries))
        self.assertEqual(len(result), 22)
        self.assertEqual(result[-1]['id'], '__other_countries__')
        self.assertEqual(result[-1]['name'], 'Altre entità (79)')
        represented_ids = [country['id'] for country in result[:-1]] + result[-1]['members']
        self.assertEqual(Counter(represented_ids), Counter(country['id'] for country in countries))
        self.assertEqual(sum(country['totals']['local'] for country in result),
                         sum(country['totals']['local'] for country in countries))
        self.assertEqual(sum(country['totals']['missingLocal'] for country in result),
                         sum(country['totals']['missingLocal'] for country in countries))
        self.assertTrue(all(country['totals']['global'] is None for country in result))
        remainder_ids = set(result[-1]['members'])
        remainder = [country for country in countries if country['id'] in remainder_ids]
        self.assertEqual(Counter(row['key'] for row in result[-1]['rows']),
                         Counter(row['key'] for country in remainder for row in country['rows']))
        for field in ('byYear', 'byDomain'):
            self.assertTrue(all(group['global'] is None for group in result[-1][field]))
            self.assertEqual(sum(group['local'] for group in result[-1][field]),
                             sum(country['totals']['local'] for country in remainder))

    def test_ties_are_stable_and_known_negative_amounts_precede_unknown(self):
        groups = [summary('Unknown', [source_row('u', None, None)]),
                  summary('Negative', [source_row('n', -20, -10)]),
                  summary('Zero', [source_row('z', 0, 0)]),
                  summary('beta', [source_row('b', 5, 5)]),
                  summary('Alpha', [source_row('a', 5, 5)])]
        expected = ['Alpha', 'beta', 'Zero', 'Negative', 'Unknown']
        for source in (groups, list(reversed(groups)), groups[2:] + groups[:2]):
            self.assertEqual([group['label'] for group in compact_groups(source)], expected)
        tied_countries = [self.country(index) for index in range(3)]
        for country in tied_countries:
            country['totals']['local'] = 0
        self.assertEqual([country['id'] for country in compact_countries(reversed(tied_countries))],
                         ['Entity 000', 'Entity 001', 'Entity 002'])

    def test_nested_remainders_keep_original_members_and_limits_include_remainder(self):
        groups = [summary(str(index), [source_row(str(index), index, index)]) for index in range(12)]
        first = compact_groups(groups, limit=8)
        second = compact_groups(first, limit=3)
        self.assertEqual(len(second), 3)
        self.assertEqual(Counter(members(second)), Counter(str(index) for index in range(12)))
        self.assertEqual(len(compact_years(groups, limit=1)), 1)
        self.assertEqual(len(compact_countries([self.country(index) for index in range(3)], limit=1)), 1)
        for function in (compact_groups, compact_years, detail_years, compact_countries):
            self.assertEqual(function([]), [])
            with self.assertRaises(ValueError):
                function([], limit=0)


if __name__ == '__main__':
    unittest.main()
