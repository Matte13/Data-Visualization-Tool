"""Generated, fictional Excel data for public tests. No customer workbook required."""
from io import BytesIO
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import Workbook
from app.workbook import MAIN_HEADERS, OT_HEADERS

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


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
