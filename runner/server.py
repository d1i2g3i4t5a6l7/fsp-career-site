"""Песочница для кода кандидата: HTTP-API в формате Piston (POST /api/v2/execute).

Свой сервер вместо Piston: работает в любом Docker без privileged, пакеты ставятся при сборке образа.
Изоляцию даёт контейнер: без сети (network_mode: none), файловая система только для чтения, лимиты памяти
и процессов. API слушает unix-сокет в томе, общем с workspace.

Внутри контейнера каждый одновременный запуск идёт под своим непривилегированным uid: код кандидата
не может трогать сервер и чужие запуски. После запуска все его процессы убиваются. Время, вывод
и размер файлов ограничены.

Вне контейнера (разработка) uid не переключается — это уже не изоляция, только совместимость API.
"""

import json
import os
import platform
import queue
import shutil
import signal
import socketserver
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# unix:/путь/к/сокету или tcp:host:port
LISTEN = os.environ.get("RUNNER_LISTEN", "unix:/run/runner/runner.sock")
SLOTS = int(os.environ.get("RUNNER_SLOTS", "4"))
MAX_TIMEOUT_S = float(os.environ.get("RUNNER_MAX_TIMEOUT_S", "60"))
DEFAULT_TIMEOUT_MS = 20_000
OUTPUT_LIMIT = int(os.environ.get("RUNNER_OUTPUT_LIMIT", str(64 * 1024)))
# Любой файл, который пишет код кандидата, включая stdout и stderr
FILE_LIMIT = int(os.environ.get("RUNNER_FILE_LIMIT", str(10 * 1024 * 1024)))
NPROC_LIMIT = int(os.environ.get("RUNNER_NPROC_LIMIT", "64"))
BASE_UID = int(os.environ.get("RUNNER_BASE_UID", "20000"))
# Группа workspace: только она может подключиться к сокету
SOCKET_GID = int(os.environ.get("RUNNER_SOCKET_GID", "10001"))
MAX_BODY = 20 * 1024 * 1024

ISOLATE = sys.platform == "linux" and os.geteuid() == 0
VERSION = platform.python_version()
LANGUAGES = {"python", "python3", "py"}

# Выполняется в дочернем процессе перед кодом кандидата: лимиты, затем exec в интерпретатор.
# Лимиты ставит сам потомок, а не preexec_fn — тот небезопасен в многопоточном сервере.
_LAUNCHER = """import os, resource, sys
fsize, nproc, entry = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
if nproc:
    resource.setrlimit(resource.RLIMIT_NPROC, (nproc, nproc))
os.execv(sys.executable, [sys.executable, "-E", "-s", entry])
"""

_slots: queue.Queue[int] = queue.Queue()
for _i in range(SLOTS):
    _slots.put(_i)


class BadRequest(Exception):
    pass


def execute(body: dict) -> dict:
    if body.get("language") not in LANGUAGES:
        raise BadRequest(f"{body.get('language')}-{body.get('version')} runtime is unknown")
    files = body.get("files") or []
    if not files or not all(isinstance(f, dict) and f.get("name") for f in files):
        raise BadRequest("files: нужен хотя бы один файл с name; первый — точка входа")
    timeout_s = min(float(body.get("run_timeout") or DEFAULT_TIMEOUT_MS) / 1000, MAX_TIMEOUT_S)
    slot = _slots.get()  # больше SLOTS запусков одновременно не идёт — остальные ждут
    try:
        run = _run(files, str(body.get("stdin") or ""), timeout_s, slot)
    finally:
        _slots.put(slot)
    return {"language": "python", "version": VERSION, "run": run}


def _run(files: list[dict], stdin: str, timeout_s: float, slot: int) -> dict:
    uid = BASE_UID + slot if ISOLATE else None
    box = Path(tempfile.mkdtemp(prefix="box-")).resolve()
    logs = Path(tempfile.mkdtemp(prefix="log-"))  # вывод — вне папки кандидата, ему недоступен
    try:
        for f in files:
            target = (box / f["name"]).resolve()
            if not target.is_relative_to(box) or target == box:
                raise BadRequest(f"Недопустимый путь: {f['name']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(f.get("content", "")), encoding="utf-8")
        if uid is not None:
            for path in [box, *box.rglob("*")]:
                os.chown(path, uid, uid)
            os.chmod(box, 0o700)

        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(box), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
        cmd = [sys.executable, "-E", "-s", "-c", _LAUNCHER, str(FILE_LIMIT), str(NPROC_LIMIT if uid else 0), files[0]["name"]]
        with open(logs / "stdout", "wb") as out, open(logs / "stderr", "wb") as err:
            proc = subprocess.Popen(
                cmd,
                cwd=box,
                env=env,
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                start_new_session=True,
                user=uid,
                group=uid,
                extra_groups=[] if uid is not None else None,
            )
            timed_out = False
            try:
                proc.communicate(stdin.encode(), timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_group(proc.pid)
                proc.wait()
            finally:
                if uid is not None:
                    _kill_uid(uid)  # то, что кандидат успел увести из группы процессов
                    _remove_uid_files(uid)  # чтобы следующий запуск под тем же uid их не прочитал
        stdout, stderr = _read(logs / "stdout"), _read(logs / "stderr")
        return {
            "stdout": stdout,
            "stderr": stderr,
            "output": stdout + stderr,
            "code": None if timed_out else proc.returncode,
            "signal": "SIGKILL" if timed_out else None,
        }
    finally:
        shutil.rmtree(box, ignore_errors=True)
        shutil.rmtree(logs, ignore_errors=True)


def _read(path: Path) -> str:
    with open(path, "rb") as f:
        data = f.read(OUTPUT_LIMIT + 1)
    text = data[:OUTPUT_LIMIT].decode("utf-8", "replace")
    return text + "\n…[вывод обрезан]" if len(data) > OUTPUT_LIMIT else text


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _kill_uid(uid: int) -> None:
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            if os.stat(f"/proc/{entry}").st_uid == uid:
                os.kill(int(entry), signal.SIGKILL)
        except (FileNotFoundError, ProcessLookupError):
            pass


def _remove_uid_files(uid: int) -> None:
    for shared in ("/tmp", "/dev/shm"):
        try:
            entries = list(os.scandir(shared))
        except FileNotFoundError:
            continue
        for entry in entries:
            try:
                if entry.stat(follow_symlinks=False).st_uid != uid:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    shutil.rmtree(entry.path, ignore_errors=True)
                else:
                    os.unlink(entry.path)
            except FileNotFoundError:
                pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        if self.path == "/api/v2/runtimes":
            self._send(200, [{"language": "python", "version": VERSION, "aliases": sorted(LANGUAGES - {"python"})}])
        elif self.path == "/health":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"message": "Not found"})

    def do_POST(self) -> None:
        if self.path != "/api/v2/execute":
            self._send(404, {"message": "Not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(413, {"message": "Слишком большой запрос"})
            self.close_connection = True
            return
        try:
            self._send(200, execute(json.loads(self.rfile.read(length) or b"{}")))
        except (BadRequest, ValueError, TypeError) as exc:
            self._send(400, {"message": str(exc)})

    def _send(self, code: int, payload) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        # Адрес клиента у unix-сокета пустой — стандартный лог на нём падает
        sys.stderr.write(f"runner: {fmt % args}\n")


class UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def make_server(listen: str) -> socketserver.BaseServer:
    if listen.startswith("unix:"):
        path = listen.removeprefix("unix:")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).unlink(missing_ok=True)  # сокет от прошлого запуска
        server = UnixHTTPServer(path, Handler)
        if ISOLATE:
            os.chown(path, 0, SOCKET_GID)
        os.chmod(path, 0o660)
        return server
    host, _, port = listen.removeprefix("tcp:").rpartition(":")
    return ThreadingHTTPServer((host or "0.0.0.0", int(port)), Handler)


def main() -> None:
    server = make_server(LISTEN)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    mode = "uid на каждый запуск" if ISOLATE else "без смены uid (разработка)"
    print(f"runner: Python {VERSION}, {LISTEN}, слотов {SLOTS}, {mode}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
