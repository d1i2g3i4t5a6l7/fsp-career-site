"""Итог теста — оценка LLM после постобработки — и смена грейда по правилам экрана «Грейд и тесты»."""

from datetime import datetime, timedelta

from tests.conftest import FIXED_DEDUP, run_sql, start, wait_final


def _solve_and_submit(client, candidate_id="cand-1", fixed=True) -> str:
    aid = start(client, candidate_id)["id"]
    if fixed:
        client.put(f"/attempts/{aid}/files", json={"path": "dedup.py", "content": FIXED_DEDUP})
    client.post(f"/attempts/{aid}/submit")
    return aid


def _status(client, candidate_id="cand-1") -> dict:
    return client.get(f"/candidates/{candidate_id}/grade", params={"category": "backend"}).json()


def _tests(client, candidate_id="cand-1") -> dict[str, dict]:
    return {t["level"]: t for t in _status(client, candidate_id)["tests"]}


def test_passed_test_changes_grade_right_after_grading(make_client):
    client = make_client()  # заглушка: тесты прошли → судья ставит всё «да»
    aid = _solve_and_submit(client)
    result = wait_final(client, aid)
    # 16 из 18 → 89: «проверял работу ассистента» сайт не засчитал — правок ассистента не было
    assert result["ai_score"] == 89 and result["level_confirmed"] is True
    assert result["final"]["score"] == 89 and result["final"]["passed"] is True

    # «BACKEND · MIDDLE · Тест 89/100», следующая смена — через 3 месяца
    status = _status(client)
    assert (status["grade"], status["score"]) == ("middle", 89)
    assert status["change_available"] is False
    next_change = datetime.fromisoformat(status["next_change_at"].rstrip("Z"))
    confirmed = datetime.fromisoformat(status["confirmed_at"].rstrip("Z"))
    assert timedelta(days=89) < next_change - confirmed <= timedelta(days=90)
    tests = {t["level"]: t for t in status["tests"]}
    assert tests["middle"]["reason"] == "Это ваш текущий грейд"
    assert tests["senior"]["reason"] == "Грейд можно менять раз в 3 месяца"
    assert tests["senior"]["available_from"] == status["next_change_at"]
    assert client.post("/attempts", json={"candidate_id": "cand-1", "category": "Backend", "level": "senior"}).status_code == 409

    # история: «Тест на Middle «…» — 89/100»
    [item] = client.get("/candidates/cand-1/attempts").json()
    assert (item["level"], item["task_title"], item["ai_score"]) == ("middle", "Дедупликация платёжных событий", 89)
    assert item["final"]["passed"] is True
    events = [e["type"] for e in client.get(f"/attempts/{aid}/events").json()]
    assert "result.final" in events and "grade.changed" in events


def test_failed_test_keeps_grade_and_opens_lower_level_at_once(make_client):
    client = make_client()
    aid = _solve_and_submit(client, fixed=False)  # баг не исправлен — тесты падают, судья ставит «нет»
    result = wait_final(client, aid)
    assert result["ai_score"] == 0 and result["final"]["passed"] is False

    status = _status(client)
    assert status["grade"] is None  # принудительного понижения нет, грейд не трогаем
    tests = {t["level"]: t for t in status["tests"]}
    assert tests["junior"]["available"]  # уровень ниже — сразу
    assert tests["middle"]["available"] is False
    assert tests["middle"]["reason"].startswith("Тест на этот уровень можно повторить через 30 дней")
    retry_at = datetime.fromisoformat(tests["middle"]["available_from"].rstrip("Z"))
    assert timedelta(days=29) < retry_at - datetime.utcnow() <= timedelta(days=30)


def test_level_waits_while_previous_attempt_is_graded(make_client):
    client = make_client()
    aid = start(client)["id"]
    second = client.post("/attempts", json={"candidate_id": "cand-1", "category": "Backend", "level": "senior"})
    assert second.status_code == 409 and "завершите текущий тест" in second.json()["detail"]
    client.post(f"/attempts/{aid}/submit")
    wait_final(client, aid)
    assert _tests(client)["junior"]["available"]


def test_grade_change_opens_after_cooldown(make_client, settings):
    client = make_client()
    aid = _solve_and_submit(client)
    wait_final(client, aid)
    assert _tests(client)["senior"]["available"] is False
    run_sql(settings, "UPDATE grade_records SET next_change_at = :at", at=datetime(2000, 1, 1))
    assert _tests(client)["senior"]["available"] is True
