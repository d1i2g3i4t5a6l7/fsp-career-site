"""Генерация задач: черновик модели → проверки → исправление → банк."""

import json

import pytest

from app.generation import GenerationRequest, TaskDraft, build_task, check_tests, parse_draft
from app.llm.providers.stub import draft_blocks
from app.sandbox import LocalRunner
from tests.conftest import ScriptedModel, start, text

GOOD = {
    "title": "Сдвиг графика метрики",
    "statement": "Аналитики жалуются, что сглаженный график сдвинут на день. Ряды — миллионы точек.",
    "assessed": ["Как вы ставите задачу ассистенту", "Итоговое решение"],
    "files": [
        {"path": "stats.py", "content": "def avg(xs):\n    return sum(xs) / (len(xs) + 1)\n"},
        {
            "path": "test_stats.py",
            "content": "import unittest\nfrom stats import avg\n\n\nclass T(unittest.TestCase):\n    def test_avg(self):\n        self.assertEqual(avg([2, 4]), 3)\n",
        },
    ],
    "reference_files": [{"path": "stats.py", "content": "def avg(xs):\n    return sum(xs) / len(xs)\n"}],
    "criteria": [
        {"id": "correct-mean", "text": "Среднее считается по числу точек", "points": 5},
        {"id": "tests-pass", "text": "Автотесты проходят", "points": 3},
        {"id": "empty-series", "text": "Пустой ряд обработан", "points": 2, "partial_points": 1},
        {"id": "verified-ai", "text": "Проверял правки ассистента тестами", "points": 2, "kind": "process"},
    ],
    "thresholds": [
        {"grade": "middle", "min_score": 60, "required": ["correct-mean"]},
        {"grade": "senior", "min_score": 80, "required": ["correct-mean", "empty-series"]},
    ],
}


def _draft_dict(**changes) -> dict:
    return {**GOOD, **changes}


def _draft(**changes) -> str:
    return draft_blocks(_draft_dict(**changes))


def _generate(client, **body) -> dict:
    resp = client.post("/tasks/generate", json={"categories": ["Data / ML"], "grades": ["senior", "middle"], **body})
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["id"]
    import time

    for _ in range(200):
        job = client.get(f"/tasks/generations/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError(job)


def test_generated_task_lands_in_bank_and_can_be_taken(make_client):
    model = ScriptedModel(text(_draft()))
    client = make_client(model)
    job = _generate(client, type="bug", brief="Команда аналитики выручки")
    assert job["status"] == "done", job
    assert job["report"][0]["problems"] == []
    assert job["report"][0]["tests"]["start"]["passed"] is False
    assert job["report"][0]["tests"]["reference"]["passed"] is True

    task = client.get(f"/tasks/{job['task_id']}").json()
    assert task["id"].startswith("V1-")
    assert (task["categories"], task["grades"], task["type"]) == (["Data / ML"], ["middle", "senior"], "bug")
    assert task["time_limit_min"] == 30  # тест на грейд — 30 минут
    assert "run_tests.py" in task["files"]  # файл запуска тестов кладёт платформа
    assert [t["min_score"] for t in task["rubric"]["thresholds"]] == [60, 80]

    # модель получила категории, грейды, тип и тему
    request = model.requests[0]
    assert request.scenario == "task_gen" and request.max_tokens
    assert "Категории: Data / ML" in request.messages[1].content
    assert "Грейды: middle, senior" in request.messages[1].content
    assert "Команда аналитики выручки" in request.messages[1].content

    # сгенерированная задача сначала ждёт эксперта и кандидатам не выдаётся
    assert task["status"] == "review"
    assert [t["id"] for t in client.get("/tasks", params={"status": "review"}).json()] == [task["id"]]
    take = {"candidate_id": "ds-1", "category": "Data / ML", "level": "senior"}
    assert client.post("/attempts", json=take).status_code == 404
    # эксперт может прорешать её сам, открыв по id
    trial = client.post("/attempts", json={"candidate_id": "expert-1", "task_id": task["id"], "level": "middle"})
    assert trial.status_code == 201

    # эксперт одобрил — задача выдаётся на тест по категории и грейду
    reviewed = client.post(f"/tasks/{task['id']}/review", json={"expert": "Северный код", "approved": True}).json()
    assert reviewed["status"] == "published" and reviewed["review"]["expert"] == "Северный код"
    assert [t["id"] for t in client.get("/tasks", params={"category": "data", "grade": "senior"}).json()] == [task["id"]]
    attempt = client.post("/attempts", json=take).json()
    assert (attempt["task"]["id"], attempt["category"], attempt["level"]) == (task["id"], "Data / ML", "senior")
    assert "reference_files" not in attempt["task"] and "rubric" not in attempt["task"]

    # отклонённую задачу не открыть даже по id
    client.post(f"/tasks/{task['id']}/review", json={"expert": "Северный код", "approved": False, "comment": "не решается за 60 минут"})
    assert client.post("/attempts", json={"candidate_id": "ds-2", "task_id": task["id"], "level": "middle"}).status_code == 409


def test_model_fixes_draft_after_failed_checks(make_client):
    broken = _draft(
        reference_files=[{"path": "stats.py", "content": "def avg(xs):\n    return 0\n"}],  # эталон не проходит тесты
        thresholds=[{"grade": "middle", "min_score": 60, "required": []}],  # нет порога для senior
    )
    model = ScriptedModel(text(broken), text(_draft()))
    client = make_client(model)
    job = _generate(client, type="bug")
    assert job["status"] == "done"
    first, second = job["report"]
    assert any("пороги должны быть ровно на грейды" in p for p in first["problems"])
    assert second["problems"] == []
    # во втором запросе модели показали, что не так
    assert "не прошёл проверки" in model.requests[1].messages[-1].content


def test_generation_fails_after_all_fix_attempts(make_client):
    passes_on_start = _draft(files=[GOOD["files"][0] | {"content": "def avg(xs):\n    return sum(xs) / len(xs)\n"}, GOOD["files"][1]])
    model = ScriptedModel(*(text(passes_on_start) for _ in range(4)))
    client = make_client(model)
    job = _generate(client, type="bug")
    assert job["status"] == "failed" and len(job["report"]) == 4  # первая попытка и 3 исправления
    assert any("Тесты проходят на стартовом коде" in p for p in job["report"][0]["problems"])
    assert job["draft"]["title"] == GOOD["title"]
    assert client.get("/tasks", params={"category": "Data / ML"}).json() == []


def test_stub_generates_working_task(make_client):
    client = make_client()  # заглушка: настоящий баг, тесты и эталон
    job = _generate(client, type="bug")
    assert job["status"] == "done", job["report"]


def test_build_task_checks():
    req = GenerationRequest(categories=[" Backend ", "backend"], grades=["middle"])
    assert req.categories == ["Backend"]  # направления — как на сайте, по id или названию
    draft = TaskDraft.model_validate(_draft_dict(reference_files=[], thresholds=[GOOD["thresholds"][0]]))
    task, problems, _ = build_task(draft, req, "bug", 45, "V1-TEST")
    assert "Нужно эталонное решение в reference_files" in problems
    touching_tests = TaskDraft.model_validate(_draft_dict(reference_files=GOOD["files"], thresholds=[GOOD["thresholds"][0]]))
    _, problems, _ = build_task(touching_tests, req, "bug", 45, "V1-TEST")
    assert any("Эталон не должен менять тесты" in p for p in problems)


async def test_tests_in_subfolder_are_found():
    """GigaChat кладёт тесты в tests/ без __init__.py — unittest их не видит, и годный черновик бракуется."""
    req = GenerationRequest(categories=["Data / ML"], grades=["middle"])
    in_folder = [GOOD["files"][0], {**GOOD["files"][1], "path": "tests/unit/test_stats.py"}]
    draft = TaskDraft.model_validate(_draft_dict(files=in_folder, thresholds=[GOOD["thresholds"][0]]))
    task, problems, fixes = build_task(draft, req, "bug", 45, "V1-TEST")
    assert problems == []
    assert task.files["tests/__init__.py"] == task.files["tests/unit/__init__.py"] == ""
    assert len([f for f in fixes if "__init__.py" in f]) == 2
    problems, report = await check_tests(task, LocalRunner())
    assert problems == [] and report["start"]["passed"] is False and report["reference"]["passed"] is True
    # без единого теста прогон не «OK», а провал
    no_tests = await LocalRunner().run({k: v for k, v in task.files.items() if "test_" not in k}, task.run)
    assert not no_tests.passed and "Не найдено ни одного теста" in no_tests.stderr


def test_hint_comments_are_stripped_and_extra_auto_criteria_demoted():
    req = GenerationRequest(categories=["Data / ML"], grades=["middle", "senior"])
    hinted = [
        {
            "path": "stats.py",
            "content": (
                "def avg(xs):\n"
                "    # BUG: деление всегда, даже при пустом ряде\n"
                "    return sum(xs) / (len(xs) + 1)  # тут ошибка\n"
            ),
        },
        GOOD["files"][1],
    ]
    criteria = GOOD["criteria"] + [{"id": "extra-auto", "text": "Ещё тесты", "points": 1, "check": "tests"}]
    criteria[1] = {**criteria[1], "check": "tests"}
    task, problems, fixes = build_task(
        TaskDraft.model_validate(_draft_dict(files=hinted, criteria=criteria)), req, "bug", 60, "V1-TEST"
    )
    assert problems == []
    code = task.files["stats.py"]
    assert "BUG" not in code and "ошибка" not in code
    assert code == "def avg(xs):\n    return sum(xs) / (len(xs) + 1)\n"  # код на месте, срезаны только комментарии
    assert len([f for f in fixes if "комментарий-подсказка" in f]) == 2
    assert [c.check for c in task.rubric.criteria if c.id in ("tests-pass", "extra-auto")] == ["tests", "judge"]


def test_request_validation(make_client):
    client = make_client()
    bad = [
        {"categories": [], "grades": ["middle"]},
        {"categories": ["Backend"], "grades": []},
        {"categories": ["Backend"], "grades": ["middle", "middle"]},
        {"categories": ["Backend"], "grades": ["junior"], "type": "design"},
        {"categories": ["Backend"], "grades": ["intern"], "type": "design"},
        {"categories": ["Backend"], "grades": ["lead"]},
        {"categories": ["ML"], "grades": ["middle"]},  # такого направления на сайте нет
    ]
    for body in bad:
        assert client.post("/tasks/generate", json=body).status_code == 422, body


def test_task_with_several_grades_needs_level_to_start(make_client):
    client = make_client()
    resp = client.post("/attempts", json={"task_id": "V1-7C2A", "candidate_id": "c"})
    assert resp.status_code == 400 and "укажите category и level" in resp.json()["detail"]
    ok = start(client, "c", level="senior")
    assert (ok["category"], ok["level"]) == ("Backend", "senior")


def test_parse_draft_blocks():
    meta = json.dumps({k: GOOD[k] for k in ("title", "statement", "assessed", "criteria", "thresholds")}, ensure_ascii=False)
    code = r"""print('кавычки " и \ без экранирования')"""
    raw = "\n".join(
        [
            "Вот задача:",
            "=== META ===",
            "```json",
            meta,
            "```",
            "=== FILE files/stats.py ===",
            "```python",
            code,
            "```",
            "=== FILE reference/stats.py ===",
            "print(1)",
            "=== FILE test_stats.py ===",  # без префикса files/ — так живой GigaChat тоже пишет
            "import unittest",
        ]
    )
    draft = parse_draft(raw)
    assert [f.path for f in draft.files] == ["stats.py", "test_stats.py"]
    assert draft.reference_files[0].content == "print(1)\n"
    assert draft.files[0].content == code + "\n"  # код как есть, обёртка ``` снята
    assert [f.path for f in draft.reference_files] == ["stats.py"]
    with pytest.raises(ValueError, match="нет блоков"):
        parse_draft('{"title": "json как раньше"}')
    with pytest.raises(ValueError, match="нет блока === META ==="):
        parse_draft("=== FILE files/a.py ===\nprint(1)")
    with pytest.raises(ValueError, match="META или файлы не по схеме"):
        parse_draft('=== META ===\n{"title": "x"}\n=== FILE files/a.py ===\nprint(1)')


def test_broken_answer_is_an_attempt_not_a_crash(make_client):
    """Живой GigaChat присылал битый JSON — теперь это неудачная попытка с понятной ошибкой, а не падение генерации."""
    model = ScriptedModel(text('{"title": "битый json", "files": [}'), text(_draft()))
    client = make_client(model)
    job = _generate(client, type="bug")
    assert job["status"] == "done"
    assert job["report"][0]["problems"][0].startswith("Ответ не в нужном формате")
