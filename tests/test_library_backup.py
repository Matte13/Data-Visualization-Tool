"""Full-library rollback uses original workbook bytes and atomic persistence."""
import base64
from contextlib import contextmanager
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from openpyxl import load_workbook

from app.library_backup import (create_snapshot, read_snapshot, restore_snapshot,
                                validate_snapshot, write_snapshot, _digest,
                                _legacy_workbook_compatible)
from app.server import StorageError, WorkbookStore
from app.config import RuntimeConfig
from fixtures import make_workbook


class LibraryBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = WorkbookStore(self.root)
        self.first = make_workbook(name_prefix='First', compact=True, include_ot=False)
        self.updated = make_workbook(name_prefix='Updated', compact=True, include_ot=False)
        self.other = make_workbook(name_prefix='Other', compact=True, include_ot=False)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_restore_removes_later_projects_and_keeps_original_import(self):
        first = self.store.create(self.first, 'first.xlsx', 'First')['project']['id']
        second = self.store.create(self.other, 'other.xlsx', 'Other')['project']['id']
        self.store.replace(self.updated, 'updated.xlsx', first)
        self.store.activate(first)
        snapshot = create_snapshot(self.store)
        self.assertTrue(snapshot['legacyCompatibility']['compatible'])
        self.store.replace(self.other, 'later.xlsx', first)
        extra = self.store.create(self.updated, 'extra.xlsx', 'Extra')['project']['id']
        result = restore_snapshot(self.store, snapshot, require_legacy_compatible=True)
        self.assertEqual(result, {'projects': 2, 'removedProjects': 1, 'legacy112Compatible': True})
        restarted = WorkbookStore(self.root)
        self.assertEqual({p['id'] for p in restarted.catalog()['projects']}, {first, second})
        self.assertNotIn(extra, restarted.projects)
        self.assertEqual(restarted.active_project_id, first)
        self.assertEqual(restarted.source(first), (self.updated, 'updated.xlsx'))
        restarted.reset(first)
        self.assertEqual(restarted.source(first), (self.first, 'first.xlsx'))
        self.assertEqual(restarted.source(second), (self.other, 'other.xlsx'))

    def test_empty_snapshot_explicitly_restores_empty_library(self):
        snapshot = create_snapshot(self.store)
        self.store.create(self.first, 'first.xlsx')
        result = restore_snapshot(self.store, snapshot)
        self.assertEqual(result['removedProjects'], 1)
        self.assertEqual(WorkbookStore(self.root).catalog(), {'projects': [], 'activeProjectId': None})

    def test_private_file_roundtrip_never_overwrites(self):
        self.store.create(self.first, 'first.xlsx')
        snapshot = create_snapshot(self.store)
        path = self.root / 'snapshot.json'
        write_snapshot(snapshot, path)
        self.assertEqual(read_snapshot(path)['state'], snapshot['state'])
        if os.name != 'nt':
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            write_snapshot(snapshot, path)
        self.assertEqual(path.read_bytes(), before)

    def test_digest_failure_preserves_library_before_transaction(self):
        key = self.store.create(self.first, 'first.xlsx')['project']['id']
        snapshot = create_snapshot(self.store)
        snapshot['state']['projects'][0]['name'] = 'Changed after export'
        with patch.object(self.store, '_operation') as operation:
            with self.assertRaises(ValueError):
                restore_snapshot(self.store, snapshot)
        operation.assert_not_called()
        self.assertEqual(self.store.source(key), (self.first, 'first.xlsx'))

    def test_invalid_initial_workbook_is_validated_before_any_write(self):
        key = self.store.create(self.first, 'first.xlsx')['project']['id']
        snapshot = create_snapshot(self.store)
        snapshot['state']['projects'][0]['initialContent'] = base64.b64encode(b'not an Excel').decode()
        snapshot['stateSha256'] = _digest(snapshot['state'])
        with patch.object(self.store, '_persist_state') as persist:
            with self.assertRaises(ValueError):
                restore_snapshot(self.store, snapshot)
        persist.assert_not_called()
        self.assertEqual(self.store.source(key), (self.first, 'first.xlsx'))

    def test_failed_local_write_leaves_memory_and_catalog_unchanged(self):
        key = self.store.create(self.first, 'first.xlsx')['project']['id']
        snapshot = create_snapshot(self.store)
        self.store.replace(self.other, 'later.xlsx', key)
        with patch.object(self.store, '_persist_state', side_effect=StorageError('Synthetic failure')):
            with self.assertRaises(StorageError):
                restore_snapshot(self.store, snapshot)
        self.assertEqual(self.store.source(key), (self.other, 'later.xlsx'))
        self.assertEqual(WorkbookStore(self.root).source(key), (self.other, 'later.xlsx'))

    def test_restore_rebuilds_parsed_values_from_original_bytes(self):
        import hashlib
        key = self.store.create(self.first, 'first.xlsx')['project']['id']
        snapshot = create_snapshot(self.store)
        snapshot['state']['projects'][0]['document'] = {
            'source': {'sha256': 'forged'}, 'rows': [{'owner': 'forged'}]}
        snapshot['stateSha256'] = _digest(snapshot['state'])
        restore_snapshot(self.store, snapshot)
        restored = self.store.snapshot(key)
        self.assertEqual(restored['source']['sha256'], hashlib.sha256(self.first).hexdigest())
        self.assertEqual(restored['rows'][0]['owner'], 'Supplier A')

    def test_legacy_check_rejects_semantic_headers_and_headerless_note_columns(self):
        self.assertTrue(_legacy_workbook_compatible(self.first))
        for semantic in (True, False):
            workbook = load_workbook(BytesIO(self.first))
            if semantic:
                workbook['LE_List']['C1'] = 'OT'
            else:
                workbook['LE_List']['I4'] = 'Scratch notes do not form an entity group'
            target = BytesIO()
            workbook.save(target)
            workbook.close()
            self.assertFalse(_legacy_workbook_compatible(target.getvalue()))

    def test_compatibility_metadata_cannot_bypass_legacy_guard(self):
        self.store.create(self.first, 'first.xlsx')
        snapshot = create_snapshot(self.store)
        snapshot['legacyCompatibility'] = {'compatible': True}
        with patch('app.library_backup._legacy_workbook_compatible', return_value=False):
            with self.assertRaises(ValueError):
                validate_snapshot(snapshot, require_legacy_compatible=True)

    def test_azure_restore_clears_fk_then_deletes_extras_before_upsert(self):
        self.store.create(self.first, 'first.xlsx')
        snapshot = create_snapshot(self.store)
        extra = self.store.create(self.other, 'extra.xlsx')['project']['id']
        store = self.store
        store.persistence = 'azuresql'
        store._projects_table, store._state_table = '[dbo].[dvt_projects]', '[dbo].[dvt_library_state]'
        calls = []
        class Connection:
            def execute(self, sql, *args):
                calls.append((sql, args))
        store._sql_connection = Connection()
        @contextmanager
        def operation():
            calls.append(('BEGIN', ()))
            try:
                yield
            except Exception:
                calls.append(('ROLLBACK', ()))
                raise
            calls.append(('COMMIT', ()))
        def persist(projects, active):
            calls.append(('UPSERT', (set(projects), active)))
        with patch.object(store, '_operation', operation), patch.object(store, '_persist_state', persist):
            restore_snapshot(store, snapshot)
        self.assertEqual(calls[0][0], 'BEGIN')
        self.assertTrue(calls[1][0].startswith('UPDATE [dbo].[dvt_library_state] SET active_project_id=NULL'))
        self.assertTrue(calls[2][0].startswith('DELETE FROM [dbo].[dvt_projects]'))
        self.assertEqual(calls[2][1], (extra,))
        self.assertEqual(calls[3][0], 'UPSERT')
        self.assertEqual(calls[4][0], 'COMMIT')


@unittest.skipUnless(os.environ.get('RUN_AZURE_SQL_TESTS') == '1',
                     'Set RUN_AZURE_SQL_TESTS=1 for disposable SQL Server snapshot tests')
class AzureSqlLibraryBackupTests(unittest.TestCase):
    def setUp(self):
        import pyodbc
        from app.sqlserver_store import AzureSqlStore
        environment = {key: value for key, value in os.environ.items() if key.startswith('AZURE_SQL_')}
        environment['STORAGE_BACKEND'] = 'azuresql'
        self.config = RuntimeConfig.from_environ(environment)
        self.pyodbc, self.store_class = pyodbc, AzureSqlStore
        self.schema = 'dvt_backup_' + uuid.uuid4().hex
        connection = self.connection()
        try:
            connection.execute(f'CREATE SCHEMA [{self.schema}]')
        finally:
            connection.close()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.first = make_workbook(name_prefix='First snapshot', compact=True, include_ot=False)
        self.later = make_workbook(name_prefix='Later snapshot', compact=True, include_ot=False)

    def connection(self):
        return self.pyodbc.connect(self.config.azure_sql_connection_string, autocommit=True)

    def store(self):
        return self.store_class(self.config.azure_sql_connection_string, self.root, self.schema)

    def tearDown(self):
        connection = self.connection()
        try:
            connection.execute(f'DROP TABLE IF EXISTS [{self.schema}].[dvt_library_state]')
            connection.execute(f'DROP TABLE IF EXISTS [{self.schema}].[dvt_projects]')
            connection.execute(f'DROP SCHEMA [{self.schema}]')
        finally:
            connection.close()
            self.temp.cleanup()

    def test_exact_sql_restore_removes_new_projects_and_recovers_original_import(self):
        store = self.store()
        key = store.create(self.first, 'first.xlsx')['project']['id']
        store.replace(self.later, 'updated.xlsx', key)
        snapshot = create_snapshot(store)
        store.replace(self.first, 'later.xlsx', key)
        extra = store.create(self.later, 'extra.xlsx')['project']['id']
        restore_snapshot(store, snapshot, require_legacy_compatible=True)
        restarted = self.store()
        self.assertEqual({entry['id'] for entry in restarted.catalog()['projects']}, {key})
        self.assertNotIn(extra, restarted.projects)
        self.assertEqual(restarted.active_project_id, key)
        self.assertEqual(restarted.source(key), (self.later, 'updated.xlsx'))
        restarted.reset(key)
        self.assertEqual(restarted.source(key), (self.first, 'first.xlsx'))

    def test_sql_restore_failure_rolls_back_fk_delete_and_upserts(self):
        store = self.store()
        key = store.create(self.first, 'first.xlsx')['project']['id']
        snapshot = create_snapshot(store)
        store.replace(self.later, 'later.xlsx', key)
        extra = store.create(self.later, 'extra.xlsx')['project']['id']
        original = store._persist_state
        def failing_write(projects, active):
            original(projects, active)
            raise StorageError('Fictional rollback failure after SQL writes')
        with patch.object(store, '_persist_state', side_effect=failing_write):
            with self.assertRaises(StorageError):
                restore_snapshot(store, snapshot, require_legacy_compatible=True)
        restarted = self.store()
        self.assertEqual({entry['id'] for entry in restarted.catalog()['projects']}, {key, extra})
        self.assertEqual(restarted.active_project_id, extra)
        self.assertEqual(restarted.source(key), (self.later, 'later.xlsx'))


if __name__ == '__main__':
    unittest.main()
