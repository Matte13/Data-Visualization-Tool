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
        for row in range(start, sheet.max_row + 1):
            if not _label(sheet.cell(row, 4).value):
                continue
            result.append({
                'sheet': name, 'row': row, 'main': main,
                'name': normalized(sheet.cell(row, 4).value),
                'id': normalized(sheet.cell(row, 2).value),
                'year': sheet.cell(row, 13 if main else 8).value,
                'global': sheet.cell(row, 9 if main else 5).value,
                'local': sheet.cell(row, 12 if main else 7).value,
                'globalDescription': _text(sheet.cell(row, 5).value) if main else '',
                'localDescription': _text(sheet.cell(row, 6).value) if main else '',
                'applicableCountries': _text(sheet.cell(row, 7).value) if main else '',
                'existingCoverage': _text(sheet.cell(row, 8).value) if main else '',
            })
    return result


def parse_rows(formulas, values, entities, issues):
    source = formulas['All Remediations']; saved = values[source.title]
    for column, expected in HEADERS.items():
        actual = _label(source[f'{column}1'].value).split('\n')[0].strip()
        if actual.casefold() != expected.casefold():
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
        global_ = _number(source, saved, f'D{row}')
        local = _number(source, saved, f'G{row}')
        complete = _number(source, saved, f'E{row}')
        business = _number(source, saved, f'F{row}')
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
        capex = _label(saved[f'P{row}'].value)
        risk_level = _label(saved[f'O{row}'].value)
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
            'priority': _text(saved[f'K{row}'].value), 'category': _text(saved[f'L{row}'].value),
            'remediationType': _label(saved[f'L{row}'].value),
            'capexOpex': {'capex': 'Capex', 'opex': 'Opex'}.get(capex.casefold(), capex),
            'riskTypes': tags(saved[f'M{row}'].value), 'impactTypes': tags(saved[f'N{row}'].value),
            'riskLevel': {'high': 'High', 'medium': 'Medium', 'low': 'Low'}.get(risk_level.casefold(), risk_level),
            'capexOpexNote': _text(saved[f'Q{row}'].value),
            'metadataSchema': 'risk-impact-types',
            'detailSources': [{'sheet': item['sheet'], 'excelRow': item['row']} for item in matches],
        }
        record['risk'] = '\n'.join(record['riskTypes'])
        record['impact'] = ''  # Legacy impact levels must never become Impact Types.
        for field in ('globalDescription', 'localDescription', 'applicableCountries', 'existingCoverage'):
            options = {detail[field] for detail in matches}
            record[field] = next(iter(options)) if len(options) == 1 else ''
        if not matches:
            _issue(issues, 'unmatched-detail', 'Descrizioni di dettaglio non abbinate in modo verificabile; dati e attributi provengono da All Remediations.', [record['key']], 'info')
        if not record['domain']:
            raise ValueError(f'All Remediations!B{row}: dominio obbligatorio.')
        _allocate(record, entities, issues)
        result.append(record)
    if not result:
        raise ValueError('All Remediations non contiene remediation importabili.')
    return result
