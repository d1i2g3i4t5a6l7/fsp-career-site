"""Уход со вкладки: попытка помечается, решает человек; аннулировал — грейд снят, тесты заморожены на 30 дней.
Плюс грейд «Стажёр», направления как на сайте и балл с округлением вверх."""

from datetime import datetime, timedelta

from app.grading import to_100
from tests.conftest import FIXED_DEDUP, run_sql, start, wait_final


def _solve(client, aid: str, *, leave: bool = False) -> dict:
    client.put(f"/attempts/{aid}/files", json={"path": "dedup.py", "content": FIXED_DEDUP})
    if leave:
        client.post(f"/attempts/{aid}/focus", json={"left": True})
        client.post(f"/attempts/{aid}/focus", json={"left": False})
    client.post(f"/attempts/{aid}/submit")
    return wait_final(client, aid)


def _status(client, candidate_id: str) -> dict:
    return client.get(f"/candidates/{candidate_id}/grade", params={"category": "backend"}).json()


def test_focus_events_are_counted_once_per_leave(make_client):
    client = make_client()
    aid = start(client, "c1")["id"]
    post = lambda left: client.post(f"/attempts/{aid}/focus", json={"left": left}).json()["recorded"]
    assert post(False) is False  # «вернулся», не уходя, — не событие
    assert post(True) is True
    assert post(True) is False  # повтор того же состояния не задваивает уход
    assert post(False) is True
    assert post(True) is True
    assert client.get(f"/attempts/{aid}").json()["stats"]["tab_leaves"] == 2
    client.post(f"/attempts/{aid}/submit")
    assert client.post(f"/attempts/{aid}/focus", json={"left": True}).status_code == 409  # тест закончен


def test_leaving_tab_marks_attempt_and_annulment_removes_grade_and_freezes(make_client):
    client = make_client()  # заглушка: тесты прошли → всё «да»
    aid = start(client, "c1")["id"]
    result = _solve(client, aid, leave=True)
    # ИИ выносит вердикт как обычно, но попытка помечена: решает человек
    assert result["final"]["passed"] is True and _status(client, "c1")["grade"] == "middle"
    assert result["violations"]["count"] == 1 and result["needs_review"] is True and result["review"] is None

    decided = client.post(f"/attempts/{aid}/review", json={"reviewer": "Эксперт", "annul": True, "comment": "уходил со вкладки"})
    assert decided.status_code == 200, decided.text
    assert decided.json()["review"]["annulled"] is True and decided.json()["needs_review"] is False

    status = _status(client, "c1")
    assert status["grade"] is None  # грейд держался на аннулированной попытке, прежнего не было
    frozen = datetime.fromisoformat(status["frozen_until"].rstrip("Z"))
    assert timedelta(days=29) < frozen - datetime.utcnow() <= timedelta(days=30)
    assert all(not t["available"] and t["reason"] == "Тесты заморожены: попытка аннулирована" for t in status["tests"])
    blocked = client.post("/attempts", json={"candidate_id": "c1", "category": "Backend", "level": "junior"})
    assert blocked.status_code == 409 and "заморожены" in blocked.json()["detail"]

    history = client.get("/candidates/c1/attempts").json()
    assert (history[0]["annulled"], history[0]["tab_leaves"]) == (True, 1)
    again = client.post(f"/attempts/{aid}/review", json={"reviewer": "Эксперт", "annul": False})
    assert again.status_code == 409  # решение принимается один раз


def test_annulment_restores_previous_grade(make_client, settings):
    client = make_client()
    first = start(client, "c1", level="junior")["id"]
    _solve(client, first)
    assert _status(client, "c1")["grade"] == "junior"
    run_sql(settings, "UPDATE grade_records SET next_change_at = :at", at=datetime(2000, 1, 1))

    second = start(client, "c1", level="middle")["id"]
    _solve(client, second, leave=True)
    assert _status(client, "c1")["grade"] == "middle"

    client.post(f"/attempts/{second}/review", json={"reviewer": "Эксперт", "annul": True})
    status = _status(client, "c1")
    assert (status["grade"], status["score"]) == ("junior", 89)  # вернулся прежний подтверждённый грейд


def test_human_can_keep_marked_attempt(make_client):
    client = make_client()
    aid = start(client, "c1")["id"]
    _solve(client, aid, leave=True)
    kept = client.post(f"/attempts/{aid}/review", json={"reviewer": "Эксперт", "annul": False, "comment": "отходил на минуту"}).json()
    assert kept["review"]["annulled"] is False and kept["needs_review"] is False
    status = _status(client, "c1")
    assert status["grade"] == "middle" and status["frozen_until"] is None


def test_active_attempt_cannot_be_reviewed(make_client):
    client = make_client()
    aid = start(client, "c1")["id"]
    assert client.post(f"/attempts/{aid}/review", json={"reviewer": "Эксперт", "annul": True}).status_code == 409


def test_intern_grade_and_site_specializations(make_client):
    client = make_client()
    tests = {t["level"] for t in _status(client, "c1")["tests"]}
    assert tests == {"intern", "junior", "middle", "senior"}
    # Направление — по id с сайта («backend») или по названию; в попытке — название, как на сайте
    attempt = client.post("/attempts", json={"candidate_id": "c1", "category": "backend", "level": "intern"})
    assert attempt.status_code == 201, attempt.text
    assert (attempt.json()["category"], attempt.json()["level"]) == ("Backend", "intern")
    assert client.post("/attempts", json={"candidate_id": "c2", "category": "ML", "level": "middle"}).status_code == 422
    assert client.get("/candidates/c2/grade", params={"category": "data"}).json()["category"] == "Data / ML"
    assert client.get("/candidates/c2/grade", params={"category": "ML"}).status_code == 400


def test_score_rounds_up():
    assert [to_100(15, 18), to_100(11, 18), to_100(7, 10), to_100(0, 18), to_100(18, 18)] == [84, 62, 70, 0, 100]
