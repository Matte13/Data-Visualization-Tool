"""Deterministic, offline importer for the agreed Remediation workbook schema.

Budget allocations describe the workbook's arithmetic groups, not verified
remediation applicability. Source rows and cached Excel values are never deduped
or amended. No general-purpose spreadsheet formula execution takes place.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import math
import re
from zipfile import ZipFile

from openpyxl import load_workbook

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_EXPANDED_BYTES = 80 * 1024 * 1024
MAIN_HEADERS = {
    'C': 'Domain', 'D': 'Remediation name', 'E': 'Global', 'F': 'Local',
    'G': 'Applicable Countries (to be verified)', 'H': 'Who has this?',
    'I': 'Budget Global', 'J': 'Budget Local - Complete',
    'K': 'Budget Local - Business Oriented', 'L': 'BUDGET LOCAL TOT',
    'M': 'Year', 'N': 'NIS2', 'O': 'Countries NIS2 - Complete',
    'P': 'Countries NIS2 - Business Oriented', 'Q': 'OWNER',
    'R': 'PRIORITY', 'S': 'DOMAIN2',
}
OT_HEADERS = {
    'C': 'Domain', 'D': 'Remediation name', 'E': 'Budget Global',
    'F': 'Budget Local', 'G': 'Local Complessivo', 'H': 'Anno', 'I': 'NIS 2',
}



def _text(value):
    return '' if value is None else str(value)


def _label(value):
    return _text(value).strip()


def _number(formula_sheet, values_sheet, coordinate):
    cell = formula_sheet[coordinate]
    value = values_sheet[coordinate].value
    if cell.data_type == 'f' and value is None:
        raise ValueError(
            f'{formula_sheet.title}!{coordinate}: formula senza risultato salvato. '
            'Aprire il file in Excel o LibreOffice, ricalcolare e salvare prima di importarlo.'
        )
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{formula_sheet.title}!{coordinate}: è richiesto un numero valido oppure una cella vuota.')
    return value


def _check_headers(sheet, row, expected):
    for col, title in expected.items():
        if _label(sheet[f'{col}{row}'].value) != title:
            raise ValueError(f'Struttura non compatibile: {sheet.title}!{col}{row} deve contenere «{title}».')


def _issue(issues, code, message, keys=(), severity='warning'):
    issues.append({'code': code, 'severity': severity, 'message': message, 'rowKeys': list(keys)})


def _group_number(value):
    """Read a positive cardinality, or a descriptive header ending in one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if math.isfinite(value) and value > 0 and int(value) == value else None
    text = _label(value)
    match = re.search(r'(?:^|[^\d.+-])([1-9]\d*)$', text)
    return int(match[1]) if match else None


def _semantic_group(value):
    """Recognize explicit category labels, never infer them from cardinality."""
    text = ' '.join(_label(value).casefold().split())
    match = re.fullmatch(r'(ot|local business|local complete)(?:\s+([1-9]\d*))?', text)
    if not match:
        return None
    return {'ot': 'ot', 'local business': 'business', 'local complete': 'complete'}[match[1]]


def _entities(sheet):
    if _label(sheet['A1'].value) != 'Country/Legal Entities' or _label(sheet['B1'].value) != 'Backup':
        raise ValueError('Il foglio LE_List non ha le intestazioni Country/Legal Entities e Backup attese.')
    columns = []
    categories = {}
    for col in range(3, sheet.max_column + 1):
        header = sheet.cell(1, col).value
        # Headerless notes may share rows with named entities. Only X markers
        # make such a column look like an incomplete membership definition.
        has_x = any(_label(sheet.cell(row, col).value).casefold() == 'x'
                    for row in range(2, sheet.max_row + 1))
        if not _label(header) and not has_x:
            continue
        semantic = _semantic_group(header)
        group = _group_number(header)
        if semantic:
            if semantic in categories:
                raise ValueError(f'LE_List: categoria «{_label(header)}» definita più volte.')
            members = {
                _label(sheet.cell(row, 1).value) for row in range(2, sheet.max_row + 1)
                if _label(sheet.cell(row, 1).value)
                and _label(sheet.cell(row, col).value).casefold() == 'x'
            }
            if group is not None and group != len(members):
                raise ValueError(f'LE_List: il gruppo {group} contiene {len(members)} legal entity invece di {group}; attribuzione budget non affidabile.')
            group = len(members)
            categories[semantic] = members
        elif group is None:
            raise ValueError(f'LE_List: il gruppo nella colonna {col} deve avere un’intestazione numerica positiva o terminare con il numero di legal entity.')
        columns.append((col, group))
    if not columns:
        raise ValueError('LE_List non contiene gruppi numerici per attribuire i budget locali.')
    if categories and set(categories) != {'ot', 'business', 'complete'}:
        raise ValueError('LE_List: la classificazione richiede le tre colonne OT, local business e local complete.')
    if categories:
        if categories['business'] & categories['complete']:
            raise ValueError('LE_List: le categorie local business e local complete devono essere disgiunte.')
        if not categories['ot'].issubset(categories['complete']):
            raise ValueError('LE_List: le legal entity OT devono appartenere anche a local complete.')
    result = []
    seen = set()
    memberships = {col: set() for col, _ in columns}
    for cells in sheet.iter_rows(min_row=2, max_col=sheet.max_column):
        name = _label(cells[0].value)
        if not name:
            if any(_label(cells[col - 1].value).lower() == 'x' for col, _ in columns):
                raise ValueError('LE_List contiene un gruppo assegnato a una legal entity senza nome.')
            continue
        if name in seen:
            raise ValueError(f'LE_List contiene la legal entity duplicata «{name}».')
        seen.add(name)
        groups = []
        for col, group in columns:
            marker = _label(cells[col - 1].value).lower()
            if marker not in ('', 'x'):
                raise ValueError(f'LE_List: usare x o una cella vuota per il gruppo {group} di «{name}».')
            if marker == 'x':
                memberships[col].add(name)
                if group > 0 and group not in groups:
                    groups.append(group)
        category = ('complete-ot' if name in categories.get('ot', ()) else
                    'complete' if name in categories.get('complete', ()) else
                    'business' if name in categories.get('business', ()) else None)
        result.append({'id': name, 'name': name, 'backup': _text(cells[1].value), 'groups': groups,
                       'localCategory': category,
                       'otEligible': name in categories['ot'] if categories else None})
    by_group = {}
    for col, group in columns:
        members = memberships[col]
        if len(members) != group:
            raise ValueError(f'LE_List: il gruppo {group} contiene {len(members)} legal entity invece di {group}; attribuzione budget non affidabile.')
        if group > 0 and group in by_group and by_group[group] != members:
            raise ValueError(f'LE_List: due gruppi con moltiplicatore {group} hanno legal entity diverse; la formula non permette di distinguere il gruppo corretto.')
        if group > 0:
            by_group[group] = members
    return result


def _apply_legacy_classification(sheet, entities):
    """Apply the confirmed original-template profile, without editing the XLSX.

    Numeric cardinalities alone have no category meaning. This compatibility
    profile is restricted to the original C:G layout and its validated,
    exhaustive membership partition. Other numeric layouts stay unclassified.
    """
    if [_label(sheet.cell(1, col).value) for col in range(3, 7)] != ['6', '8', '13', '5']:
        return None
    if ' '.join(_label(sheet['G1'].value).casefold().split()) not in ('9', 'europa ai act 9'):
        return None
    for col in range(8, sheet.max_column + 1):
        if _label(sheet.cell(1, col).value) or any(
                _label(sheet.cell(row, col).value).casefold() == 'x'
                for row in range(2, sheet.max_row + 1)):
            return None
    if len(entities) != 21:
        return None
    ot = {entity['id'] for entity in entities if 6 in entity['groups']}
    business = {entity['id'] for entity in entities if 8 in entity['groups']}
    complete = {entity['id'] for entity in entities if 13 in entity['groups']}
    if not ot.issubset(complete) or business & complete or business | complete != {
            entity['id'] for entity in entities}:
        return None
    for entity in entities:
        entity['localCategory'] = ('complete-ot' if entity['id'] in ot else
                                   'complete' if entity['id'] in complete else 'business')
        entity['otEligible'] = entity['id'] in ot
    return 'legacy-cde-6-8-13'


def _formula_groups(sheet_name, row, formula, known_groups):
    if not isinstance(formula, str):
        return None
    if sheet_name == 'Remediations':
        match = re.fullmatch(r'=\$?J\$?(\d+)\*(\d+)\+\$?K\$?(\d+)\*(\d+)', formula.replace(' ', ''), re.IGNORECASE)
        if not match or int(match[1]) != row or int(match[3]) != row:
            return None
        groups = (int(match[2]), int(match[4]))
        return groups if all(group == 0 or group in known_groups for group in groups) else None
    match = re.fullmatch(r'=\$?F\$?(\d+)\*(\d+)', formula.replace(' ', ''), re.IGNORECASE)
    if not match or int(match[1]) != row or (int(match[2]) != 0 and int(match[2]) not in known_groups):
        return None
    return (int(match[2]),)


def _allocate(record, entities, issues):
    key = record['key']
    known_groups = {group for entity in entities for group in entity['groups']}
    groups = _formula_groups(record['sheet'], record['excelRow'], record['localFormula'], known_groups)
    record.update(allocations=[], allocationStatus='unavailable', allocationNote='Formula non riconosciuta: budget locale non attribuito alle legal entity.')
    if record['localTotal'] is None:
        record['allocationNote'] = 'Budget locale complessivo non specificato nel file.'
        _issue(issues, 'missing-local-total', record['allocationNote'], [key])
        return
    if groups is None:
        _issue(issues, 'unsupported-local-formula', 'Formula locale non riconosciuta; importato il valore Excel senza attribuzione per legal entity.', [key])
        return
    unit_values = [record['localComplete'], record['localBusiness']] if len(groups) == 2 else [record['localComplete']]
    expected = sum((unit or 0) * group for unit, group in zip(unit_values, groups))
    if not math.isclose(expected, record['localTotal'], rel_tol=0, abs_tol=0.005):
        raise ValueError(f'{record["sheet"]}!{record["excelRow"]}: il budget locale salvato non coincide con la formula. Ricalcolare e salvare il file in Excel.')
    if record['sheet'] == 'OT' and any(entity['otEligible'] is not None for entity in entities):
        allocated = {entity['id'] for entity in entities if groups[0] in entity['groups']}
        eligible = {entity['id'] for entity in entities if entity['otEligible']}
        if not allocated.issubset(eligible):
            record['allocationStatus'] = 'ambiguous'
            record['allocationNote'] = 'Il gruppo della formula OT include legal entity non abilitate alla componente OT: totale di gruppo conservato, attribuzione per entità da confermare.'
            _issue(issues, 'ot-membership-conflict', record['allocationNote'], [key])
            return
    # Explicit country lists cannot be silently overridden by a numerical group.
    raw_countries = record['applicableCountries'].strip()
    if ';' in raw_countries:
        names = [part.strip() for part in raw_countries.split(';') if part.strip()]
        known_names = {e['id'] for e in entities}
        mapped = set(names)
        budget_entities = {
            e['id'] for e in entities
            if any(group in e['groups'] and (unit or 0) != 0 for unit, group in zip(unit_values, groups))
        }
        if not mapped.issubset(known_names) or mapped != budget_entities:
            record['allocationStatus'] = 'ambiguous'
            record['allocationNote'] = 'La lista di country della riga non coincide con i gruppi della formula: budget locale mantenuto nel totale di gruppo, attribuzione per legal entity da confermare.'
            _issue(issues, 'country-formula-conflict', record['allocationNote'], [key])
            return
    allocations = {}
    for unit, group in zip(unit_values, groups):
        for entity in entities:
            if group in entity['groups']:
                entity_id = entity['id']
                # Membership is retained even when the unit estimate is zero.
                # A blank estimate remains unknown, including overlapping groups.
                previous = allocations.get(entity_id, 0)
                allocations[entity_id] = None if unit is None or previous is None else previous + unit
    record['allocations'] = [{'entityId': entity_id, 'amount': amount} for entity_id, amount in allocations.items()]
    record['allocationStatus'] = 'mapped'
    record['allocationNote'] = 'Attribuzione del budget dalla formula Excel e dai gruppi LE_List; non certifica l’applicabilità della remediation.'
    if any(unit is None for unit in unit_values):
        record['allocationNote'] += ' Una stima unitaria non è specificata: gli importi delle legal entity corrispondenti restano non disponibili.'
    if raw_countries and raw_countries.casefold() not in ('all', 'solo global') and ';' not in raw_countries and record['sheet'] == 'Remediations':
        _issue(issues, 'provisional-coverage-note', 'La nota di copertura della riga è descrittiva; l’attribuzione economica segue la formula e non determina l’applicabilità effettiva.', [key], 'info')


def _main_rows(formulas, values, entities, issues):
    sheet = formulas['Remediations']; saved = values['Remediations']
    _check_headers(sheet, 3, MAIN_HEADERS)
    optional = {}
    aliases = {'capex/opex': 'capexOpex', 'rischi': 'risk', 'impatto': 'impact'}
    for cell in sheet[3]:
        field = aliases.get(''.join(_label(cell.value).casefold().split()))
        if field:
            if field in optional:
                raise ValueError(f'Remediations: intestazione duplicata {cell.value}.')
            optional[field] = cell.column
    rows = []
    for row in range(4, sheet.max_row + 1):
        if sheet[f'D{row}'].value is None:
            continue  # header/footer totals carry no remediation name
        record = {
            'key': f'Remediations:{row}', 'sheet': 'Remediations', 'excelRow': row,
            'id': saved[f'B{row}'].value,
            'domain': _label(saved[f'C{row}'].value), 'name': _text(saved[f'D{row}'].value),
            'globalDescription': _text(saved[f'E{row}'].value), 'localDescription': _text(saved[f'F{row}'].value),
            'applicableCountries': _text(saved[f'G{row}'].value), 'existingCoverage': _text(saved[f'H{row}'].value),
            'globalBudget': _number(sheet, saved, f'I{row}'),
            'localComplete': _number(sheet, saved, f'J{row}'), 'localBusiness': _number(sheet, saved, f'K{row}'),
            'localTotal': _number(sheet, saved, f'L{row}'),
            'localFormula': sheet[f'L{row}'].value if sheet[f'L{row}'].data_type == 'f' else None,
            'year': _number(sheet, saved, f'M{row}'), 'nis2': _text(saved[f'N{row}'].value),
            'nis2CompleteCount': _number(sheet, saved, f'O{row}'),
            'nis2BusinessCount': _number(sheet, saved, f'P{row}'),
            'owner': ('Advisor' if _label(saved[f'Q{row}'].value).casefold() == 'kpmg'
                      else _label(saved[f'Q{row}'].value)),
            'sourceOwner': _text(saved[f'Q{row}'].value), 'priority': _text(saved[f'R{row}'].value),
            'category': _text(saved[f'S{row}'].value),
        }
        for field in ('capexOpex', 'risk', 'impact'):
            if field in optional and sheet.cell(row, optional[field]).data_type == 'f' and saved.cell(row, optional[field]).value is None:
                raise ValueError(f'Remediations!{sheet.cell(row, optional[field]).coordinate}: formula senza risultato salvato; ricalcolare e salvare il file.')
            value = _label(saved.cell(row, optional[field]).value) if field in optional else ''
            normalized = value.casefold()
            if field == 'capexOpex':
                value = {'capex': 'Capex', 'opex': 'Opex'}.get(normalized, value)
            if field == 'impact':
                value = {'alto': 'Alto', 'medio': 'Medio', 'basso': 'Basso'}.get(normalized, value)
            record[field] = value
        if not record['domain'] or not record['name'].strip():
            raise ValueError(f'Remediations!{row}: dominio e nome remediation sono obbligatori.')
        if record['year'] is not None and record['year'] != int(record['year']):
            raise ValueError(f'Remediations!M{row}: anno non intero.')
        if record['year'] is not None:
            record['year'] = int(record['year'])
        _allocate(record, entities, issues)
        rows.append(record)
    if not rows:
        raise ValueError('Il foglio Remediations non contiene remediation importabili.')
    return rows


def _ot_rows(formulas, values, entities, issues):
    sheet = formulas['OT']; saved = values['OT']
    _check_headers(sheet, 1, OT_HEADERS)
    result = []
    for row in range(2, sheet.max_row + 1):
        if sheet[f'D{row}'].value is None:
            continue
        record = {
            'key': f'OT:{row}', 'sheet': 'OT', 'excelRow': row, 'id': saved[f'B{row}'].value,
            'domain': _label(saved[f'C{row}'].value), 'name': _text(saved[f'D{row}'].value),
            'globalDescription': '', 'localDescription': '', 'applicableCountries': '', 'existingCoverage': '',
            'globalBudget': _number(sheet, saved, f'E{row}'),
            'localComplete': _number(sheet, saved, f'F{row}'), 'localBusiness': None,
            'localTotal': _number(sheet, saved, f'G{row}'),
            'localFormula': sheet[f'G{row}'].value if sheet[f'G{row}'].data_type == 'f' else None,
            'year': _number(sheet, saved, f'H{row}'), 'nis2': _text(saved[f'I{row}'].value),
            'owner': '', 'sourceOwner': '', 'priority': '', 'category': '',
        }
        if not record['domain'] or not record['name'].strip():
            raise ValueError(f'OT!{row}: dominio e nome remediation sono obbligatori.')
        if record['year'] is not None and record['year'] != int(record['year']):
            raise ValueError(f'OT!H{row}: anno non intero.')
        if record['year'] is not None:
            record['year'] = int(record['year'])
        _allocate(record, entities, issues)
        result.append(record)
    return result


def _summaries(rows):
    result = {}
    for name in ('Remediations', 'OT'):
        selected = [row for row in rows if row['sheet'] == name]
        summary = {
            'rows': len(selected),
            'globalBudget': sum(row['globalBudget'] or 0 for row in selected),
            'localTotal': sum(row['localTotal'] or 0 for row in selected),
            'mappedLocal': sum(row['localTotal'] or 0 for row in selected if row['allocationStatus'] == 'mapped'),
            'ambiguousLocal': sum(row['localTotal'] or 0 for row in selected if row['allocationStatus'] == 'ambiguous'),
            'unavailableLocal': sum(row['localTotal'] or 0 for row in selected if row['allocationStatus'] == 'unavailable'),
            'missingGlobalEstimates': sum(row['globalBudget'] is None for row in selected),
            'byYear': {},
        }
        for year in sorted({row['year'] for row in selected if row['year'] is not None}):
            yearly = [row for row in selected if row['year'] == year]
            summary['byYear'][str(year)] = {
                'rows': len(yearly), 'globalBudget': sum(row['globalBudget'] or 0 for row in yearly),
                'localTotal': sum(row['localTotal'] or 0 for row in yearly),
            }
        result[name] = summary
    return result


def parse_workbook(data: bytes, filename: str) -> dict:
    """Read this project's Excel schema, or fail with a useful Italian message."""
    if not isinstance(data, bytes) or not data:
        raise ValueError('Il file Excel è vuoto o non valido.')
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('Il file supera il limite di 10 MB.')
    try:
        with ZipFile(BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 2048 or sum(item.file_size for item in members) > MAX_EXPANDED_BYTES:
                raise ValueError('Il contenuto del file Excel supera i limiti previsti.')
            if any(item.filename.lower().endswith('vbaproject.bin') for item in members):
                raise ValueError('Sono accettati soltanto file .xlsx senza macro.')
        formulas = load_workbook(BytesIO(data), data_only=False, keep_links=False)
        values = load_workbook(BytesIO(data), data_only=True, keep_links=False)
    except ValueError:
        raise
    except Exception as error:
        raise ValueError('Impossibile leggere il file. Selezionare un file .xlsx valido con il tracciato Remediations/LE_List previsto.') from error
    try:
        for required in ('LE_List', 'Remediations'):
            if required not in formulas.sheetnames:
                raise ValueError(f'Foglio obbligatorio «{required}» mancante.')
        if any(sheet.max_row > 5000 or sheet.max_column > 200 for sheet in formulas):
            raise ValueError('Dimensioni del workbook non compatibili con il modello dedicato.')
        entities = _entities(values['LE_List'])
        legacy_profile = _apply_legacy_classification(values['LE_List'], entities)
        issues = []
        rows = _main_rows(formulas, values, entities, issues)
        if 'OT' in formulas.sheetnames:
            rows += _ot_rows(formulas, values, entities, issues)
        _issue(issues, 'provisional-applicability', 'Le attribuzioni per legal entity rappresentano i gruppi di budget della formula. La colonna Applicable Countries è «to be verified» e non certifica l’applicabilità delle remediation.', severity='info')
        by_id = defaultdict(list)
        for record in rows:
            if record['id']:
                by_id[(record['sheet'], record['id'])].append(record['key'])
        for (_, display_id), keys in by_id.items():
            if len(keys) > 1:
                _issue(issues, 'duplicate-id', f'ID {display_id} presente in più righe nel file originale. Le righe sono mantenute come interventi distinti, con chiavi basate sulla riga Excel, e sono tutte incluse nei totali.', keys)
        missing_ids = [r['key'] for r in rows if r['id'] is None]
        if missing_ids:
            _issue(issues, 'missing-id', 'Alcune righe non hanno un ID nel file; sono mantenute con il riferimento alla riga Excel.', missing_ids, 'info')
        missing_budget = [r['key'] for r in rows if r['globalBudget'] is None]
        if missing_budget:
            _issue(issues, 'missing-global-estimate', 'Budget globale non specificato: il totale include solo gli importi presenti, senza stimare quelli mancanti.', missing_budget)
        placeholders = [r['key'] for r in rows if any('METTERE DESCRIZIONE' in r[k] for k in ('globalDescription', 'localDescription'))]
        if placeholders:
            _issue(issues, 'source-placeholder', 'Nel file sono presenti descrizioni provvisorie, riportate senza modificarle.', placeholders, 'info')
        missing_descriptions = [r['key'] for r in rows if r['sheet'] == 'Remediations' and (not r['globalDescription'] or not r['localDescription'])]
        if missing_descriptions:
            _issue(issues, 'missing-descriptions', 'Alcune descrizioni Global/Local non sono presenti nel file.', missing_descriptions, 'info')
        totals = _summaries(rows)
        # Match the source's own total row where present, without evaluating it.
        for r in range(4, formulas['Remediations'].max_row + 1):
            if formulas['Remediations'][f'D{r}'].value is None and formulas['Remediations'][f'I{r}'].data_type == 'f':
                global_reference = _number(formulas['Remediations'], values['Remediations'], f'I{r}')
                local_reference = _number(formulas['Remediations'], values['Remediations'], f'L{r}')
                if global_reference is not None and local_reference is not None:
                    matches = math.isclose(global_reference, totals['Remediations']['globalBudget'], abs_tol=0.005, rel_tol=0) and math.isclose(local_reference, totals['Remediations']['localTotal'], abs_tol=0.005, rel_tol=0)
                    totals['Remediations']['reference'] = {'excelRow': r, 'globalBudget': global_reference, 'localTotal': local_reference, 'matches': matches}
                    if not matches:
                        raise ValueError('I totali delle remediation non coincidono con i totali salvati nel file. Ricalcolare e salvare il workbook.')
                break
        classification_available = bool(legacy_profile) or any(
            _semantic_group(values['LE_List'].cell(1, col).value)
            for col in range(3, values['LE_List'].max_column + 1))
        return {
            'source': {'filename': filename, 'sha256': sha256(data).hexdigest()},
            'sheets': list(formulas.sheetnames), 'entities': entities,
            'classification': {
                'available': classification_available,
                'source': 'LE_List' if classification_available else None,
                'counts': {category: sum(entity['localCategory'] == category for entity in entities)
                           for category in ('complete-ot', 'complete', 'business')}
                          | {'unclassified': sum(entity['localCategory'] is None for entity in entities)},
                **({'profileId': legacy_profile} if legacy_profile else {}),
            },
            'rows': rows, 'issues': issues, 'totals': totals,
        }
    finally:
        formulas.close()
        values.close()
