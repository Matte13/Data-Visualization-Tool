"""Real PostgreSQL tests use a new isolated schema, never the application tables.

Set TEST_DATABASE_URL for CI, or RUN_POSTGRES_TESTS=1 in the disposable test
container to use its PG* settings. No service is created by this test module.
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
from app.server import WorkbookStore, ExplorerServer, StorageError
from fixtures import make_workbook

ENABLED=bool(os.environ.get('TEST_DATABASE_URL') or os.environ.get('RUN_POSTGRES_TESTS')=='1')


@unittest.skipUnless(ENABLED,'Set TEST_DATABASE_URL to run real PostgreSQL integration tests')
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        self.psycopg,self.sql=psycopg,sql
        self.config=RuntimeConfig.from_environ({'DATABASE_URL':os.environ['TEST_DATABASE_URL']}) if os.environ.get('TEST_DATABASE_URL') else RuntimeConfig.from_environ()
        self.schema='dvt_test_'+uuid.uuid4().hex
        with psycopg.connect(self.config.database_url or '',**(self.config.database_options or {})) as connection:
            connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.options={**(self.config.database_options or {}),'options':'-c search_path='+self.schema}
        self.first=make_workbook(name_prefix='First',compact=True,include_ot=False)
        self.second=make_workbook(name_prefix='Second',compact=True,include_ot=False)

    def tearDown(self):
        with self.psycopg.connect(self.config.database_url or '',**(self.config.database_options or {})) as connection:
            connection.execute(self.sql.SQL('DROP SCHEMA {} CASCADE').format(self.sql.Identifier(self.schema)))
        self.temp.cleanup()

    def store(self):
        return WorkbookStore(self.root,database_url=self.config.database_url,database_options=self.options)

    def test_projects_updates_reset_and_restart_persist(self):
        store=self.store();first=store.create(self.first,'first.xlsx','First')
        second=store.create(self.second,'second.xlsx','Second')
        key=first['project']['id'];other=second['project']['id']
        store.replace(self.second,'updated.xlsx',key)
        restarted=self.store()
        self.assertEqual(restarted.source(key),(self.second,'updated.xlsx'))
        restarted.reset(key)
        self.assertEqual(store.source(key),(self.first,'first.xlsx'))
        self.assertEqual(store.source(other),(self.second,'second.xlsx'))
        self.assertEqual(len(restarted.catalog()['projects']),2)

    def test_independent_stores_refresh_and_do_not_overwrite_other_projects(self):
        left,right=self.store(),self.store()
        first=left.create(self.first,'first.xlsx','First')['project']['id']
        second=right.create(self.second,'second.xlsx','Second')['project']['id']
        self.assertEqual(len(left.catalog()['projects']),2)
        left.replace(self.second,'changed.xlsx',first)
        right.activate(second)
        self.assertEqual(right.source(first),(self.second,'changed.xlsx'))
        self.assertEqual(left.catalog()['activeProjectId'],second)

    def test_concurrent_writers_keep_every_committed_project(self):
        stores=[self.store(),self.store()]
        def writer(index):
            return [stores[index].create(self.first,f'{index}-{n}.xlsx',f'Project {index}-{n}')['project']['id'] for n in range(3)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            keys=[key for batch in pool.map(writer,range(2)) for key in batch]
        catalog=self.store().catalog()
        self.assertEqual({p['id'] for p in catalog['projects']},set(keys))

    def test_failed_write_rolls_back_database_and_memory(self):
        store=self.store();key=store.create(self.first,'first.xlsx','First')['project']['id']
        original=store._persist_state
        def failing_write(projects,active):
            original(projects,active)
            raise StorageError('Synthetic failure before transaction commit')
        with patch.object(store,'_persist_state',side_effect=failing_write):
            with self.assertRaises(StorageError):store.replace(self.second,'changed.xlsx',key)
        self.assertEqual(store.source(key),(self.first,'first.xlsx'))
        self.assertEqual(self.store().source(key),(self.first,'first.xlsx'))

    def test_database_outage_affects_readiness_but_not_liveness(self):
        store=self.store();server=ExplorerServer(('127.0.0.1',0),store)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        try:
            self.assertEqual(urlopen(origin+'/api/ready').status,200)
            with patch.object(store,'_connect',side_effect=StorageError('Unavailable')):
                self.assertEqual(urlopen(origin+'/api/health').status,200)
                with self.assertRaises(HTTPError) as error:urlopen(origin+'/api/ready')
                self.assertEqual(error.exception.code,503)
                with self.assertRaises(HTTPError) as error:urlopen(origin+'/api/projects')
                self.assertEqual(error.exception.code,503)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
