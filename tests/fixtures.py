"""Generated, fictional Excel data for public tests. No customer workbook required."""
from io import BytesIO
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import Workbook
from app.workbook import MAIN_HEADERS, OT_HEADERS

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def make_semantic_workbook(seed: int = 0, name_prefix: str = 'Demo', *,
                           include_ot: bool = True, advisor_owner: bool = True,
                           notes: bool = True) -> bytes:
    """Fictional semantic LE headers, preserving all cached budget results.

    The category counts are OT6 within Complete13 and Business8, hence6/7/8
    disjoint classes. Financial values remain exactly make_workbook's values.
    Headerless notes deliberately coexist with entity rows and follow the list.
    """
    content = make_workbook(seed, name_prefix, include_ot=include_ot)
    output = BytesIO()
    with ZipFile(BytesIO(content)) as source, ZipFile(output, 'w', ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename in ('xl/worksheets/sheet1.xml', 'xl/worksheets/sheet2.xml'):
                tree = ET.fromstring(data)
                changes = ({'C1': ' OT ', 'D1': 'local business', 'E1': 'local complete'}
                           if item.filename.endswith('sheet1.xml') else
                           {'Q4': ' KpMg '} if advisor_owner else {})
                if notes and item.filename.endswith('sheet1.xml'):
                    changes.update({'I17': 'Global senza OT2027', 'K17': '1k',
                                    'I18': 'Global senza OT2028', 'K18': '5k',
                                    'C25': 'OT', 'D25': 'local business', 'E25': 'local complete',
                                    'C26': '20 nel2027', 'D26': '10 nel2027', 'E26': '100 nel2027',
                                    'C27': '30 nel2028', 'D27': '20 nel2028', 'E27': '250 nel2028'})
                    tree.find('s:dimension', NS).set('ref', 'A1:K27')
                sheet_data = tree.find('s:sheetData', NS)
                for coordinate, text in changes.items():
                    cell = tree.find(f'.//s:c[@r="{coordinate}"]', NS)
                    if cell is None:
                        number = ''.join(c for c in coordinate if c.isdigit())
                        row = sheet_data.find(f's:row[@r="{number}"]', NS)
                        if row is None:
                            row = ET.SubElement(sheet_data, '{' + NS['s'] + '}row', {'r': number})
                        cell = ET.SubElement(row, '{' + NS['s'] + '}c', {'r': coordinate})
                    cell.clear()
                    cell.set('r', coordinate)
                    cell.set('t', 'inlineStr')
                    ET.SubElement(ET.SubElement(cell, '{' + NS['s'] + '}is'),
                                  '{' + NS['s'] + '}t').text = text
                data = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
            target.writestr(item, data)
    return output.getvalue()


def with_cached_values(content: bytes, caches: dict[str, dict[str, float]]) -> bytes:
    """Write fixture-only Excel caches; never use this to alter user uploads."""
    target = BytesIO()
    with ZipFile(BytesIO(content)) as original, ZipFile(target, 'w', ZIP_DEFLATED) as output:
        for item in original.infolist():
            data = original.read(item.filename)
            if item.filename in caches:
                tree = ET.fromstring(data)
                values = caches[item.filename]
                for cell in tree.findall('.//s:c', NS):
                    coordinate = cell.get('r')
                    if coordinate not in values:
                        continue
                    value = cell.find('s:v', NS)
                    if value is None:
                        value = ET.SubElement(cell, '{' + NS['s'] + '}v')
                    value.text = str(values[coordinate])
                data = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
            output.writestr(item, data)
    return target.getvalue()


def make_workbook(seed: int = 0, name_prefix: str = 'Demo', *, compact: bool = False,
                  include_ot: bool = True) -> bytes:
    """Five remediation records and two optional OT records, with valid formula caches.

    compact=False: 21 entities; explicit budget groups6/8/13/5/9.
    compact=True: three entities; groups1/2/3 overlap intentionally.
    seed changes a known Global budget so project isolation is measurable.
    """
    workbook = Workbook()
    entities = workbook.active
    entities.title = 'LE_List'
    if compact:
        group_members = {1: {1}, 2: {1, 2}, 3: {1, 2, 3}}
        main_group, business_group, backup_group, ot_group = 3, 1, 2, 2
        entity_count = 3
    else:
        group_members = {6: set(range(1, 7)), 8: set(range(14, 22)),
                         13: set(range(1, 14)), 5: set(range(1, 6)), 9: set(range(1, 10))}
        main_group, business_group, backup_group, ot_group = 13, 8, 5, 6
        entity_count = 21
    names = [f'{name_prefix} Entity {index:02}' for index in range(1, entity_count + 1)]
    entities.append(['Country/Legal Entities', 'Backup', *group_members])
    for index, name in enumerate(names, start=1):
        entities.append([name, 'Provider' if index % 2 else 'Non centralizzato',
                         *['x' if index in members else None for members in group_members.values()]])
    main = workbook.create_sheet('Remediations')
    for column, title in MAIN_HEADERS.items():
        main[f'{column}3'] = title
    records = [
        # id,domain,name,global,complete,BO,year,owner,nis2,priority,formula primary group
        ('R.1', 'Governance', f'{name_prefix} governance', 1000 + seed, 100, 10, 2027, 'Supplier A', 'Yes', 'yes', main_group),
        ('R.2', 'Security', f'{name_prefix} backup', 2000, 200, 0, 2028, 'Supplier B', 'No', 'no', backup_group),
        ('R.2', 'Security', f'{name_prefix} alignment', 3000, 50, 20, 2028, 'Supplier A', 'Yes', None, main_group),
        (None, 'Governance', f'{name_prefix} audit', 400, 0, 0, 2029, 'Supplier B', None, 'no', main_group),
        ('R.4', 'Governance', f'{name_prefix} insurance', None, None, 0, 2029, 'Supplier A', None, None, main_group),
    ]
    caches = {}
    for row, record in enumerate(records, start=4):
        ident, domain, name, global_budget, complete, business, year, owner, nis2, priority, group = record
        main[f'A{row}'] = row - 3
        main[f'B{row}'] = ident
        main[f'C{row}'] = domain
        main[f'D{row}'] = name
        main[f'E{row}'] = 'METTERE DESCRIZIONE' if row == 8 else f'Original global text {row}'
        main[f'F{row}'] = None if row == 8 else f'Original local text {row}'
        main[f'G{row}'] = '; '.join(names[:2]) if row == 6 else 'All'
        main[f'I{row}'] = global_budget
        main[f'J{row}'] = complete
        main[f'K{row}'] = business
        main[f'L{row}'] = f'=J{row}*{group}+K{row}*{business_group}'
        main[f'M{row}'] = year
        main[f'N{row}'] = nis2
        main[f'O{row}'] = 1 if nis2 == 'Yes' else 0
        main[f'P{row}'] = 0
        main[f'Q{row}'] = owner
        main[f'R{row}'] = priority
        caches[f'L{row}'] = (complete or 0) * group + business * business_group
    main['I9'] = '=SUM(I4:I8)'
    main['L9'] = '=SUM(L4:L8)'
    caches['I9'] = sum(record[3] or 0 for record in records)
    caches['L9'] = sum(caches[f'L{row}'] for row in range(4, 9))
    main.row_dimensions[5].hidden = True
    main.column_dimensions['E'].hidden = True
    all_caches = {'xl/worksheets/sheet2.xml': caches}
    if include_ot:
        ot = workbook.create_sheet('OT')
        for column, title in OT_HEADERS.items():
            ot[f'{column}1'] = title
        ot_caches = {}
        for row, budget, unit, year in [(2, 500, 20, 2027), (3, 700, 30, 2028)]:
            ot[f'B{row}'] = f'R.OT.{row-1}'
            ot[f'C{row}'] = 'Security'
            ot[f'D{row}'] = f'{name_prefix} OT {row-1}'
            ot[f'E{row}'] = budget
            ot[f'F{row}'] = unit
            ot[f'G{row}'] = f'=F{row}*{ot_group}'
            ot[f'H{row}'] = year
            ot[f'I{row}'] = 'NIS 2' if row == 2 else None
            ot_caches[f'G{row}'] = unit * ot_group
        all_caches['xl/worksheets/sheet3.xml'] = ot_caches
    out = BytesIO()
    workbook.save(out)
    workbook.close()
    return with_cached_values(out.getvalue(), all_caches)
