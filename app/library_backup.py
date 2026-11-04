"""Private project-library snapshots for upgrades and rollback.

Run the explicit export/restore commands with the same runtime configuration as
the application. A snapshot includes the original Excel files and must be kept
outside Git. This module never creates a database or records credentials.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re

from openpyxl import load_workbook

from .config import RuntimeConfig
from .server import ROOT, StorageError, WorkbookStore, safe_filename, safe_project_name, timestamp
from .workbook import MAIN_HEADERS, OT_HEADERS, parse_workbook

FORMAT = 'data-visualization-tool-library'
MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024
MAX_PROJECTS = 5000


def _digest(state):
    try:
        data = json.dumps(state, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError):
        raise ValueError('Lo snapshot contiene dati non validi.') from None
    return hashlib.sha256(data).hexdigest()


def _legacy_cardinality(value):
    """The exact group-header syntax understood by the published 1.1.2 parser."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if math.isfinite(value) and value > 0 and int(value) == value else None
    match = re.search(r'(?:^|[^\d.+-])([1-9]\d*)$', str(value or '').strip())
    return int(match[1]) if match else None


def _legacy_workbook_compatible(content):
    """Check old import syntax after the current parser has validated the bytes.

    In particular, semantic headers and the headerless scratch-note columns of
    the meeting workbook cannot be read by version 1.1.2.
    """
    workbook = load_workbook(BytesIO(content), data_only=True, keep_links=False)
    try:
        if not {'LE_List', 'Remediations'}.issubset(workbook.sheetnames):
            return False
        sheet = workbook['LE_List']
        text = lambda value: str(value).strip() if value is not None else ''
        if text(sheet['A1'].value) != 'Country/Legal Entities' or text(sheet['B1'].value) != 'Backup':
            return False
        columns = []
        for col in range(3, sheet.max_column + 1):
            header = sheet.cell(1, col).value
            has_data = any(text(sheet.cell(row, col).value) for row in range(2, sheet.max_row + 1))
            if not text(header) and not has_data:
                continue
            cardinality = _legacy_cardinality(header)
            if cardinality is None:
                return False
            columns.append((col, cardinality))
        if not columns:
            return False
        memberships = {col: set() for col, _ in columns}
        names = set()
        for row in range(2, sheet.max_row + 1):
            name = text(sheet.cell(row, 1).value)
            if not name:
                if any(text(sheet.cell(row, col).value).lower() == 'x' for col, _ in columns):
                    return False
                continue
            if name in names:
                return False
            names.add(name)
            for col, _ in columns:
                marker = text(sheet.cell(row, col).value).lower()
                if marker not in ('', 'x'):
                    return False
                if marker == 'x':
                    memberships[col].add(name)
        by_number = {}
        for col, number in columns:
            if len(memberships[col]) != number:
                return False
            if number in by_number and by_number[number] != memberships[col]:
                return False
            by_number[number] = memberships[col]
        for name, header_row, expected in (('Remediations', 3, MAIN_HEADERS), ('OT', 1, OT_HEADERS)):
            if name == 'OT' and name not in workbook.sheetnames:
                continue
            if any(text(workbook[name][f'{column}{header_row}'].value) != title
                   for column, title in expected.items()):
                return False
        return True
    finally:
        workbook.close()


def _validated_state(state):
    if (not isinstance(state, dict) or type(state.get('version')) is not int
            or state['version'] != 1 or not isinstance(state.get('projects'), list)):
        raise ValueError('Lo snapshot non contiene una libreria valida.')
    if len(state['projects']) > MAX_PROJECTS:
        raise ValueError('Lo snapshot contiene troppi progetti.')
    for entry in state['projects']:
        if not isinstance(entry, dict):
            raise ValueError('Un progetto dello snapshot non è valido.')
        for name in ('name', 'filename', 'initialFilename', 'updatedAt'):
            if not isinstance(entry.get(name), str):
                raise ValueError('I metadati di un progetto dello snapshot non sono validi.')
        if (entry['filename'] != safe_filename(entry['filename'])
                or entry['initialFilename'] != safe_filename(entry['initialFilename'])
                or entry['name'] != safe_project_name(entry['name'], entry['filename'])):
            raise ValueError('I metadati di un progetto dello snapshot non sono validi.')
        try:
            updated = datetime.fromisoformat(entry['updatedAt'].replace('Z', '+00:00'))
            if len(entry['updatedAt']) > 40 or updated.tzinfo is None:
                raise ValueError('date')
        except ValueError:
            raise ValueError('La data di un progetto dello snapshot non è valida.') from None
    # Do not initialize a real store or trust any serialized parsed document.
    validator = object.__new__(WorkbookStore)
    validator.projects = {}
    validator.active_project_id = None
    try:
        validator._restore_state(state)
        validated = {hashlib.sha256(project['content']).hexdigest() for project in validator.projects.values()}
        for project in validator.projects.values():
            digest = hashlib.sha256(project['initialContent']).hexdigest()
            if digest not in validated:
                parse_workbook(project['initialContent'], project['initialFilename'])
                validated.add(digest)
    except (StorageError, ValueError, TypeError, KeyError, AttributeError):
        raise ValueError('Uno degli Excel attuali o originali dello snapshot non è valido. Nessun dato è stato sostituito.') from None
    return validator.projects, validator.active_project_id


def _compatibility(projects):
    results = {}
    incompatible = []
    for project in projects.values():
        for name, key in (('current', 'content'), ('initial', 'initialContent')):
            content = project[key]
            digest = hashlib.sha256(content).hexdigest()
            if digest not in results:
                results[digest] = _legacy_workbook_compatible(content)
            if not results[digest]:
                incompatible.append({'projectId': project['id'], 'workbook': name})
    return {'version': '1.1.2', 'compatible': not incompatible,
            'checkedWorkbooks': len(projects) * 2, 'incompatible': incompatible}


def create_snapshot(store):
    """Read a consistent full-library snapshot; no client workbook is changed."""
    with store._operation():
        state = WorkbookStore._encoded_state(store.projects, store.active_project_id)
    projects, _ = _validated_state(state)
    return {'format': FORMAT, 'version': 1, 'createdAt': timestamp(),
            'stateSha256': _digest(state), 'state': state,
            'legacyCompatibility': _compatibility(projects)}


def validate_snapshot(snapshot, *, require_legacy_compatible=False):
    if (not isinstance(snapshot, dict) or snapshot.get('format') != FORMAT
            or type(snapshot.get('version')) is not int or snapshot['version'] != 1):
        raise ValueError('Formato dello snapshot non riconosciuto.')
    state = snapshot.get('state')
    if not isinstance(snapshot.get('stateSha256'), str) or _digest(state) != snapshot['stateSha256']:
        raise ValueError('Il checksum dello snapshot non coincide. Nessun dato è stato sostituito.')
    projects, active = _validated_state(state)
    compatibility = _compatibility(projects)
    if require_legacy_compatible and not compatibility['compatible']:
        raise ValueError('Lo snapshot contiene Excel non leggibili dalla versione 1.1.2. Usare il backup creato prima di importare il nuovo tracciato.')
    return projects, active, compatibility


def write_snapshot(snapshot, path):
    """Create a private file, refusing overwrite or a pre-existing symlink."""
    validate_snapshot(snapshot)
    data = json.dumps(snapshot, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(data) > MAX_SNAPSHOT_BYTES:
        raise ValueError('Lo snapshot supera il limite di 256 MiB.')
    path = Path(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    complete = False
    try:
        with os.fdopen(descriptor, 'wb') as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        complete = True
    finally:
        if not complete:
            path.unlink(missing_ok=True)


def read_snapshot(path):
    path = Path(path)
    with path.open('rb') as source:
        data = source.read(MAX_SNAPSHOT_BYTES + 1)
    if len(data) > MAX_SNAPSHOT_BYTES:
        raise ValueError('Lo snapshot supera il limite di 256 MiB.')
    try:
        snapshot = json.loads(data.decode('utf-8'))
    except (ValueError, UnicodeError):
        raise ValueError('Il file dello snapshot non è un JSON valido.') from None
    validate_snapshot(snapshot)
    return snapshot


def restore_snapshot(store, snapshot, *, require_legacy_compatible=False):
    """Replace the exact library, including removal of post-backup projects.

    Validation is complete before the transaction starts. SQL uses the existing
    application lock, resets the active FK, deletes only absent project IDs and
    upserts the candidate state in that same transaction. Local mode replaces its
    one catalog atomically. Stop application processes/revisions during restore.
    """
    projects, active, compatibility = validate_snapshot(
        snapshot, require_legacy_compatible=require_legacy_compatible)
    with store._operation():
        previous = store.projects, store.active_project_id
        removed = set(store.projects) - set(projects)
        try:
            if store.persistence == 'azuresql':
                connection = store._sql_connection
                connection.execute(f'UPDATE {store._state_table} SET active_project_id=NULL WHERE singleton=1')
                for offset in range(0, len(removed), 1000):
                    ids = sorted(removed)[offset:offset + 1000]
                    connection.execute(f'DELETE FROM {store._projects_table} WHERE id IN ({",".join("?" for _ in ids)})', *ids)
            elif store.persistence == 'postgres':
                connection = store._pg_connection
                connection.execute('UPDATE remediation_library_state SET active_project_id=NULL WHERE singleton=true')
                for offset in range(0, len(removed), 1000):
                    ids = sorted(removed)[offset:offset + 1000]
                    connection.execute('DELETE FROM remediation_projects WHERE id IN (' + ','.join('%s::uuid' for _ in ids) + ')', ids)
            store._persist_state(projects, active)
            store.projects, store.active_project_id = projects, active
        except Exception:
            store.projects, store.active_project_id = previous
            raise
    return {'projects': len(projects), 'removedProjects': len(removed),
            'legacy112Compatible': compatibility['compatible']}


def _open_store(root):
    config = RuntimeConfig.from_environ()
    if config.azure_sql_connection_string:
        from .sqlserver_store import AzureSqlStore
        return AzureSqlStore(config.azure_sql_connection_string, root=root, schema=config.azure_sql_schema)
    return WorkbookStore(root, database_url=config.database_url, database_options=config.database_options)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export', help='Salva la libreria completa in un file privato nuovo.')
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--require-legacy-compatible', action='store_true')
    inspect = commands.add_parser('inspect', help='Verifica checksum, Excel e compatibilità senza aprire un database.')
    inspect.add_argument('--input', type=Path, required=True)
    restore = commands.add_parser('restore', help='Ripristina esattamente la libreria; arrestare prima l’applicazione.')
    restore.add_argument('--input', type=Path, required=True)
    restore.add_argument('--require-legacy-compatible', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'export':
            snapshot = create_snapshot(_open_store(ROOT))
            _, _, compatibility = validate_snapshot(snapshot, require_legacy_compatible=args.require_legacy_compatible)
            write_snapshot(snapshot, args.output)
            summary = {'projects': len(snapshot['state']['projects']), 'legacy112Compatible': compatibility['compatible']}
        else:
            snapshot = read_snapshot(args.input)
            if args.command == 'restore':
                # Check the requested rollback target before even opening SQL.
                validate_snapshot(snapshot, require_legacy_compatible=args.require_legacy_compatible)
                summary = restore_snapshot(_open_store(ROOT), snapshot, require_legacy_compatible=args.require_legacy_compatible)
            else:
                projects, _, compatibility = validate_snapshot(snapshot)
                summary = {'projects': len(projects), 'legacy112Compatible': compatibility['compatible'],
                           'incompatibleWorkbooks': len(compatibility['incompatible'])}
    except (OSError, ValueError, StorageError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
