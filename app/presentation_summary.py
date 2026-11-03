"""Deterministic, lossless numerical grouping for the short presentation.

These helpers only combine existing report values. They do not infer country
allocations, change estimates, deduplicate remediation rows or rank priorities.
The unabridged source data remain available in the presentation's notes.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _known(group, field):
    count = group.get('count', 0)
    if count and group.get('missing' + field.capitalize(), 0) == count:
        return None
    return _number(group.get(field))


def _selected(group, scope='all'):
    if group.get('selectedUnknown') is True:
        return None
    if scope in ('global', 'local'):
        return _known(group, scope)
    count = group.get('count', 0)
    if count and group.get('missingGlobal') == count and group.get('missingLocal') == count:
        return None
    if 'selected' in group:
        return _number(group['selected'])
    values = [_known(group, field) for field in ('global', 'local')]
    return sum(value for value in values if value is not None) if any(value is not None for value in values) else None


def _rank(group, scope='all'):
    value = _selected(group, scope)
    label = str(group.get('label', ''))
    return (value is None, -(value or 0), label.casefold(), label)


def _year_order(group):
    label = str(group.get('label', ''))
    return (label in ('', 'Non specificato', 'Anno non specificato'), label)


def combine_groups(groups, label):
    """Sum existing group summaries without treating unknown amounts as zero."""
    groups = list(groups)
    result = {'label': label}
    for field in ('global', 'local', 'selected'):
        values = [_number(group.get(field)) for group in groups]
        available = [value for value in values if value is not None]
        result[field] = sum(available) if available or not groups else None
    for field in ('count', 'missingGlobal', 'missingLocal', 'missingSelected', 'unresolvedLocal'):
        result[field] = sum(_number(group.get(field)) or 0 for group in groups)
    nonempty = [group for group in groups if group.get('count', 0)]
    result['selectedUnknown'] = bool(nonempty) and all(_selected(group) is None for group in nonempty)
    result['rows'] = deepcopy([row for group in groups for row in group.get('rows', [])])
    result['members'] = [str(member) for group in groups
                         for member in group.get('members', [group.get('label', '')])]
    return result


def compact_groups(groups, limit=8, scope='all', other_label='Altri'):
    """Show the largest existing amounts and one explicit remainder group."""
    if limit < 1:
        raise ValueError('Il numero di gruppi deve essere almeno uno.')
    ranked = sorted(groups, key=lambda group: _rank(group, scope))
    if len(ranked) <= limit:
        return deepcopy(ranked)
    return deepcopy(ranked[:limit - 1]) + [combine_groups(ranked[limit - 1:], other_label)]


def compact_years(groups, limit=8, scope='all'):
    """Keep chronological labels, grouping surplus years by exact amounts."""
    if limit < 1:
        raise ValueError('Il numero di anni deve essere almeno uno.')
    groups = list(groups)
    if len(groups) <= limit:
        return deepcopy(sorted(groups, key=_year_order))
    ranked = sorted(groups, key=lambda group: _rank(group, scope))
    shown = sorted(ranked[:limit - 1], key=_year_order)
    return deepcopy(shown) + [combine_groups(sorted(ranked[limit - 1:], key=_year_order), 'Altri anni')]


def detail_years(groups, limit=3, scope='all'):
    return compact_years(groups, limit=limit, scope=scope)


def _country_rank(country):
    value = _known(country.get('totals', {}), 'local')
    name = str(country.get('name', country.get('id', '')))
    return (value is None, -(value or 0), name.casefold(), str(country.get('id', '')))


def _combined_country_groups(countries, field):
    grouped = defaultdict(list)
    for country in countries:
        for group in country.get(field, []):
            grouped[str(group.get('label', ''))].append(group)
    result = [combine_groups(groups, label) for label, groups in grouped.items()]
    # Global budgets always remain at group level, including remainder entities.
    for group in result:
        group['global'] = None
    return sorted(result, key=_year_order if field == 'byYear' else lambda group: _rank(group, 'local'))


def compact_countries(countries, limit=22):
    """Bound country matrix rows; preserve all other entities in a named total."""
    if limit < 1:
        raise ValueError('Il numero di entità deve essere almeno uno.')
    ranked = sorted(countries, key=_country_rank)
    if len(ranked) <= limit:
        return deepcopy(ranked)
    remaining = ranked[limit - 1:]
    totals = combine_groups([country.get('totals', {}) for country in remaining], 'Altre entità')
    totals['global'] = None
    combined = {
        'id': '__other_countries__',
        'name': f'Altre entità ({len(remaining)})',
        'totals': totals,
        'rows': deepcopy([row for country in remaining for row in country.get('rows', [])]),
        'byYear': _combined_country_groups(remaining, 'byYear'),
        'byDomain': _combined_country_groups(remaining, 'byDomain'),
        'members': [str(country.get('id', '')) for country in remaining],
    }
    return deepcopy(ranked[:limit - 1]) + [combined]
