import asyncio
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from app.tasks import RunSpec


@dataclass
class RunResult:
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def summary(self, limit: int = 4000) -> str:
        head = "Время вышло" if self.timed_out else f"Код выхода: {self.exit_code}"
        text = f"{head}\n{self.stdout}\n{self.stderr}".strip()
        return text if len(text) <= limit else text[: limit // 2] + "\n…\n" + text[-limit // 2 :]


class Runner(Protocol):
    async def run(self, files: dict[str, str], spec: RunSpec) -> RunResult: ...


class LocalRunner:
    """Запуск прямо на машине — ТОЛЬКО для разработки: код кандидата исполняется без изоляции."""

    def __init__(self, timeout_s: float = 20.0):
        self._timeout_s = timeout_s

    async def run(self, files: dict[str, str], spec: RunSpec) -> RunResult:
        return await asyncio.to_thread(self._run_sync, files, spec)

    def _run_sync(self, files: dict[str, str], spec: RunSpec) -> RunResult:
        if spec.language != "python":
            return RunResult(None, "", f"Локальный запуск поддерживает только python, а не {spec.language}", 0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for path, content in files.items():
                target = (root / path).resolve()
                if not target.is_relative_to(root):
                    return RunResult(None, "", f"Недопустимый путь: {path}", 0)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
            if "SYSTEMROOT" in os.environ:  # без него Python на Windows не стартует
                env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
            started = time.monotonic()
            try:
                proc = subprocess.run(
                    # -E -s: без PYTHON* переменных и пользовательских пакетов; папка с файлами задачи — в sys.path
                    [sys.executable, "-E", "-s", spec.entrypoint],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self._timeout_s,
                )
            except subprocess.TimeoutExpired as exc:
                return RunResult(None, _decode(exc.stdout), _decode(exc.stderr), _ms_since(started), timed_out=True)
            return RunResult(proc.returncode, proc.stdout, proc.stderr, _ms_since(started))


class PistonRunner:
    """Песочница по API Piston: наш контейнер runner/ или сам Piston (https://github.com/engineer-man/piston).

    url — http://host:port или unix:/путь/к/сокету: runner запущен без сети и слушает сокет в общем томе.
    У настоящего Piston лимит времени запуска по умолчанию 3 с, а вывод режется до 1 КБ —
    поднять PISTON_RUN_TIMEOUT и PISTON_OUTPUT_MAX_SIZE.
    """

    def __init__(self, url: str, timeout_s: float = 20.0, client: httpx.AsyncClient | None = None):
        self._timeout_s = timeout_s
        transport = None
        if url.startswith("unix:"):
            transport = httpx.AsyncHTTPTransport(uds=url.removeprefix("unix:"))
            url = "http://runner"
        self._url = url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout_s + 10, transport=transport)

    async def run(self, files: dict[str, str], spec: RunSpec) -> RunResult:
        if spec.entrypoint not in files:
            return RunResult(None, "", f"Нет файла запуска {spec.entrypoint}", 0)
        # Piston запускает первый файл из списка
        ordered = [{"name": spec.entrypoint, "content": files[spec.entrypoint]}]
        ordered += [{"name": p, "content": c} for p, c in files.items() if p != spec.entrypoint]
        body = {
            "language": spec.language,
            "version": spec.version,
            "files": ordered,
            "run_timeout": int(self._timeout_s * 1000),
        }
        started = time.monotonic()
        try:
            resp = await self._client.post(f"{self._url}/api/v2/execute", json=body)
        except httpx.TransportError as exc:
            return RunResult(None, "", f"Песочница недоступна: {exc}", _ms_since(started))
        if resp.status_code >= 400:
            return RunResult(None, "", f"Песочница ответила {resp.status_code}: {resp.text[:300]}", _ms_since(started))
        run = resp.json().get("run", {})
        return RunResult(
            exit_code=run.get("code"),
            stdout=run.get("stdout", ""),
            stderr=run.get("stderr", ""),
            duration_ms=_ms_since(started),
            timed_out=run.get("signal") == "SIGKILL",
        )


def _ms_since(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _decode(value: bytes | str | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value
