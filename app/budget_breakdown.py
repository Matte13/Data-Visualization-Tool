"""Reconcile source Global/Local amounts with base, OT delta and entity classes.

The source row totals remain authoritative at group level. Entity classifications
describe recipients, not which unit-cost column happened to fund the allocation.
Uncertain geography is a visible residual, never an invented category allocation.
"""
from __future__ import annotations

import math


CATEGORIES = (
    ('complete-ot', 'Local Complete + OT'),
    ('complete', 'Local Complete senza OT'),
    ('business', 'Local Business'),
    ('unclassified', 'Entità non classificate'),
)


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _local_amount(row, selected):
    if selected is None:
        return _number(row.get('localTotal'))
    if row.get('allocationStatus') != 'mapped':
        return None
    allocations = [item for item in row.get('allocations', []) if item.get('entityId') in selected]
    if any(_number(item.get('amount')) is None for item in allocations):
        return None
    return sum(item['amount'] for item in allocations)


def budget_breakdown(rows, entities, selected_entities=None):
    """Return only sums of actual source rows/allocations, without mutation.

    ``None`` selects the full source group; an explicit selection sums only
    those entities' mapped Local amounts, while Global always remains group-wide.
    No entity-category classification is inferred from a multiplier alone.
    """
    selected = None if selected_entities is None else set(selected_entities)
    chosen_entities = [entity for entity in entities if selected is None or entity['id'] in selected]
    known = {key for key, _ in CATEGORIES if key != 'unclassified'}
    entity_categories = {
        entity['id']: entity.get('localCategory') if entity.get('localCategory') in known else 'unclassified'
        for entity in chosen_entities
    }
    categories = {
        key: {'id': key, 'label': label, 'entityCount': sum(value == key for value in entity_categories.values()),
              'base': 0, 'ot': 0, 'total': 0, 'missing': 0, 'known': 0,
              'baseMissing': 0, 'otMissing': 0, 'baseKnown': 0, 'otKnown': 0}
        for key, label in CATEGORIES
    }
    result = {
        'globalBase': 0, 'globalOt': 0, 'global': 0,
        'localBase': 0, 'localOt': 0, 'localTotal': 0,
        'unallocatedBase': 0, 'unallocatedOt': 0, 'unallocated': 0,
        'classificationAvailable': any(value != 'unclassified' for value in entity_categories.values()),
        'missingGlobal': 0, 'missingLocal': 0, 'unresolvedSource': 0,
        'rowCount': len(rows), 'baseCount': 0, 'otCount': 0,
        'missingGlobalBase': 0, 'missingGlobalOt': 0,
        'missingLocalBase': 0, 'missingLocalOt': 0,
    }
    for row in rows:
        is_ot = row.get('sheet') == 'OT'
        suffix = 'Ot' if is_ot else 'Base'
        component = 'ot' if is_ot else 'base'
        result['otCount' if is_ot else 'baseCount'] += 1
        global_value = _number(row.get('globalBudget'))
        local_value = _local_amount(row, selected)
        result['global' + suffix] += global_value or 0
        result['local' + suffix] += local_value or 0
        result['missingGlobal' + suffix] += global_value is None
        result['missingLocal' + suffix] += local_value is None
        if row.get('allocationStatus') != 'mapped':
            result['unresolvedSource'] += _number(row.get('localTotal')) or 0
            continue
        for allocation in row.get('allocations', []):
            category_id = entity_categories.get(allocation.get('entityId'))
            if category_id is None:
                continue
            value = _number(allocation.get('amount'))
            if value is None:
                categories[category_id]['missing'] += 1
                categories[category_id][component + 'Missing'] += 1
            else:
                categories[category_id][component] += value
                categories[category_id]['known'] += 1
                categories[category_id][component + 'Known'] += 1
    for category in categories.values():
        category['total'] = category['base'] + category['ot']
    result['global'] = result['globalBase'] + result['globalOt']
    result['localTotal'] = result['localBase'] + result['localOt']
    result['missingGlobal'] = result['missingGlobalBase'] + result['missingGlobalOt']
    result['missingLocal'] = result['missingLocalBase'] + result['missingLocalOt']
    # At group level the difference includes all unassigned source geography.
    # Explicit entity selections have no share of those uncertain group amounts.
    if selected is None:
        result['unallocatedBase'] = result['localBase'] - sum(category['base'] for category in categories.values())
        result['unallocatedOt'] = result['localOt'] - sum(category['ot'] for category in categories.values())
        for key in ('unallocatedBase', 'unallocatedOt'):
            if abs(result[key]) < 1e-9:
                result[key] = 0
    result['unallocated'] = result['unallocatedBase'] + result['unallocatedOt']
    result['missingAllocationCount'] = sum(category['missing'] for category in categories.values())
    result['categories'] = list(categories.values())
    return result
