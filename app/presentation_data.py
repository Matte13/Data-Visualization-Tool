"""Build an authoritative, deterministic snapshot for a filtered presentation.

The browser submits source row references, never amounts. Every displayed value
is read from the selected project's parsed workbook. Global amounts remain group
budgets; legal-entity breakdowns contain Local allocations only.
"""
from __future__ import annotations

from copy import deepcopy
import math

MAX_ROWS = 5000
MAX_COUNTRY_REFERENCES = 200000
FILTER_FIELDS = ('sheets', 'years', 'domains', 'owners', 'entities', 'nis2', 'priority')


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _local_amount(row, entities=None):
    if entities is None:
        return _number(row.get('localTotal'))
    if row.get('allocationStatus') != 'mapped':
        return None
    allocations = [item for item in row.get('allocations', []) if item.get('entityId') in entities]
    if any(_number(item.get('amount')) is None for item in allocations):
        return None
    return sum(item['amount'] for item in allocations)


def _belongs(row, entity_id):
    return row.get('allocationStatus') != 'mapped' or any(
        allocation.get('entityId') == entity_id for allocation in row.get('allocations', [])
    )


def _keys(value, rows_by_key, label, *, allow_empty=False):
    if not isinstance(value, list) or len(value) > MAX_ROWS or (not value and not allow_empty):
        raise ValueError(f'{label}: selezionare da 1 a {MAX_ROWS} righe valide.' if not allow_empty else f'{label}: elenco delle righe non valido.')
    seen = set()
    result = []
    for key in value:
        if not isinstance(key, str) or key not in rows_by_key:
            raise ValueError(f'{label}: una riga non appartiene al progetto selezionato.')
        if key in seen:
            raise ValueError(f'{label}: una riga è stata indicata più volte.')
        seen.add(key)
        result.append(key)
    return result


def _filters(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('I filtri della presentazione non sono validi.')
    result = {}
    for name in FILTER_FIELDS:
        if name not in value:
            continue
        selection = value[name]
        if selection is None:
            result[name] = None
        elif isinstance(selection, list) and len(selection) <= MAX_ROWS and all(isinstance(item, str) and len(item) <= 1000 for item in selection):
            result[name] = list(selection)
        elif name in ('nis2', 'priority') and selection in ('all', 'yes', 'no', 'missing'):
            result[name] = selection
        else:
            raise ValueError(f'Il filtro «{name}» non è valido.')
    for name in ('query', 'scope', 'localBudget', 'entityScope'):
        if name not in value:
            continue
        if not isinstance(value[name], str) or len(value[name]) > 2000:
            raise ValueError(f'Il filtro «{name}» non è valido.')
        result[name] = value[name]
    return result


def _prepare_rows(records, entities):
    result = deepcopy(records)
    for row in result:
        row['displayLocal'] = _local_amount(row, entities)
    return result


def _totals(records, entities=None, scope='all', *, country=False):
    globals_ = [_number(row.get('globalBudget')) for row in records]
    locals_ = [_local_amount(row, entities) for row in records]
    global_sum = sum(value for value in globals_ if value is not None)
    local_sum = sum(value for value in locals_ if value is not None)
    missing_global = sum(value is None for value in globals_)
    missing_local = sum(value is None for value in locals_)
    if country:
        selected = local_sum
        missing_selected = missing_local
        all_unknown = bool(records) and missing_local == len(records)
    else:
        selected = (global_sum if scope != 'local' else 0) + (local_sum if scope != 'global' else 0)
        missing_selected = sum(
            (scope != 'local' and global_value is None) or (scope != 'global' and local_value is None)
            for global_value, local_value in zip(globals_, locals_)
        )
        all_unknown = bool(records) and all(
            (scope == 'local' or global_value is None) and (scope == 'global' or local_value is None)
            for global_value, local_value in zip(globals_, locals_)
        )
    return {
        'global': None if country else global_sum,
        'local': local_sum,
        'selected': selected,
        'count': len(records),
        'missingGlobal': 0 if country else missing_global,
        'missingLocal': missing_local,
        'missingSelected': missing_selected,
        'selectedUnknown': all_unknown,
        'unresolvedLocal': sum(
            _number(row.get('localTotal')) or 0 for row in records
            if entities is not None and row.get('allocationStatus') != 'mapped'
        ),
    }


def _aggregate(records, field, entities=None, scope='all', *, country=False):
    groups = {}
    for row in records:
        value = row.get(field)
        label = 'Non specificato' if value in (None, '') else str(value)
        groups.setdefault(label, []).append(row)
    result = [
        {'label': label, 'rows': _prepare_rows(group, entities), **_totals(group, entities, scope, country=country)}
        for label, group in groups.items()
    ]
    if field == 'year':
        result.sort(key=lambda item: (item['label'] == 'Non specificato', item['label']))
    else:
        result.sort(key=lambda item: (-item['selected'], item['label'].casefold()))
    return result


def build_presentation_data(document: dict, request: dict) -> dict:
    """Validate row/entity references and return the original values for the deck.

    countryRows records the per-entity result already displayed by the client.
    It may contain source rows outside rowKeys when Local budget filtering has
    different meanings at group and entity level. Every reference is still checked
    against this project's workbook. The function never accepts client amounts.
    """
    if not isinstance(document, dict) or not isinstance(request, dict):
        raise ValueError('La richiesta di presentazione non è valida.')
    project = document.get('project')
    if not isinstance(project, dict) or not isinstance(project.get('id'), str) or request.get('projectId') != project['id']:
        raise ValueError('La presentazione deve riferirsi al progetto aperto.')
    source_rows = document.get('rows', [])
    rows_by_key = {row['key']: row for row in source_rows}
    if len(rows_by_key) != len(source_rows):
        raise ValueError('Il progetto contiene riferimenti alle righe non univoci.')
    row_keys = _keys(request.get('rowKeys'), rows_by_key, 'Presentazione')
    known_entities = {entity['id']: entity for entity in document.get('entities', [])}
    entities = request.get('entities')
    if entities is not None:
        if not isinstance(entities, list) or not entities or len(entities) > MAX_ROWS:
            raise ValueError('Selezionare almeno una country o legal entity.')
        if any(not isinstance(entity_id, str) or entity_id not in known_entities for entity_id in entities):
            raise ValueError('Una country o legal entity non appartiene al progetto selezionato.')
        if len(set(entities)) != len(entities):
            raise ValueError('Una country o legal entity è stata indicata più volte.')
        entities = list(entities)
    scope = request.get('scope', 'all')
    if scope not in ('all', 'global', 'local'):
        raise ValueError('Il livello di budget deve essere Global, Local o entrambi.')
    filters = _filters(request.get('filters'))
    selected_entity_ids = list(known_entities) if entities is None else entities
    country_selection = request.get('countryRows')
    if country_selection is not None and not isinstance(country_selection, dict):
        raise ValueError('La selezione delle righe per country non è valida.')
    if country_selection is not None and any(entity_id not in selected_entity_ids for entity_id in country_selection):
        raise ValueError('La presentazione include una country o legal entity non selezionata.')
    selected_rows = [rows_by_key[key] for key in row_keys]
    if entities is not None and any(not any(_belongs(row, entity_id) for entity_id in entities) for row in selected_rows):
        raise ValueError('Una riga non è associata alle entità selezionate.')
    countries = []
    references = 0
    represented_keys = set(row_keys)
    for entity_id in selected_entity_ids:
        if country_selection is not None:
            if entity_id not in country_selection:
                raise ValueError('Manca la selezione delle righe di una country o legal entity.')
            keys = _keys(country_selection[entity_id], rows_by_key, 'Country / legal entity', allow_empty=True)
            records = [rows_by_key[key] for key in keys]
            if any(not _belongs(row, entity_id) for row in records):
                raise ValueError('Una riga non è associata alla country o legal entity indicata.')
        else:
            records = [row for row in selected_rows if _belongs(row, entity_id)]
        references += len(records)
        if references > MAX_COUNTRY_REFERENCES:
            raise ValueError('La presentazione contiene troppe associazioni per country. Ridurre la selezione.')
        represented_keys.update(row['key'] for row in records)
        countries.append({
            'id': entity_id,
            'name': known_entities[entity_id].get('name', entity_id),
            'rows': _prepare_rows(records, [entity_id]),
            'totals': _totals(records, [entity_id], country=True),
            'byYear': _aggregate(records, 'year', [entity_id], country=True),
            'byDomain': _aggregate(records, 'domain', [entity_id], country=True),
            'groupGlobal': sum(_number(row.get('globalBudget')) or 0 for row in records),
        })
    notes = []
    for issue in document.get('issues', []):
        keys = issue.get('rowKeys') or []
        relevant = [key for key in keys if key in represented_keys]
        if not keys or relevant:
            notes.append({**deepcopy(issue), 'rowKeys': relevant})
    return {
        'project': deepcopy(project),
        'projectName': project.get('name') or document.get('source', {}).get('filename') or 'Progetto',
        'source': deepcopy(document.get('source', {})),
        'filters': filters,
        'scope': scope,
        'entities': entities,
        'rowKeys': row_keys,
        'rows': _prepare_rows(selected_rows, entities),
        'totals': _totals(selected_rows, entities, scope),
        'byYear': _aggregate(selected_rows, 'year', entities, scope),
        'byDomain': _aggregate(selected_rows, 'domain', entities, scope),
        'byOwner': _aggregate(selected_rows, 'owner', entities, scope),
        'countries': countries,
        'notes': notes,
    }
