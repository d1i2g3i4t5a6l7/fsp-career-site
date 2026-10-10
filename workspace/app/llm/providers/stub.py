"""Заглушка LLM для разработки без ключей и сети.

Не пытается быть умной: по ключевым словам изображает типовые ходы ассистента,
а судья ставит всё «да», если прошли автотесты, — чтобы весь путь от задачи до грейда
можно было пройти руками.
"""

import asyncio
import json
import re
import uuid

from app.llm.providers.base import OnDelta
from app.llm.types import ChatRequest, ChatResult, Message, ToolCall

_FIX_WORDS = ("исправ", "почин", "правк", "fix")
_TEST_WORDS = ("тест", "запусти")
_FILE_WORDS = ("файл",)


class StubProvider:
    def __init__(self, chunk_delay_s: float = 0.03):
        self._chunk_delay_s = chunk_delay_s

    async def chat(self, req: ChatRequest, on_delta: OnDelta | None = None) -> ChatResult:
        if req.scenario == "assistant":
            result = _assistant_step(req)
        elif req.scenario == "grader":
            result = _text(_judge(req))
        elif req.scenario == "task_gen":
            result = _text(_task_draft(req))
        else:
            result = _text("(заглушка LLM) ответ не настроен для сценария " + req.scenario)
        if on_delta is not None:
            # изображаем потоковую генерацию: по паре слов с паузой
            content = result.message.content
            chunks = re.findall(r"\s*\S+(?:\s+\S+)?", content)
            tail = content[len("".join(chunks)) :]
            for chunk in chunks + ([tail] if tail else []):
                await asyncio.sleep(self._chunk_delay_s)
                await on_delta(chunk)
        return result


def _text(content: str) -> ChatResult:
    return ChatResult(message=Message(role="assistant", content=content), finish_reason="stop")


def _call(name: str, **arguments) -> ChatResult:
    call = ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments=arguments)
    return ChatResult(message=Message(role="assistant", tool_calls=[call]), finish_reason="function_call")


def _assistant_step(req: ChatRequest) -> ChatResult:
    last_user = max(i for i, m in enumerate(req.messages) if m.role == "user")
    # служебные строки «[Событие: …]» и «[Система: …]» — не слова кандидата
    question = "\n".join(
        line for line in req.messages[last_user].content.lower().splitlines() if not line.startswith("[")
    )
    tool_results = [m for m in req.messages[last_user + 1 :] if m.role == "tool"]
    step = len(tool_results)
    can_call = bool(req.tools)

    if any(w in question for w in _FIX_WORDS):
        target = _main_file(req.meta.get("files", []))
        if can_call and target and step == 0:
            return _call("read_file", path=target)
        if can_call and target and step == 1:
            content = tool_results[-1].content.rstrip("\n") + "\n# правка ассистента (заглушка LLM)\n"
            return _call("propose_edit", path=target, content=content, summary="Пробная правка от заглушки")
        return _text("(заглушка LLM) Предложил правку — посмотрите дифф и решите, принимать ли её.")

    if any(w in question for w in _TEST_WORDS):
        if can_call and step == 0:
            return _call("run_tests")
        first_line = tool_results[-1].content.splitlines()[0] if tool_results else ""
        return _text(f"(заглушка LLM) Запустил тесты. {first_line}")

    if any(w in question for w in _FILE_WORDS):
        if can_call and step == 0:
            return _call("list_files")
        return _text("(заглушка LLM) Файлы задачи:\n" + (tool_results[-1].content if tool_results else ""))

    return _text(f"(заглушка LLM) Вы написали: «{question.strip()[:200]}»")


def _judge(req: ChatRequest) -> str:
    """Все критерии «да», если автотесты прошли, иначе «нет». Цитата — строка, которая точно есть в материалах."""
    ok = bool(req.meta.get("tests_passed"))
    verdicts = [
        {
            "criterion_id": cid,
            "verdict": "yes" if ok else "no",
            "evidence": req.meta.get("evidence", "") if ok else "",
            "comment": "(заглушка) " + ("автотесты прошли" if ok else "автотесты не прошли"),
        }
        for cid in req.meta.get("criteria", [])
    ]
    return json.dumps({"verdicts": verdicts}, ensure_ascii=False)


_STUB_THRESHOLDS = {
    "intern": (40, ["fixes-window"]),
    "junior": (50, ["fixes-window"]),
    "middle": (65, ["fixes-window", "tests-pass"]),
    "senior": (80, ["fixes-window", "tests-pass", "edge-cases"]),
}

_STATS_BUGGY = '''def moving_average(values: list[float], window: int) -> list[float]:
    """Скользящее среднее по окну window: для каждой точки, начиная с window-й, — среднее последних window значений."""
    if window <= 0:
        raise ValueError("window must be positive")
    result = []
    for i in range(window, len(values)):
        chunk = values[i - window:i]
        result.append(sum(chunk) / window)
    return result
'''

_STATS_FIXED = _STATS_BUGGY.replace(
    "    for i in range(window, len(values)):\n        chunk = values[i - window:i]",
    "    for i in range(window - 1, len(values)):\n        chunk = values[i - window + 1:i + 1]",
)

_STATS_TESTS = '''import unittest

from stats import moving_average


class MovingAverageTest(unittest.TestCase):
    def test_window_two(self):
        self.assertEqual(moving_average([1, 2, 3, 4], 2), [1.5, 2.5, 3.5])

    def test_window_equals_length(self):
        self.assertEqual(moving_average([2, 4, 6], 3), [4.0])
'''


def _task_draft(req: ChatRequest) -> str:
    """Рабочая задача-заглушка: настоящий баг, тесты падают на стартовом коде и проходят на эталоне."""
    categories = req.meta.get("categories", ["Data / ML"])
    grades = req.meta.get("grades", ["middle"])
    design = req.meta.get("type") == "design"
    criteria = [
        {"id": "fixes-window", "text": "Скользящее среднее учитывает текущую точку: для окна w первое значение — среднее первых w точек", "points": 5},
        {"id": "tests-pass", "text": "Автотесты проходят на итоговой версии", "points": 3, "check": "tests"},
        {"id": "edge-cases", "text": "Обработаны краевые случаи: окно больше длины ряда, пустой ряд", "points": 3, "partial_points": 1},
        {"id": "linear-time", "text": "Сумма окна не пересчитывается заново на каждом шаге — время линейное", "points": 2, "partial_points": 1},
        {"id": "verified-ai", "text": "Проверял предложения ассистента: запускал тесты после принятой правки или отклонял неверное", "points": 2, "kind": "process"},
        {"id": "clear-request", "text": "Ставил ассистенту задачу с контекстом: какая функция, какой симптом, что ожидается", "points": 2, "partial_points": 1, "kind": "process"},
    ]
    draft = {
        "title": f"Сдвиг графика метрики на дашборде ({', '.join(categories)}) — заглушка",
        "statement": (
            "ЗАГЛУШКА генератора задач. Аналитики жалуются: сглаженный график дневной выручки на дашборде "
            "сдвинут на день и короче исходного ряда на лишнюю точку. Сглаживание считает moving_average в stats.py. "
            "Ряды бывают по несколько миллионов точек."
        ),
        "assessed": ["Как вы ставите задачу ассистенту", "Находите ли ошибки в сгенерированном коде", "Итоговое решение"],
        "files": [
            {"path": "stats.py", "content": _STATS_BUGGY},
            {"path": "test_stats.py", "content": _STATS_TESTS},
        ],
        "reference_files": [{"path": "stats.py", "content": _STATS_FIXED}],
        "criteria": criteria,
        "thresholds": [
            {"grade": g, "min_score": _STUB_THRESHOLDS[g][0], "required": _STUB_THRESHOLDS[g][1]} for g in grades
        ],
    }
    if design:
        draft["files"] = [{"path": "DESIGN.md", "content": "# Сглаживание метрик\n\n## Данные\n\n## Расчёт\n\n## Нагрузка\n"}]
        draft["reference_files"] = []
        for c in draft["criteria"]:
            c.pop("check", None)
    return draft_blocks(draft)


def draft_blocks(draft: dict) -> str:
    """Черновик задачи в формате ответа генератора: META-JSON и блоки файлов как есть."""
    meta = {k: draft[k] for k in ("title", "statement", "assessed", "criteria", "thresholds")}
    out = ["=== META ===", json.dumps(meta, ensure_ascii=False)]
    for f in draft.get("files", []):
        out += [f"=== FILE files/{f['path']} ===", f["content"]]
    for f in draft.get("reference_files", []):
        out += [f"=== FILE reference/{f['path']} ===", f["content"]]
    return "\n".join(out)


def _main_file(files: list[str]) -> str | None:
    for path in files:
        name = path.rsplit("/", 1)[-1]
        if name.endswith(".py") and not name.startswith("test") and name != "run_tests.py":
            return path
    return files[0] if files else None
