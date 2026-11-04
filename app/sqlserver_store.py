"""Azure SQL / SQL Server persistence, with encrypted ODBC connections.

Uses an existing database. Only two application tables are initialized; a
transaction-owned application lock protects rolling revisions and all writes.
"""
from contextlib import contextmanager
import base64
from pathlib import Path
import re
import threading

from .server import WorkbookStore, StorageError, NoProjectError, ROOT


class AzureSqlStore(WorkbookStore):
    def __init__(self, connection_string: str, root: Path = ROOT, schema: str = 'dbo'):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}', schema):
            raise ValueError('Schema Azure SQL non valido.')
        self.root = root
        self.runtime = root / 'runtime'
        self.lock = threading.RLock()
        self.persistence = 'azuresql'
        self.projects = {}
        self.active_project_id = None
        self._connection_string = connection_string
        self._sql_connection = None
        self._initialized = False
        self._projects_table = f'[{schema}].[dvt_projects]'
        self._state_table = f'[{schema}].[dvt_library_state]'
        self._resource = f'data-visualization-tool:{schema}:library-v1'
        with self._operation():
            pass

    def _connect(self):
        try:
            import pyodbc
        except ImportError:
            raise StorageError('Installare requirements-azuresql.txt e Microsoft ODBC Driver 18 per usare Azure SQL.') from None
        try:
            connection = pyodbc.connect(self._connection_string, timeout=5, autocommit=True)
            connection.timeout = 15
            return connection
        except Exception:
            raise StorageError('Connessione Azure SQL non disponibile. Verificare rete e configurazione del database.') from None

    def _initialize(self, connection):
        # Identifiers are validated above; workbook values are always parameters.
        connection.execute(f"""
            IF OBJECT_ID(N'{self._projects_table}', N'U') IS NULL
            CREATE TABLE {self._projects_table} (
                id uniqueidentifier NOT NULL PRIMARY KEY,
                name nvarchar(200) NOT NULL,
                filename nvarchar(360) NOT NULL,
                content varbinary(max) NOT NULL,
                initial_filename nvarchar(360) NOT NULL,
                initial_content varbinary(max) NOT NULL,
                updated_at datetimeoffset(0) NOT NULL,
                created_at datetime2 NOT NULL DEFAULT SYSUTCDATETIME()
            )
        """)
        connection.execute(f"""
            IF OBJECT_ID(N'{self._state_table}', N'U') IS NULL
            CREATE TABLE {self._state_table} (
                singleton tinyint NOT NULL PRIMARY KEY CHECK (singleton = 1),
                active_project_id uniqueidentifier NULL REFERENCES {self._projects_table}(id)
            )
        """)

    @contextmanager
    def _operation(self):
        with self.lock:
            if self._sql_connection is not None:
                yield
                return
            previous = self.projects, self.active_project_id
            connection = None
            try:
                connection = self._connect()
                connection.execute('SET XACT_ABORT ON; SET LOCK_TIMEOUT 10000; BEGIN TRANSACTION;')
                connection.execute("""
                    DECLARE @result int;
                    EXEC @result = sys.sp_getapplock @Resource = ?, @LockMode = 'Exclusive',
                        @LockOwner = 'Transaction', @LockTimeout = 10000;
                    IF @result < 0 THROW 50001, 'Project library is busy.', 1;
                """, self._resource)
                self._sql_connection = connection
                if not self._initialized:
                    self._initialize(connection)
                state = self._load_sql(connection)
                if state is None:
                    self._persist_state({}, None)
                    self.projects, self.active_project_id = {}, None
                else:
                    self._restore_state(state)
                yield
                connection.execute('COMMIT TRANSACTION;')
                self._initialized = True
            except Exception as error:
                self.projects, self.active_project_id = previous
                if connection is not None:
                    try:
                        connection.execute('IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;')
                    except Exception:
                        pass
                if isinstance(error, (ValueError, NoProjectError, StorageError)):
                    raise
                raise StorageError('Operazione Azure SQL non riuscita. Nessun dato è stato sostituito.') from None
            finally:
                self._sql_connection = None
                if connection is not None:
                    connection.close()

    def _load_sql(self, connection):
        active = connection.execute(f'SELECT active_project_id FROM {self._state_table} WHERE singleton = 1').fetchone()
        rows = connection.execute(f"""
            SELECT CONVERT(nvarchar(36), id), name, filename, content, initial_filename,
                initial_content, CONVERT(nvarchar(35), updated_at, 127)
            FROM {self._projects_table} ORDER BY created_at, id
        """).fetchall()
        if active is None:
            if rows:
                raise StorageError('Stato Azure SQL incompleto. Nessun progetto è stato modificato.')
            return None
        return {'version': 1, 'activeProjectId': str(active[0]).lower() if active[0] else None,
                'projects': [
                    {'id': row[0].lower(), 'name': row[1], 'filename': row[2],
                     'content': base64.b64encode(bytes(row[3])).decode('ascii'),
                     'initialFilename': row[4],
                     'initialContent': base64.b64encode(bytes(row[5])).decode('ascii'),
                     'updatedAt': row[6]}
                    for row in rows]}

    def _persist_state(self, projects, active):
        connection = self._sql_connection
        if connection is None:
            raise StorageError('Salvataggio Azure SQL richiesto fuori dalla transazione.')
        for project in projects.values():
            values = (project['name'], project['filename'], project['content'],
                      project['initialFilename'], project['initialContent'],
                      project['updatedAt'], project['id'])
            cursor = connection.execute(f"""
                UPDATE {self._projects_table} SET name=?, filename=?, content=?,
                    initial_filename=?, initial_content=?, updated_at=? WHERE id=?
            """, *values)
            if cursor.rowcount == 0:
                connection.execute(f"""
                    INSERT INTO {self._projects_table}
                        (name,filename,content,initial_filename,initial_content,updated_at,id)
                    VALUES (?,?,?,?,?,?,?)
                """, *values)
        cursor = connection.execute(f'UPDATE {self._state_table} SET active_project_id=? WHERE singleton=1', active)
        if cursor.rowcount == 0:
            connection.execute(f'INSERT INTO {self._state_table} (singleton,active_project_id) VALUES (1,?)', active)

    def ready(self):
        connection = self._connect()
        try:
            connection.execute('SELECT 1').fetchone()
        except Exception:
            raise StorageError('Azure SQL non disponibile.') from None
        finally:
            connection.close()
        return True
