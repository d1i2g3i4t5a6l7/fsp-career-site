import json
from datetime import datetime

from app.grading import JudgeOutput, JudgeVerdict, aggregate, evaluate_run, evidence_found, grade_of, normalize
from app.llm.types import InvalidResponse
from app.tasks import Rubric
from tests.conftest import FIXED_DEDUP, ScriptedModel, run_sql, start, text, wait_result

RUBRIC = Rubric.model_validate(
    {
        "criteria": [
            {"id": "a", "text": "A", "points": 5},
            {"id": "b", "text": "B", "points": 3, "partial_points": 1},
            {"id": "c", "text": "C", "points": 2, "kind": "process"},
        ],
        "thresholds": [
            {"grade": "junior", "min_score": 50, "required": ["a"]},
            {"grade": "middle", "min_score": 80, "required": ["a", "b"]},
        ],
    }
)
HAYSTACK = normalize("def process(events):\n    seen.add(event['id'])\nRan 2 tests in 0.001s\n[00:10] Кандидат запустил тесты")


def judge(**verdicts) -> JudgeOutput:
    return JudgeOutput(
        verdicts=[JudgeVerdict(criterion_id=cid, verdict=v, evidence=e) for cid, (v, e) in verdicts.items()]
    )


def test_evidence_must_be_verbatim():
    assert evidence_found("seen.add(event['id'])", HAYSTACK)
    assert evidence_found("  SEEN.add(event['id'])\n", HAYSTACK)  # регистр и пробелы не важны
    assert evidence_found("def process(events): ... Ran 2 tests", HAYSTACK)  # фрагменты через многоточие
    assert not evidence_found("seen.add(event.id)", HAYSTACK)  # пересказ не считается
    assert not evidence_found("Ran", HAYSTACK)  # слишком коротко, чтобы что-то доказывать
    assert not evidence_found("", HAYSTACK)


LIVE_LOG = normalize(
    "[00:01] Кандидат → ассистенту: Пользователи жалуются, что платёж иногда зачисляется дважды. "
    "Посмотри dedup.py, найди причину и предложи исправление.\n"
    "[00:10] Тесты запустил кандидат: не прошли\n"
    "[00:12] Кандидат → ассистенту: Добавь тест на случай, когда одно событие приходит три раза подряд среди других событий.\n"
    "[00:20] Кандидат принял правку #1 в test_dedup.py\n"
    "    def test_triplicate_counted_once(self):\n        self.assertEqual(\n"
)


def test_evidence_from_live_gigachat_runs():
    """Цитаты, которые GigaChat реально давал судьёй: настоящие — засчитываются, пересказ — нет."""
    # настоящая цитата в обёртке из слов судьи и с другими кавычками
    assert evidence_found(
        "Запрос кандидата: «Посмотри dedup.py, найди причину и предложи исправление.» Затем уточнение про тест", LIVE_LOG
    )
    # несколько строк журнала, склеенных переносами, — без меток времени
    assert evidence_found(
        "Тесты запустил кандидат: не прошли\nКандидат → ассистенту: Добавь тест на случай, когда одно событие приходит три раза",
        LIVE_LOG,
    )
    assert evidence_found("def test_triplicate_counted_once(...): self.assertEqual(..., 150)", LIVE_LOG + " 150)")
    # пересказ своими словами — не цитата
    assert not evidence_found(
        "Кандидат запускал тесты после предложенной правки ассистента и отклонил неверное поведение", LIVE_LOG
    )
    assert not evidence_found("Ассистент добавил тест test_triplicate_counted_one с тремя повторами", LIVE_LOG)


def test_run_counts_only_supported_verdicts():
    run = evaluate_run(
        RUBRIC,
        judge(
            a=("yes", "seen.add(event['id'])"),
            b=("partial", "выдуманная цитата из головы"),  # цитаты нет в материалах
            c=("partial", "Кандидат запустил тесты"),  # «частично» для c не разрешено
        ),
        HAYSTACK,
    )
    assert {cid: v["counted"] for cid, v in run["verdicts"].items()} == {"a": "yes", "b": "no", "c": "no"}
    assert run["verdicts"]["b"]["evidence_found"] is False
    assert (run["score"], run["grade"]) == (5, "junior")


def test_tests_criterion_is_decided_by_test_run_not_by_judge():
    """На живом GigaChat один прогон судьи «не увидел» прошедшие тесты и уронил грейд — теперь это решают сами тесты."""
    from app.grading import auto_verdicts
    from app.sandbox import RunResult

    rubric = Rubric.model_validate(
        {
            "criteria": [
                {"id": "a", "text": "A", "points": 5},
                {"id": "tests", "text": "Автотесты проходят", "points": 5, "check": "tests"},
            ],
            "thresholds": [{"grade": "middle", "min_score": 100, "required": ["a", "tests"]}],
        }
    )
    passed = RunResult(0, "", "Ran 3 tests in 0.001s\n\nOK", 10)
    judge_says_no = judge(a=("yes", "seen.add(event['id'])"), tests=("no", ""))
    run = evaluate_run(rubric, judge_says_no, HAYSTACK, auto_verdicts(rubric, passed))
    assert run["verdicts"]["tests"]["counted"] == "yes" and run["verdicts"]["tests"]["evidence"] == "OK"
    assert run["grade"] == "middle"
    failed = RunResult(1, "", "FAILED (failures=1)", 10)
    run = evaluate_run(rubric, judge(a=("yes", "seen.add(event['id'])"), tests=("yes", "OK")), HAYSTACK, auto_verdicts(rubric, failed))
    assert run["verdicts"]["tests"]["counted"] == "no" and run["grade"] is None


def test_missing_verdict_is_no():
    run = evaluate_run(RUBRIC, judge(a=("yes", "seen.add(event['id'])")), HAYSTACK)
    assert run["verdicts"]["b"]["counted"] == "no" and run["verdicts"]["b"]["comment"] == "Судья не дал вердикт"


def test_grade_needs_points_and_required_criteria():
    assert grade_of(RUBRIC, {"a": "yes", "b": "yes", "c": "no"}, 80) == "middle"
    assert grade_of(RUBRIC, {"a": "yes", "b": "partial", "c": "yes"}, 80) == "junior"  # b обязателен для middle
    assert grade_of(RUBRIC, {"a": "no", "b": "yes", "c": "yes"}, 50) is None


def test_majority_per_criterion_and_lower_grade_when_runs_disagree():
    good = judge(a=("yes", "seen.add(event['id'])"), b=("yes", "Ran 2 tests in"), c=("yes", "Кандидат запустил тесты"))
    weak = judge(a=("yes", "seen.add(event['id'])"), b=("no", ""), c=("yes", "Кандидат запустил тесты"))
    runs = [evaluate_run(RUBRIC, o, HAYSTACK) for o in (good, good, weak)]
    result = aggregate(RUBRIC, runs, "middle")
    by_id = {c["id"]: c for c in result["criteria"]}
    assert by_id["b"]["verdict"] == "yes" and by_id["b"]["runs"] == ["yes", "yes", "no"]
    assert result["score"] == 10 and result["max_score"] == 10
    # по большинству вышел бы middle, но один прогон дал junior — засчитан нижний
    assert result["unstable"] is True and result["grade"] == "junior"
    assert result["level_confirmed"] is False
    assert [t["reached"] for t in result["thresholds"]] == [True, True]


def _wait_result(client, aid) -> dict:
    return wait_result(client, aid)


def _judge_json(verdicts: dict[str, tuple[str, str]]) -> str:
    return json.dumps(
        {"verdicts": [{"criterion_id": k, "verdict": v, "evidence": e, "comment": f"про {k}"} for k, (v, e) in verdicts.items()]},
        ensure_ascii=False,
    )


def test_submit_triggers_grading_with_rubric_of_the_task(make_client):
    verdict = _judge_json(
        {
            "dedup": ("yes", 'seen.add(event["id"])'),
            "first-counted": ("yes", 'total += event["amount"]'),
            "tests-pass": ("yes", "Ran 2 tests"),
            "new-test": ("partial", "def test_three_duplicates"),  # такого теста нет — не засчитается
            "verified-ai": ("no", ""),
            "clear-request": ("no", ""),
        }
    )
    model = ScriptedModel(text(verdict), text(verdict), text(verdict))
    client = make_client(model)
    aid = start(client)["id"]
    assert client.get(f"/attempts/{aid}/result").json()["status"] == "not_submitted"

    client.put(f"/attempts/{aid}/files", json={"path": "dedup.py", "content": FIXED_DEDUP})
    client.post(f"/attempts/{aid}/submit")
    result = _wait_result(client, aid)

    assert result["status"] == "done", result
    assert result["tests"]["passed"] is True
    assert (result["score"], result["max_score"], result["grade"]) == (11, 18, "junior")
    assert result["level_confirmed"] is False and result["unstable"] is False
    by_id = {c["id"]: c for c in result["criteria"]}
    assert by_id["dedup"]["earned"] == 5 and by_id["dedup"]["evidence"] == 'seen.add(event["id"])'
    assert by_id["new-test"]["verdict"] == "no" and by_id["new-test"]["evidence"] == ""
    assert [t["reached"] for t in result["thresholds"]] == [True, True, False, False]  # intern, junior, middle, senior

    # судья видел рубрику, итоговые файлы и журнал, а работал с приоритетом проверки
    judge_request = model.requests[0]
    assert judge_request.scenario == "grader"
    material = judge_request.messages[1].content
    assert "dedup [решение] Событие с уже обработанным id" in material
    assert "tests-pass" not in material.split("</критерии>")[0]  # автоматический критерий судье не отдаём
    assert "seen.add" in material and "Кандидат вручную изменил dedup.py" in material
    state = client.get(f"/attempts/{aid}").json()
    assert state["grading_status"] == "done"
    assert "grading.completed" in [e["type"] for e in client.get(f"/attempts/{aid}/events").json()]


def test_time_out_closes_attempt_and_grades_automatically(make_client, settings):
    settings.grading_poll_s = 0.05
    client = make_client()  # заглушка: судья ставит «да», если тесты прошли
    aid = start(client)["id"]
    client.put(f"/attempts/{aid}/files", json={"path": "dedup.py", "content": FIXED_DEDUP})
    run_sql(settings, "UPDATE attempts SET deadline_at = :at WHERE id = :id", at=datetime(2000, 1, 1), id=aid)

    result = _wait_result(client, aid)
    assert client.get(f"/attempts/{aid}").json()["status"] == "expired"
    assert result["status"] == "done"
    # 16 из 18: «проверял работу ассистента» не засчитан — правок ассистента не было, сайт видит это по журналу
    assert (result["score"], result["grade"], result["level_confirmed"]) == (16, "senior", True)


def test_tests_criterion_uses_original_tests_not_candidates_edits(make_client):
    """Кандидат «починил» тест вместо кода — автоматический критерий это не засчитывает."""
    client = make_client()
    aid = start(client)["id"]
    tampered = (
        "import unittest\n\nfrom dedup import process\n\n\nclass ProcessTest(unittest.TestCase):\n"
        "    def test_duplicate_counted_once(self):\n        self.assertEqual(1, 1)\n"
    )
    client.put(f"/attempts/{aid}/files", json={"path": "test_dedup.py", "content": tampered})
    assert client.post(f"/attempts/{aid}/tests").json()["passed"] is True  # в сессии — его версия тестов
    client.post(f"/attempts/{aid}/submit")
    result = _wait_result(client, aid)
    assert result["tests"]["passed"] is False
    assert next(c for c in result["criteria"] if c["id"] == "tests-pass")["verdict"] == "no"


def test_judge_failure_is_reported_and_can_be_retried(make_client):
    class BrokenJudge(ScriptedModel):
        async def chat(self, req, on_delta=None):
            if req.scenario == "grader" and self.broken:
                raise InvalidResponse("модель недоступна")
            return await super().chat(req, on_delta)

    model = BrokenJudge()
    model.broken = True
    client = make_client(model)
    aid = start(client)["id"]
    client.post(f"/attempts/{aid}/submit")
    failed = _wait_result(client, aid)
    assert failed["status"] == "failed" and "Ни один прогон судьи не удался" in failed["error"]

    model.broken = False
    model.steps = [text(_judge_json({"dedup": ("no", "")}))] * 3
    assert client.post(f"/attempts/{aid}/grade").status_code == 202
    result = _wait_result(client, aid)
    assert result["status"] == "done" and result["grade"] is None and result["score"] == 0


def test_cannot_grade_active_attempt(make_client):
    client = make_client()
    aid = start(client)["id"]
    assert client.post(f"/attempts/{aid}/grade").status_code == 409


def test_random_task_by_category_and_level(make_client):
    client = make_client()
    resp = client.post("/attempts", json={"candidate_id": "c1", "category": "backend", "level": "middle"})
    assert resp.status_code == 201 and resp.json()["task"]["id"] in ("V1-7C2A", "V1-4E9B")  # обе — Backend · Middle
    assert client.post("/attempts", json={"candidate_id": "c2", "category": "frontend", "level": "middle"}).status_code == 404
    assert client.post("/attempts", json={"candidate_id": "c1"}).status_code == 422
    assert client.post("/attempts", json={"candidate_id": "c1", "category": "backend", "level": "lead"}).status_code == 422
