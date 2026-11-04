"""Small local HTTP server. Workbook data never leaves this process by default."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

from .workbook import parse_workbook

ROOT = Path(__file__).resolve().parent.parent
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PRESENTATION_BYTES = 2 * 1024 * 1024
BASE_FILENAME = "Remediation_AllCountries.xlsx"


class StorageError(RuntimeError):
    """A persistence error safe to display without leaking connection strings."""


def safe_filename(name: str) -> str:
    """Display-only filename: never use user input as a filesystem path."""
    name = str(name or "").replace("\\", "/").split("/")[-1]
    name = "".join(c for c in name if c.isprintable() and c not in '\r\n"')[:180]
    return name or "Remediation_AllCountries.xlsx"


class NoProjectError(LookupError):
    """The project library is empty or the requested project is unavailable."""


def safe_project_name(name: str, filename: str) -> str:
    name = "".join(c for c in str(name) if c.isprintable()).strip()[:100]
    return name or Path(filename).stem[:100] or "Nuovo progetto"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class WorkbookStore:
    """Independent projects; parse and persist a complete candidate state before commit.

    Local catalog stores current and original XLSX bytes in one atomic JSON file.
    The parsed documents are memory-only caches. One server process owns the library.
    """

    def __init__(self, root: Path = ROOT, database_url: str | None = None):
        self.root = root
        self.lock = threading.RLock()
        self.database_url = database_url
        self.persistence = "postgres" if database_url else "local"
        self.runtime = root / "runtime"
        self.base = root / "data" / "base.xlsx"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.projects = {}
        self.active_project_id = None
        legacy = None
        if database_url:
            state, legacy = self._load_postgres()
        else:
            path = self.runtime / "projects.json"
            try:
                state = json.loads(path.read_text()) if path.exists() else None
            except (OSError, ValueError):
                raise StorageError("Catalogo progetti non leggibile. I file esistenti non sono stati modificati.") from None
        if state is not None:
            self._restore_state(state)
            return
        if legacy is None:
            legacy = self._legacy_local()
        if legacy is not None:
            content, filename = legacy
            self.create(content, filename, Path(filename).stem)
        else:
            # An explicitly empty catalog prevents later accidental legacy re-import.
            self._persist_state({}, None)

    def _legacy_local(self):
        path = self.runtime / "current.xlsx"
        if path.exists():
            content, filename = path.read_bytes(), BASE_FILENAME
            try:
                metadata = json.loads((self.runtime / "current.json").read_text())
                if metadata.get("sha256") == hashlib.sha256(content).hexdigest():
                    filename = safe_filename(metadata.get("filename", BASE_FILENAME))
            except (OSError, ValueError, TypeError, AttributeError):
                pass
            return content, filename
        if self.base.exists():
            return self.base.read_bytes(), BASE_FILENAME
        return None

    @staticmethod
    def _encoded_state(projects, active):
        return {"version": 1, "activeProjectId": active, "projects": [
            {"id": project["id"], "name": project["name"],
             "filename": project["filename"], "initialFilename": project["initialFilename"],
             "updatedAt": project["updatedAt"],
             "content": base64.b64encode(project["content"]).decode("ascii"),
             "initialContent": base64.b64encode(project["initialContent"]).decode("ascii")}
            for project in projects.values()
        ]}

    def _restore_state(self, state):
        try:
            if state.get("version") != 1 or not isinstance(state.get("projects"), list):
                raise ValueError("version")
            projects = {}
            for entry in state["projects"]:
                project_id = entry["id"]
                if str(uuid.UUID(project_id)) != project_id or project_id in projects:
                    raise ValueError("id")
                content = base64.b64decode(entry["content"], validate=True)
                initial = base64.b64decode(entry["initialContent"], validate=True)
                if not content or not initial or max(len(content), len(initial)) > MAX_UPLOAD_BYTES:
                    raise ValueError("size")
                filename = safe_filename(entry["filename"])
                document = parse_workbook(content, filename)
                projects[project_id] = {
                    "id": project_id, "name": safe_project_name(entry["name"], filename),
                    "filename": filename, "initialFilename": safe_filename(entry["initialFilename"]),
                    "updatedAt": entry["updatedAt"], "content": content,
                    "initialContent": initial, "document": document,
                }
            active = state.get("activeProjectId")
            if active is not None and active not in projects:
                raise ValueError("active")
            if projects and active is None:
                raise ValueError("missing active")
        except (ValueError, TypeError, KeyError, AttributeError, binascii.Error):
            raise StorageError("Catalogo progetti non valido. Ripristinare il catalogo conservato; nessun file è stato sostituito.") from None
        self.projects, self.active_project_id = projects, active

    def _connect(self):
        try:
            import psycopg
        except ImportError:
            raise StorageError(
                "DATABASE_URL è configurata: installare requirements-postgres.txt per usare PostgreSQL."
            ) from None
        try:
            return psycopg.connect(self.database_url, connect_timeout=5)
        except Exception:
            raise StorageError("Connessione PostgreSQL non disponibile. Verificare la configurazione del database.") from None

    def _load_postgres(self):
        try:
            with self._connect() as connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS remediation_projects (
                        id uuid PRIMARY KEY,
                        name text NOT NULL,
                        filename text NOT NULL,
                        content bytea NOT NULL,
                        initial_filename text NOT NULL,
                        initial_content bytea NOT NULL,
                        updated_at timestamptz NOT NULL,
                        created_at timestamptz NOT NULL DEFAULT now()
                    )
                """)
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS remediation_library_state (
                        singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
                        active_project_id uuid REFERENCES remediation_projects(id)
                    )
                """)
                active = connection.execute(
                    "SELECT active_project_id FROM remediation_library_state WHERE singleton = true"
                ).fetchone()
                rows = connection.execute(
                    "SELECT id,name,filename,content,initial_filename,initial_content,updated_at "
                    "FROM remediation_projects ORDER BY created_at,id"
                ).fetchall()
                if active is not None:
                    entries = [{"id": str(row[0]), "name": row[1], "filename": row[2],
                                "content": base64.b64encode(bytes(row[3])).decode("ascii"),
                                "initialFilename": row[4],
                                "initialContent": base64.b64encode(bytes(row[5])).decode("ascii"),
                                "updatedAt": row[6].isoformat()} for row in rows]
                    return {"version": 1, "projects": entries,
                            "activeProjectId": str(active[0]) if active[0] else None}, None
                if rows:
                    raise StorageError("Stato PostgreSQL incompleto. Nessun progetto è stato modificato.")
                # Upgrade old single-workbook storage without dropping or changing it.
                existing = connection.execute("SELECT to_regclass('remediation_workbook')").fetchone()
                if existing and existing[0]:
                    legacy = connection.execute(
                        "SELECT content,filename FROM remediation_workbook WHERE singleton = true"
                    ).fetchone()
                    if legacy:
                        return None, (bytes(legacy[0]), safe_filename(legacy[1]))
                return None, None
        except StorageError:
            raise
        except Exception:
            raise StorageError("Impossibile leggere la libreria PostgreSQL. Nessun progetto è stato sostituito.") from None

    def _persist_state(self, projects, active):
        if self.database_url:
            try:
                with self._connect() as connection:
                    for project in projects.values():
                        connection.execute("""
                            INSERT INTO remediation_projects
                                (id,name,filename,content,initial_filename,initial_content,updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (id) DO UPDATE SET name=excluded.name,
                                filename=excluded.filename,content=excluded.content,
                                initial_filename=excluded.initial_filename,
                                initial_content=excluded.initial_content,updated_at=excluded.updated_at
                        """, (project["id"], project["name"], project["filename"], project["content"],
                              project["initialFilename"], project["initialContent"], project["updatedAt"]))
                    connection.execute("""
                        INSERT INTO remediation_library_state (singleton,active_project_id)
                        VALUES (true,%s) ON CONFLICT (singleton) DO UPDATE
                        SET active_project_id=excluded.active_project_id
                    """, (active,))
            except StorageError:
                raise
            except Exception:
                raise StorageError("Salvataggio PostgreSQL non riuscito. La libreria precedente rimane attiva.") from None
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.runtime,
                                             suffix=".json", delete=False) as file:
                temporary = Path(file.name)
                json.dump(self._encoded_state(projects, active), file, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            temporary.replace(self.runtime / "projects.json")
            temporary = None
        except OSError:
            raise StorageError("Salvataggio locale non riuscito. La libreria precedente rimane attiva.") from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _commit(self, projects, active):
        self._persist_state(projects, active)
        self.projects, self.active_project_id = projects, active

    @staticmethod
    def _response(project):
        return {**project["document"], "project": {"id": project["id"], "name": project["name"]}}

    def _active(self):
        if self.active_project_id is None:
            raise NoProjectError("Nessun progetto attivo. Caricare un file Excel per iniziare.")
        return self.projects[self.active_project_id]

    def _selected(self, project_id=None):
        if project_id is None:
            return self._active()
        try:
            valid_id = str(uuid.UUID(project_id)) == project_id
        except (ValueError, AttributeError):
            valid_id = False
        if not valid_id or project_id not in self.projects:
            raise NoProjectError("Progetto non trovato.")
        return self.projects[project_id]

    def create(self, content: bytes, filename: str, name: str = ""):
        with self.lock:
            if not content or len(content) > MAX_UPLOAD_BYTES:
                raise ValueError("Il file deve essere non vuoto e inferiore a 10 MB.")
            filename = safe_filename(filename)
            document = parse_workbook(content, filename)
            project_id = str(uuid.uuid4())
            project = {"id": project_id, "name": safe_project_name(name, filename),
                       "filename": filename, "initialFilename": filename, "updatedAt": timestamp(),
                       "content": content, "initialContent": content, "document": document}
            projects = {**self.projects, project_id: project}
            self._commit(projects, project_id)
            return self._response(project)

    def replace(self, content: bytes, filename: str, project_id=None):
        with self.lock:
            if project_id is None and self.active_project_id is None:
                return self.create(content, filename)
            selected = self._selected(project_id)
            if not content or len(content) > MAX_UPLOAD_BYTES:
                raise ValueError("Il file deve essere non vuoto e inferiore a 10 MB.")
            filename = safe_filename(filename)
            document = parse_workbook(content, filename)
            project = {**selected, "filename": filename, "updatedAt": timestamp(),
                       "content": content, "document": document}
            self._commit({**self.projects, project["id"]: project}, self.active_project_id)
            return self._response(project)

    def activate(self, project_id: str):
        with self.lock:
            self._selected(project_id)
            self._commit(self.projects, project_id)
            return self._response(self.projects[project_id])

    def reset(self, project_id=None):
        with self.lock:
            project = self._selected(project_id)
            return self.replace(project["initialContent"], project["initialFilename"], project["id"])

    def catalog(self):
        with self.lock:
            return {"projects": [
                {"id": project["id"], "name": project["name"], "filename": project["filename"],
                 "rows": len(project["document"].get("rows", [])),
                 "entities": len(project["document"].get("entities", [])),
                 "updatedAt": project["updatedAt"]}
                for project in self.projects.values()
            ], "activeProjectId": self.active_project_id}

    def snapshot(self, project_id=None):
        with self.lock:
            if project_id is None and self.active_project_id is None:
                return None
            return self._response(self._selected(project_id))

    def source(self, project_id=None):
        with self.lock:
            project = self._selected(project_id)
            return project["content"], project["filename"]


class ExplorerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store: WorkbookStore, allowed_hosts=()):
        self.store = store
        self.allowed_hosts = {"localhost", "127.0.0.1", "::1", *allowed_hosts}
        bound_host = address[0]
        if bound_host not in ("0.0.0.0", "::", ""):
            self.allowed_hosts.add(bound_host.lower())
        super().__init__(address, ExplorerHandler)


class ExplorerHandler(BaseHTTPRequestHandler):
    server_version = "DataVisualizationTool/1.0"
    sys_version = ""
    timeout = 30

    def log_message(self, format, *args):
        # Request URLs can contain uploaded filenames. Do not log query strings or data.
        return

    def _send(self, status, content: bytes, content_type: str, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _json(self, status, document):
        self._send(status, json.dumps(document, ensure_ascii=False, allow_nan=False).encode(), "application/json; charset=utf-8")

    def _error(self, status, message):
        self._json(status, {"error": message})

    def _host_allowed(self):
        try:
            host_header = self.headers.get("Host", "")
            parsed = urlsplit("//" + host_header)
            valid = (parsed.hostname or "").lower() in self.server.allowed_hosts
            valid = valid and parsed.username is None and parsed.password is None and not parsed.path
            # Accessing port validates malformed/non-numeric port specifications.
            _ = parsed.port
            return valid
        except ValueError:
            return False

    def _mutation_allowed(self):
        if not self._host_allowed():
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            return False
        origin = self.headers.get("Origin")
        if origin is None:
            return True  # Command-line clients have no Origin header.
        try:
            parsed = urlsplit(origin)
            return (
                parsed.scheme in ("http", "https") and not parsed.path
                and parsed.username is None and parsed.password is None
                and parsed.netloc.lower() == self.headers.get("Host", "").lower()
            )
        except ValueError:
            return False

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self._host_allowed():
            return self._error(HTTPStatus.FORBIDDEN, "Host non autorizzato. Configurare ALLOWED_HOSTS per l'hosting remoto.")
        parsed = urlsplit(self.path)
        path = parsed.path
        project_id = parse_qs(parsed.query, keep_blank_values=True).get("projectId", [None])[0]
        if path == "/api/projects":
            return self._json(HTTPStatus.OK, self.server.store.catalog())
        if path == "/api/workbook":
            try:
                document = self.server.store.snapshot(project_id)
            except NoProjectError as error:
                return self._error(HTTPStatus.NOT_FOUND, str(error))
            if document is None:
                return self._error(HTTPStatus.NOT_FOUND, "Nessun progetto attivo. Caricare un file Excel per iniziare.")
            return self._json(HTTPStatus.OK, document)
        if path == "/api/health":
            document = self.server.store.snapshot() or {}
            return self._json(HTTPStatus.OK, {
                "status": "ok", "storage": self.server.store.persistence,
                "sha256": document.get("source", {}).get("sha256"),
                "rows": len(document.get("rows", [])),
                "entities": len(document.get("entities", [])),
            })
        if path == "/api/source":
            try:
                content, filename = self.server.store.source(project_id)
            except NoProjectError as error:
                return self._error(HTTPStatus.NOT_FOUND, str(error))
            return self._send(HTTPStatus.OK, content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename)})
        static = {
            "/": "index.html", "/index.html": "index.html",
            "/styles.css": "styles.css", "/countries.css": "countries.css",
            "/brand.css": "brand.css",
            "/model.js": "model.js", "/countries.js": "countries.js",
            "/owner-map.js": "owner-map.js", "/app.js": "app.js",
        }
        if path not in static:
            return self._error(HTTPStatus.NOT_FOUND, "Risorsa non trovata.")
        file = self.server.store.root / "web" / static[path]
        try:
            content = file.read_bytes()
        except OSError:
            return self._error(HTTPStatus.NOT_FOUND, "Risorsa non disponibile.")
        mime = {".html": "text/html", ".css": "text/css", ".js": "application/javascript"}[file.suffix]
        self._send(HTTPStatus.OK, content, mime + "; charset=utf-8")

    def do_POST(self):
        if not self._mutation_allowed():
            return self._error(HTTPStatus.FORBIDDEN, "Richiesta non autorizzata: aprire il tool dal suo indirizzo locale.")
        parsed = urlsplit(self.path)
        activation = (parsed.path.startswith("/api/projects/") and parsed.path.endswith("/activate")
                      and parsed.path.count("/") == 4)
        if parsed.path not in ("/api/workbook", "/api/reset", "/api/projects", "/api/presentation") and not activation:
            return self._error(HTTPStatus.NOT_FOUND, "Risorsa non trovata.")
        if self.headers.get("Transfer-Encoding"):
            return self._error(HTTPStatus.BAD_REQUEST, "Trasferimento non supportato.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._error(HTTPStatus.BAD_REQUEST, "Dimensione del file non valida.")
        limit = MAX_PRESENTATION_BYTES if parsed.path == "/api/presentation" else MAX_UPLOAD_BYTES
        if length < 0 or length > limit:
            message = ("La richiesta PowerPoint deve essere inferiore a 2 MB."
                       if parsed.path == "/api/presentation" else "Il file deve essere inferiore a 10 MB.")
            return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, message)
        if parsed.path in ("/api/workbook", "/api/projects") and length == 0:
            return self._error(HTTPStatus.BAD_REQUEST, "Selezionare un file Excel .xlsx.")
        content = self.rfile.read(length)
        if len(content) != length:
            return self._error(HTTPStatus.BAD_REQUEST, "Caricamento del file incompleto.")
        if parsed.path == "/api/presentation":
            return self._presentation(content)
        try:
            query = parse_qs(parsed.query, keep_blank_values=True)
            project_id = query.get("projectId", [None])[0]
            if parsed.path == "/api/reset":
                document = self.server.store.reset(project_id)
            elif activation:
                document = self.server.store.activate(parsed.path.split("/")[3])
            else:
                filename = query.get("filename", [BASE_FILENAME])[0]
                if not filename.lower().endswith(".xlsx"):
                    return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "È supportato solo il formato Excel .xlsx.")
                if parsed.path == "/api/projects":
                    document = self.server.store.create(content, filename, query.get("name", [""])[0])
                else:
                    document = self.server.store.replace(content, filename, project_id)
        except NoProjectError as error:
            return self._error(HTTPStatus.NOT_FOUND, str(error))
        except ValueError as error:
            return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
        except StorageError as error:
            return self._error(HTTPStatus.SERVICE_UNAVAILABLE, str(error))
        except Exception:
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Impossibile caricare il file. Il file precedente rimane attivo.")
        self._json(HTTPStatus.OK, document)

    def _presentation(self, content: bytes):
        """Generate a presentation from one explicit project without changing its data."""
        try:
            def invalid_constant(value):
                raise ValueError("JSON non valido")
            request = json.loads(content.decode("utf-8"), parse_constant=invalid_constant)
        except (ValueError, UnicodeDecodeError, RecursionError):
            return self._error(HTTPStatus.BAD_REQUEST, "La richiesta PowerPoint deve contenere JSON valido.")
        if not isinstance(request, dict):
            return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "La richiesta PowerPoint deve essere un oggetto JSON.")
        project_id = request.get("projectId")
        if not isinstance(project_id, str) or not project_id:
            return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, "Specificare il progetto da esportare in PowerPoint.")
        try:
            document = self.server.store.snapshot(project_id)
            from .presentation_data import build_presentation_data
            from .presentation import create_presentation
            output = create_presentation(build_presentation_data(document, request))
        except NoProjectError as error:
            return self._error(HTTPStatus.NOT_FOUND, str(error))
        except ImportError:
            return self._error(HTTPStatus.SERVICE_UNAVAILABLE,
                               "Esportazione PowerPoint non disponibile. Installare le dipendenze di requirements.txt.")
        except ValueError as error:
            return self._error(HTTPStatus.UNPROCESSABLE_ENTITY, str(error))
        except Exception:
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR,
                               "Impossibile creare il PowerPoint. I dati dei progetti rimangono invariati.")
        if not isinstance(output, bytes):
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Il file PowerPoint non è stato generato correttamente.")
        name = "".join(character for character in document["project"]["name"]
                       if character.isprintable() and character not in '/\\:"<>|?*')[:80].strip(". ") or "progetto"
        filename = f"Data-Visualization-Tool-{name}.pptx"
        self._send(HTTPStatus.OK, output,
                   "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                   {"Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename, safe="")})


def main():
    parser = argparse.ArgumentParser(description="Data Visualization Tool — navigazione Excel locale")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        store = WorkbookStore(database_url=os.environ.get("DATABASE_URL"))
        hosts = [h.strip().lower() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
        server = ExplorerServer((args.host, args.port), store, hosts)
    except (StorageError, ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")
    print(f"Data Visualization Tool avviato sulla porta {server.server_port}. Archivio: {store.persistence}.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
