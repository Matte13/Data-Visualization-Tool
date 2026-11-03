"""HTTP multi-project isolation, transactional imports and local library migration."""

import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.server import ExplorerServer, WorkbookStore, StorageError
from fixtures import make_workbook


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "web").mkdir()
        (self.root / "web" / "index.html").write_text("<!doctype html><title>Explorer</title>")
        self.first = make_workbook(seed=0, name_prefix="First")
        self.second = make_workbook(seed=200, name_prefix="Second")
        self.store = WorkbookStore(self.root)
        self.server = ExplorerServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def request(self, path, data=None, headers=None, method=None):
        return urlopen(Request(self.origin + path, data=data, headers=headers or {}, method=method), timeout=5)

    def create(self, content=None, name="First project", filename="first.xlsx"):
        with self.request(f"/api/projects?filename={filename}&name={name.replace(' ', '%20')}",
                          content if content is not None else self.first,
                          {"Origin": self.origin}) as response:
            return json.load(response)

    def test_empty_library_health_static_and_missing_workbook(self):
        with self.request("/api/health") as response:
            payload = json.load(response)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["rows"], 0)
            self.assertEqual(payload["entities"], 0)
            self.assertEqual(payload["storage"], "local")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        with self.request("/api/projects") as response:
            self.assertEqual(json.load(response), {"projects": [], "activeProjectId": None})
        for endpoint, data in [("/api/workbook", None), ("/api/source", None), ("/api/reset", b"")]:
            with self.subTest(endpoint=endpoint), self.assertRaises(HTTPError) as failure:
                self.request(endpoint, data)
            self.assertEqual(failure.exception.code, 404)
        with self.request("/") as response:
            self.assertIn(b"Explorer", response.read())
        with self.assertRaises(HTTPError) as failure:
            self.request("/../runtime/projects.json")
        self.assertEqual(failure.exception.code, 404)

    def test_brand_stylesheet_and_embedded_fonts_remain_local(self):
        stylesheet = '@font-face{font-family:KPMG;src:url(data:font/woff2;base64,d09GMg==) format("woff2")}'
        (self.root / "web" / "brand.css").write_text(stylesheet)
        with self.request("/brand.css") as response:
            self.assertEqual(response.read().decode(), stylesheet)
            self.assertEqual(response.headers["Content-Type"], "text/css; charset=utf-8")
            policy = response.headers["Content-Security-Policy"]
            self.assertIn("font-src 'self' data:;", policy)
            self.assertIn("default-src 'self';", policy)
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        # The stylesheet route does not expose an arbitrary asset directory.
        with self.assertRaises(HTTPError) as failure:
            self.request("/assets/../runtime/projects.json")
        self.assertEqual(failure.exception.code, 404)

    def test_create_activate_restart_and_project_isolation(self):
        first = self.create()
        second = self.create(self.second, "Second project", "second.xlsx")
        first_id, second_id = first["project"]["id"], second["project"]["id"]
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(len(first["rows"]), 7)
        self.assertEqual(first["rows"][0]["name"], "First governance")
        self.assertEqual(second["rows"][0]["name"], "Second governance")
        with self.request("/api/projects") as response:
            catalog = json.load(response)
        self.assertEqual(len(catalog["projects"]), 2)
        self.assertEqual(catalog["activeProjectId"], second_id)
        self.assertTrue(all(project["rows"] == 7 for project in catalog["projects"]))
        self.assertTrue(all(project["entities"] == 21 for project in catalog["projects"]))
        with self.request(f"/api/projects/{first_id}/activate", b"", {"Origin": self.origin}) as response:
            active = json.load(response)
        self.assertEqual(active["project"], {"id": first_id, "name": "First project"})
        self.assertEqual(active["source"]["sha256"], hashlib.sha256(self.first).hexdigest())
        with self.request("/api/source") as response:
            self.assertEqual(response.read(), self.first)
        reloaded = WorkbookStore(self.root)
        self.assertEqual(reloaded.catalog()["activeProjectId"], first_id)
        self.assertEqual(len(reloaded.catalog()["projects"]), 2)
        self.assertEqual(reloaded.source(), (self.first, "first.xlsx"))
        reloaded.activate(second_id)
        self.assertEqual(reloaded.source(), (self.second, "second.xlsx"))

    def test_same_filename_import_always_creates_independent_project(self):
        first = self.create(filename="same.xlsx")
        second = self.create(self.second, "Separate project", "same.xlsx")
        self.assertNotEqual(first["project"]["id"], second["project"]["id"])
        self.assertEqual(len(self.store.catalog()["projects"]), 2)

    def test_explicit_project_binding_keeps_other_tab_and_active_project_unchanged(self):
        first = self.create()
        second = self.create(self.second, "Second project", "second.xlsx")
        first_id, second_id = first["project"]["id"], second["project"]["id"]
        updated = make_workbook(seed=400, name_prefix="Updated first")
        # A second tab has activated B. The first tab must still mutate/download A.
        with self.request(f"/api/workbook?filename=updated-first.xlsx&projectId={first_id}",
                          updated, {"Origin": self.origin}) as response:
            replaced = json.load(response)
        self.assertEqual(replaced["project"], first["project"])
        self.assertEqual(self.store.catalog()["activeProjectId"], second_id)
        with self.request(f"/api/source?projectId={first_id}") as response:
            self.assertEqual(response.read(), updated)
        with self.request(f"/api/workbook?projectId={first_id}") as response:
            self.assertEqual(json.load(response)["source"]["filename"], "updated-first.xlsx")
        with self.request("/api/workbook") as response:
            self.assertEqual(json.load(response)["project"], second["project"])
        with self.request(f"/api/reset?projectId={first_id}", b"", {"Origin": self.origin}) as response:
            self.assertEqual(json.load(response)["project"], first["project"])
        self.assertEqual(self.store.source(first_id), (self.first, "first.xlsx"))
        self.assertEqual(self.store.source(), (self.second, "second.xlsx"))
        reloaded = WorkbookStore(self.root)
        self.assertEqual(reloaded.catalog()["activeProjectId"], second_id)
        self.assertEqual(reloaded.source(first_id), (self.first, "first.xlsx"))
        self.assertEqual(reloaded.source(second_id), (self.second, "second.xlsx"))

    def test_invalid_explicit_project_never_falls_back_to_active_project(self):
        self.create()
        before = self.store.catalog()
        for path, data in [("/api/source", None), ("/api/workbook", None),
                           ("/api/reset", b""), ("/api/workbook", self.second)]:
            with self.subTest(path=path, data=data is not None), self.assertRaises(HTTPError) as failure:
                self.request(path + "?projectId=not-a-project&filename=other.xlsx", data)
            self.assertEqual(failure.exception.code, 404)
        self.assertEqual(self.store.catalog(), before)
        self.assertEqual(self.store.source()[0], self.first)

    def test_replace_and_reset_only_active_project_to_own_initial_file(self):
        first = self.create()
        second = self.create(self.second, "Second project", "second.xlsx")
        first_id = first["project"]["id"]
        self.store.activate(first_id)
        with self.request("/api/workbook?filename=updated.xlsx", self.second,
                          {"Origin": self.origin}) as response:
            replaced = json.load(response)
        self.assertEqual(replaced["project"], first["project"])
        self.assertEqual(replaced["source"]["filename"], "updated.xlsx")
        self.assertEqual(self.store.source()[0], self.second)
        with self.request("/api/reset", b"", {"Origin": self.origin}) as response:
            reset = json.load(response)
        self.assertEqual(reset["project"], first["project"])
        self.assertEqual(self.store.source(), (self.first, "first.xlsx"))
        self.store.activate(second["project"]["id"])
        self.assertEqual(self.store.source(), (self.second, "second.xlsx"))
        self.store.reset()
        self.assertEqual(self.store.source(), (self.second, "second.xlsx"))
        reloaded = WorkbookStore(self.root)
        reloaded.activate(first_id)
        self.assertEqual(reloaded.source(), (self.first, "first.xlsx"))

    def test_legacy_import_creates_when_no_project_exists(self):
        with self.request("/api/workbook?filename=legacy.xlsx", self.first,
                          {"Origin": self.origin}) as response:
            document = json.load(response)
        self.assertEqual(document["project"]["name"], "legacy")
        self.assertEqual(len(self.store.catalog()["projects"]), 1)

    def test_invalid_import_keeps_active_project_and_entire_catalog(self):
        self.create()
        previous = (self.root / "runtime" / "projects.json").read_bytes()
        original = self.store.catalog()
        for endpoint in ("/api/projects?filename=invalid.xlsx", "/api/workbook?filename=invalid.xlsx"):
            with self.subTest(endpoint=endpoint), self.assertRaises(HTTPError) as failure:
                self.request(endpoint, b"bad bytes", {"Origin": self.origin})
            self.assertEqual(failure.exception.code, 422)
            self.assertEqual(self.store.catalog(), original)
            self.assertEqual((self.root / "runtime" / "projects.json").read_bytes(), previous)
            self.assertEqual(self.store.source(), (self.first, "first.xlsx"))

    def test_failed_storage_keeps_memory_and_disk_state(self):
        self.create()
        previous = (self.root / "runtime" / "projects.json").read_bytes()
        catalog = self.store.catalog()
        with patch.object(self.store, "_persist_state", side_effect=StorageError("Storage unavailable")):
            with self.assertRaises(HTTPError) as failure:
                self.request("/api/projects?filename=new.xlsx", self.second)
            self.assertEqual(failure.exception.code, 503)
        self.assertEqual(self.store.catalog(), catalog)
        self.assertEqual((self.root / "runtime" / "projects.json").read_bytes(), previous)

    def test_cross_origin_dns_rebinding_and_bad_project_ids_are_rejected(self):
        self.create()
        with self.assertRaises(HTTPError) as failure:
            self.request("/api/reset", b"", {"Origin": "https://example.invalid"})
        self.assertEqual(failure.exception.code, 403)
        with self.assertRaises(HTTPError) as failure:
            self.request("/api/projects", headers={"Host": "example.invalid"})
        self.assertEqual(failure.exception.code, 403)
        for project_id in ("invalid", "00000000-0000-0000-0000-000000000000", ".."):
            with self.subTest(id=project_id), self.assertRaises(HTTPError) as failure:
                self.request(f"/api/projects/{project_id}/activate", b"")
            self.assertEqual(failure.exception.code, 404)
        self.assertEqual(self.store.source()[0], self.first)

    def test_upload_validation(self):
        with self.assertRaises(HTTPError) as failure:
            self.request("/api/projects?filename=other.xls", self.first)
        self.assertEqual(failure.exception.code, 422)
        with self.assertRaises(HTTPError) as failure:
            self.request("/api/projects", b"")
        self.assertEqual(failure.exception.code, 400)
        with self.assertRaises(HTTPError) as failure:
            self.request("/api/workbook", b"x", {"Content-Length": str(11 * 1024 * 1024)})
        self.assertEqual(failure.exception.code, 413)

    def test_existing_base_or_current_seed_without_deleting_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data" / "base.xlsx").write_bytes(self.first)
            seeded = WorkbookStore(root)
            self.assertEqual(len(seeded.catalog()["projects"]), 1)
            self.assertEqual(seeded.source()[0], self.first)
            self.assertEqual((root / "data" / "base.xlsx").read_bytes(), self.first)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "runtime").mkdir()
            (root / "runtime" / "current.xlsx").write_bytes(self.second)
            (root / "runtime" / "current.json").write_text(json.dumps({
                "filename": "old-current.xlsx", "sha256": hashlib.sha256(self.second).hexdigest()}))
            seeded = WorkbookStore(root)
            self.assertEqual(seeded.source(), (self.second, "old-current.xlsx"))
            self.assertEqual((root / "runtime" / "current.xlsx").read_bytes(), self.second)
            seeded.replace(self.first, "new.xlsx")
            seeded.reset()
            self.assertEqual(seeded.source(), (self.second, "old-current.xlsx"))

    def test_corrupt_catalog_does_not_fallback_to_legacy_or_destroy_it(self):
        self.create()
        path = self.root / "runtime" / "projects.json"
        path.write_text("{invalid")
        with self.assertRaisesRegex(StorageError, "Catalogo"):
            WorkbookStore(self.root)
        self.assertEqual(path.read_text(), "{invalid")

    def test_configured_postgres_has_no_silent_fallback(self):
        with patch.object(WorkbookStore, "_connect", side_effect=StorageError("database unavailable")):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                WorkbookStore(self.root, database_url="postgresql://not-a-real-host/db")


if __name__ == "__main__":
    unittest.main()
