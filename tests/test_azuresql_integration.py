"""SQL Server compatibility checks for Azure SQL; use a disposable test database.

RUN_AZURE_SQL_TESTS=1 uses AZURE_SQL_* test settings and creates/drops only a
unique test schema. Never point these tests at the client's database.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen
import uuid

from app.config import RuntimeConfig
from app.server import ExplorerServer, StorageError
from app.sqlserver_store import AzureSqlStore
from fixtures import make_workbook


@unittest.skipUnless(os.environ.get('RUN_AZURE_SQL_TESTS') == '1',
                     'Set RUN_AZURE_SQL_TESTS=1 for a disposable SQL Server database')
class AzureSqlIntegrationTests(unittest.TestCase):
    def setUp(self):
        import pyodbc
        self.pyodbc = pyodbc
        environment = {key:value for key,value in os.environ.items() if key.startswith('AZURE_SQL_')}
        environment['STORAGE_BACKEND'] = 'azuresql'
        self.config = RuntimeConfig.from_environ(environment)
        self.schema = 'dvt_test_' + uuid.uuid4().hex
        connection = pyodbc.connect(self.config.azure_sql_connection_string,autocommit=True)
        try:
            connection.execute(f'CREATE SCHEMA [{self.schema}]')
        finally:
            connection.close()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.first = make_workbook(name_prefix='First',compact=True,include_ot=False)
        self.second = make_workbook(name_prefix='Second',compact=True,include_ot=False)

    def tearDown(self):
        connection = self.pyodbc.connect(self.config.azure_sql_connection_string,autocommit=True)
        try:
            connection.execute(f'DROP TABLE IF EXISTS [{self.schema}].[dvt_library_state]')
            connection.execute(f'DROP TABLE IF EXISTS [{self.schema}].[dvt_projects]')
            connection.execute(f'DROP SCHEMA [{self.schema}]')
        finally:
            connection.close()
            self.temp.cleanup()

    def store(self):
        return AzureSqlStore(self.config.azure_sql_connection_string,self.root,self.schema)

    def test_projects_update_reset_and_restart(self):
        store=self.store()
        first=store.create(self.first,'first.xlsx','Piano 🌍')['project']['id']
        other=store.create(self.second,'second.xlsx','Other')['project']['id']
        store.replace(self.second,'updated.xlsx',first)
        restarted=self.store()
        self.assertEqual(restarted.source(first),(self.second,'updated.xlsx'))
        restarted.reset(first)
        self.assertEqual(store.source(first),(self.first,'first.xlsx'))
        self.assertEqual(store.source(other),(self.second,'second.xlsx'))
        self.assertFalse((self.root/'runtime/projects.json').exists())

    def test_independent_stores_refresh_and_keep_other_changes(self):
        left,right=self.store(),self.store()
        first=left.create(self.first,'first.xlsx','First')['project']['id']
        second=right.create(self.second,'second.xlsx','Second')['project']['id']
        left.replace(self.second,'changed.xlsx',first)
        right.activate(second)
        self.assertEqual(right.source(first),(self.second,'changed.xlsx'))
        self.assertEqual(left.catalog()['activeProjectId'],second)
        self.assertEqual(len(left.catalog()['projects']),2)

    def test_concurrent_writers_keep_all_projects(self):
        stores=[self.store(),self.store()]
        def writer(index):
            return [stores[index].create(self.first,f'{index}-{n}.xlsx')['project']['id'] for n in range(3)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            keys={key for batch in pool.map(writer,range(2)) for key in batch}
        self.assertEqual({entry['id'] for entry in self.store().catalog()['projects']},keys)

    def test_failed_transaction_preserves_database_and_memory(self):
        store=self.store();key=store.create(self.first,'first.xlsx')['project']['id']
        original=store._persist_state
        def failing_write(projects,active):
            original(projects,active)
            raise StorageError('Fictional failure before commit')
        with patch.object(store,'_persist_state',side_effect=failing_write):
            with self.assertRaises(StorageError):store.replace(self.second,'changed.xlsx',key)
        self.assertEqual(store.source(key),(self.first,'first.xlsx'))
        self.assertEqual(self.store().source(key),(self.first,'first.xlsx'))

    def test_database_outage_blocks_readiness_and_never_uses_local_files(self):
        store=self.store();server=ExplorerServer(('127.0.0.1',0),store)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            self.assertEqual(urlopen(base+'/api/ready').status,200)
            with patch.object(store,'_connect',side_effect=StorageError('Unavailable')):
                self.assertEqual(urlopen(base+'/api/health').status,200)
                for path in ('/api/ready','/api/projects'):
                    with self.assertRaises(HTTPError) as error:urlopen(base+path)
                    self.assertEqual(error.exception.code,503)
            self.assertFalse((self.root/'runtime/projects.json').exists())
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)


if __name__ == '__main__':
    class DiagnosticResult(unittest.TextTestResult):
        def addError(self, test, error):
            # CI uses only fictional credentials and a disposable database.
            # Show the ODBC cause in annotations when application errors hide it.
            cause = error[1].__context__
            if os.environ.get('CI') == 'true' and cause:
                message = str(cause).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
                print('::error title=SQL Server compatibility::' + message)
            super().addError(test, error)
    unittest.main(testRunner=unittest.TextTestRunner(resultclass=DiagnosticResult,verbosity=2))
