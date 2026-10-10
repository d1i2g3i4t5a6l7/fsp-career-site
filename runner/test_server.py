"""python -m unittest test_server — без зависимостей. Смена uid проверяется только в контейнере под root."""

import http.client
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path

import server


def run(*files: tuple[str, str], timeout_ms: int = 5000) -> dict:
    body = {"language": "python", "version": "*", "files": [{"name": n, "content": c} for n, c in files], "run_timeout": timeout_ms}
    return server.execute(body)["run"]


class ExecuteTest(unittest.TestCase):
    def test_passing_and_failing_exit_codes(self):
        self.assertEqual(run(("main.py", "print('привет')")), {"stdout": "привет\n", "stderr": "", "output": "привет\n", "code": 0, "signal": None})
        failed = run(("main.py", "import sys; sys.exit(3)"))
        self.assertEqual((failed["code"], failed["signal"]), (3, None))

    def test_entrypoint_imports_files_from_subfolders(self):
        result = run(("run.py", "from pkg.mod import X; print(X)"), ("pkg/__init__.py", ""), ("pkg/mod.py", "X = 42"))
        self.assertEqual(result["stdout"], "42\n", result["stderr"])

    def test_timeout_kills_the_run(self):
        result = run(("main.py", "import time\nwhile True: time.sleep(0.01)"), timeout_ms=300)
        self.assertEqual((result["code"], result["signal"]), (None, "SIGKILL"))

    def test_output_is_capped(self):
        result = run(("main.py", f"print('x' * {server.OUTPUT_LIMIT * 2})"))
        self.assertTrue(result["stdout"].endswith("[вывод обрезан]"))
        self.assertLess(len(result["stdout"]), server.OUTPUT_LIMIT + 100)

    def test_paths_outside_the_box_are_rejected(self):
        for name in ("../escape.py", "/etc/escape.py"):
            with self.assertRaises(server.BadRequest):
                run(("main.py", "print(1)"), (name, "x = 1"))

    def test_unknown_language_is_rejected(self):
        with self.assertRaises(server.BadRequest):
            server.execute({"language": "brainfuck", "files": [{"name": "a", "content": ""}]})


class UnixSocketApiTest(unittest.TestCase):
    """Тот же путь, что у workspace в docker compose: HTTP поверх unix-сокета."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.sock = str(Path(self.dir.name) / "r.sock")
        self.srv = server.make_server(f"unix:{self.sock}")
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.dir.cleanup()

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        conn = http.client.HTTPConnection("runner")
        conn.sock = socket.socket(socket.AF_UNIX)
        conn.sock.connect(self.sock)
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        try:
            return resp.status, json.loads(resp.read())
        finally:
            conn.close()

    def test_execute_and_errors(self):
        status, data = self.request("POST", "/api/v2/execute", {"language": "python", "files": [{"name": "m.py", "content": "print(2 + 2)"}]})
        self.assertEqual((status, data["run"]["stdout"], data["run"]["code"]), (200, "4\n", 0))
        self.assertEqual(self.request("POST", "/api/v2/execute", {"language": "go", "files": []})[0], 400)
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))


if __name__ == "__main__":
    unittest.main()
