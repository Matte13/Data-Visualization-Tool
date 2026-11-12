"""Import the consolidated template without summing its companion sheets."""
import math
import re

from .workbook import _allocate, _issue, _label, _number, _text

HEADERS = {
    'A': 'Remediation', 'B': 'Domain', 'C': 'Remediation name',
    'D': 'Budget Global', 'E': 'Budget Local - Complete',
    'F': 'Budget Local - Business Oriented', 'G': 'BUDGET LOCAL TOT',
    'H': 'Year', 'I': 'NIS2', 'J': 'Owner', 'K': 'Priority',
    'L': 'Type Of Remediation', 'M': 'Risk Type', 'N': 'Impact type',
    'O': 'Risk Level', 'P': 'CAPEX/OPEX', 'Q': 'Note',
}


def tags(value):
    """Line breaks separate declared attributes; no inferred risk/impact pairs."""
    return list(dict.fromkeys(part.strip() for part in _text(value).splitlines() if part.strip()))


def normalized(value):
    return ' '.join(_label(value).replace('&', ' and ').casefold().split())


def _details(values):
    result = []
    for name, start, main in (('CMA, WIFI, VA Remediations', 4, True), ('OT Remediations', 2, False)):
        if name not in values:
            continue
        sheet = values[name]
        shifted_main = main and _label(sheet['H2'].value).casefold() == 'budget global'
        if shifted_main:
            start = 3
        for row in range(start, sheet.max_row + 1):
            if not _label(sheet.cell(row, 4).value):
                continue
            result.append({
                'sheet': name, 'row': row, 'main': main,
                'name': normalized(sheet.cell(row, 4).value),
                'id': normalized(sheet.cell(row, 2).value),
                'year': sheet.cell(row, (12 if shifted_main else 13) if main else 8).value,
                'global': None if _label(sheet.cell(row, (8 if shifted_main else 9) if main else 5).value).casefold() == 'tbd' else sheet.cell(row, (8 if shifted_main else 9) if main else 5).value,
                'local': None if _label(sheet.cell(row, (11 if shifted_main else 12) if main else 7).value).casefold() == 'tbd' else sheet.cell(row, (11 if shifted_main else 12) if main else 7).value,
                'globalDescription': _text(sheet.cell(row, 5).value) if main else '',
                'localDescription': _text(sheet.cell(row, 6).value) if main else '',
                'applicableCountries': _text(sheet.cell(row, 7).value) if main else '',
                'existingCoverage': _text(sheet.cell(row, 8).value) if main and not shifted_main else '',
            })
    return result


def _budget_number(source, saved, coordinate):
    if source[coordinate].data_type != 'f' and _label(saved[coordinate].value).casefold() == 'tbd':
        return None
    return _number(source, saved, coordinate)


def _confirmed_nis2_allocation(record, entities):
    """Confirmed R.23 scope: seven Complete entities plus Sweden Business.

    This profile is restricted to the declared country list and 2027/2028
    formula 7+1; it never turns arbitrary multipliers into inferred geography.
    """
    if record.get('id') != 'R.23' or normalized(record.get('name')) != 'nis2 alignment' or record.get('year') not in (2027, 2028):
        return False
    formula = str(record.get('allocationFormula') or '').replace(' ', '')
    row = record['excelRow']
    if not re.fullmatch(rf'=J{row}\*7\+K{row}\*1', formula, re.IGNORECASE):
        return False
    declared = _text(record.get('applicableCountries'))
    declared = re.sub(r'^specific countries\s*:\s*', '', declared, flags=re.IGNORECASE)
    names = {normalized(name) for name in re.split(r'[,;\n]', declared) if name.strip()}
    expected = {'germany', 'spain lacer', 'spain itf', 'greece', 'france', 'benelux', 'portugal', 'sweden'}
    if names != expected:
        return False
    complete = ('Germania', 'Spagna - Lacer', 'Spagna - ITF', 'Grecia', 'Francia', 'Paesi Bassi & Belgio', 'Portogallo')
    by_id = {entity['id']: entity for entity in entities}
    if not all(name in by_id for name in (*complete, 'Svezia')):
        return False
    if by_id['Svezia'].get('localCategory') != 'business' or any(by_id[name].get('localCategory') not in ('complete', 'complete-ot') for name in complete):
        return False
    a, b = record.get('localComplete'), record.get('localBusiness')
    if a is None or b is None or record.get('localTotal') is None:
        return False
    if not math.isclose(a * 7 + b, record['localTotal'], rel_tol=0, abs_tol=.005):
        raise ValueError('NIS2 Alignment: il totale Local non coincide con la ripartizione confermata 7 Complete + Sweden Business.')
    record['allocations'] = [{'entityId': name, 'amount': a} for name in complete] + [{'entityId': 'Svezia', 'amount': b}]
    record['allocationStatus'] = 'mapped'
    record['allocationNote'] = 'Ripartizione NIS2 Alignment confermata: sette entità Complete e Svezia Business, identica nel 2027 e 2028. Formula e valori sorgente invariati.'
    return True


def parse_rows(formulas, values, entities, issues):
    source = formulas['All Remediations']; saved = values[source.title]
    rated_impacts = _label(source['N1'].value).casefold() == 'risk level'
    headers = dict(HEADERS)
    if rated_impacts:
        headers.update({'N': 'Risk Level', 'P': 'Reputational Impact', 'Q': 'Regulatory Impact',
                        'R': 'Economic Impact', 'S': 'Operational Impact', 'T': 'CAPEX/OPEX', 'U': 'Note'})
        headers.pop('O')  # Personal reasoning column: never read or expose its contents.
    for column, expected in headers.items():
        actual = _label(source[f'{column}1'].value).split('\n')[0].strip()
        accepted = {'priority', '2027 cma priority'} if column == 'K' else {expected.casefold()}
        if ' '.join(actual.casefold().split()) not in accepted:
            raise ValueError(f'All Remediations!{column}1: intestazione attesa «{expected}».')
    details = _details(values)
    result = []
    for row in range(2, source.max_row + 1):
        if not _label(saved[f'C{row}'].value):
            continue
        ident = _label(saved[f'A{row}'].value)
        year = _number(source, saved, f'H{row}')
        if year is not None and int(year) != year:
            raise ValueError(f'All Remediations!H{row}: anno non intero.')
        global_ = _budget_number(source, saved, f'D{row}')
        local = _budget_number(source, saved, f'G{row}')
        complete = _budget_number(source, saved, f'E{row}')
        business = _budget_number(source, saved, f'F{row}')
        candidates = [detail for detail in details if detail['year'] == year
                      and detail['global'] == global_ and detail['local'] == local]
        matches = [detail for detail in candidates
                   if detail['name'] == normalized(saved[f'C{row}'].value)]
        if not matches and ident:
            matches = [detail for detail in candidates if detail['id'] == normalized(ident)]
        ot = ident.casefold().startswith('r.ot.')
        if not ident and matches and all(not item['main'] for item in matches):
            ot = True
        formula = source[f'G{row}'].value if source[f'G{row}'].data_type == 'f' else None
        # Validate source arithmetic independently of country-group availability.
        pattern = r'=\$?E\$?(\d+)\*(\d+)' if ot else r'=\$?E\$?(\d+)\*(\d+)\+\$?F\$?(\d+)\*(\d+)'
        parsed = re.fullmatch(pattern, str(formula).replace(' ', ''), re.IGNORECASE)
        allocation_formula = None
        if parsed:
            numbers = list(map(int, parsed.groups()))
            expected = 0
            for offset, column in ((0, 'E'),) if ot else ((0, 'E'), (2, 'F')):
                referenced, factor = numbers[offset:offset+2]
                expected += (_number(source, saved, f'{column}{referenced}') or 0) * factor
            if local is not None and not math.isclose(expected, local, abs_tol=.005, rel_tol=0):
                raise ValueError(f'All Remediations!G{row}: il risultato salvato non coincide con la formula. Ricalcolare e salvare il file.')
            if numbers[0] != row or (not ot and numbers[2] != row):
                _issue(issues, 'cross-row-local-formula', 'Formula locale con riferimento a un’altra riga: valore Excel conservato, attribuzione country sospesa.', [f'All Remediations:{row}'])
            else:
                allocation_formula = (f'=F{row}*{numbers[1]}' if ot else
                                      f'=J{row}*{numbers[1]}+K{row}*{numbers[3]}')
        capex = _label(saved[f"{'T' if rated_impacts else 'P'}{row}"].value)
        risk_level = _label(saved[f"{'N' if rated_impacts else 'O'}{row}"].value)
        impact_levels = {}
        if rated_impacts:
            for column, kind in (('P', 'Reputational'), ('Q', 'Regulatory'), ('R', 'Economic'), ('S', 'Operational')):
                value = _label(saved[f'{column}{row}'].value)
                impact_levels[kind] = {'high': 'High', 'medium': 'Medium', 'low': 'Low'}.get(value.casefold(), value)
        record = {
            'key': f'All Remediations:{row}', 'sheet': 'OT' if ot else 'Remediations',
            'sourceSheet': source.title, 'excelRow': row, 'id': ident or None,
            'domain': _label(saved[f'B{row}'].value), 'name': _text(saved[f'C{row}'].value),
            'globalBudget': global_, 'localTotal': local, 'localComplete': complete,
            'localBusiness': business, 'localFormula': formula,
            'allocationFormula': allocation_formula, 'year': int(year) if year is not None else None,
            'nis2': _text(saved[f'I{row}'].value), 'nis2CompleteCount': None, 'nis2BusinessCount': None,
            'sourceOwner': _text(saved[f'J{row}'].value),
            'owner': 'Advisor' if _label(saved[f'J{row}'].value).casefold() in ('kpmg', 'advisor') else _label(saved[f'J{row}'].value),
            'priority': _text(saved[f'K{row}'].value), 'prioritySourceHeader': _text(source['K1'].value), 'category': _text(saved[f'L{row}'].value),
            'remediationType': _label(saved[f'L{row}'].value),
            'capexOpex': {'capex': 'Capex', 'opex': 'Opex'}.get(capex.casefold(), capex),
            'riskTypes': tags(saved[f'M{row}'].value), 'impactTypes': list(impact_levels) if rated_impacts else tags(saved[f'N{row}'].value),
            'riskLevel': {'high': 'High', 'medium': 'Medium', 'low': 'Low'}.get(risk_level.casefold(), risk_level),
            'capexOpexNote': _text(saved[f"{'U' if rated_impacts else 'Q'}{row}"].value),
            'metadataSchema': 'risk-impact-types',
            'detailSources': [{'sheet': item['sheet'], 'excelRow': item['row']} for item in matches],
        }
        if rated_impacts:
            record['impactLevels'] = impact_levels
        markers = {field: 'TBD' for column, field in (('D', 'globalBudget'), ('E', 'localComplete'), ('F', 'localBusiness'), ('G', 'localTotal'))
                   if source[f'{column}{row}'].data_type != 'f' and _label(saved[f'{column}{row}'].value).casefold() == 'tbd'}
        if markers:
            record['sourceBudgetMarkers'] = markers
            _issue(issues, 'unspecified-budget-marker', 'Stima indicata come TBD nel file: importo non disponibile, distinto da zero.', [record['key']])
        record['risk'] = '\n'.join(record['riskTypes'])
        record['impact'] = ''  # Legacy impact levels must never become Impact Types.
        for field in ('globalDescription', 'localDescription', 'applicableCountries', 'existingCoverage'):
            options = {detail[field] for detail in matches}
            record[field] = next(iter(options)) if len(options) == 1 else ''
        if not matches:
            _issue(issues, 'unmatched-detail', 'Descrizioni di dettaglio non abbinate in modo verificabile; dati e attributi provengono da All Remediations.', [record['key']], 'info')
        if not record['domain']:
            raise ValueError(f'All Remediations!B{row}: dominio obbligatorio.')
        if not _confirmed_nis2_allocation(record, entities):
            _allocate(record, entities, issues)
        result.append(record)
    if not result:
        raise ValueError('All Remediations non contiene remediation importabili.')
    return result
