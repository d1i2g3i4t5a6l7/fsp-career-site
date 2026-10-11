"""«Проверка оценок»: человек видит отчёт ИИ и может подтвердить его, исправить вердикты или аннулировать попытку.
Исправил — балл пересчитывается, итог теста и грейд — по исправленным вердиктам; оценка ИИ сохраняется."""

import json

from tests.conftest import FIXED_DEDUP, ScriptedModel, start, text, wait_final

# Судья: баг исправлен, но процесс не засчитан — 11 из 18, это 62 из 100: Middle (порог 65) не взят
PARTLY = json.dumps(
    {
        "verdicts": [
            {"criterion_id": "dedup", "verdict": "yes", "evidence": 'seen.add(event["id"])', "comment": "исправлено"},
            {"criterion_id": "first-counted", "verdict": "yes", "evidence": 'total += event["amount"]', "comment": "учитывается"},
            {"criterion_id": "new-test", "verdict": "partial", "evidence": "def test_three_duplicates", "comment": "такого теста нет"},
            {"criterion_id": "verified-ai", "verdict": "no", "evidence": "", "comment": "не проверял"},
            {"criterion_id": "clear-request", "verdict": "no", "evidence": "", "comment": "не ставил задачу"},
        ]
    },
    ensure_ascii=False,
)


def _submitted(client, candidate_id="c1", level="middle") -> str:
    aid = start(client, candidate_id, level=level)["id"]
    client.put(f"/attempts/{aid}/files", json={"path": "dedup.py", "content": FIXED_DEDUP})
    client.post(f"/attempts/{aid}/submit")
    wait_final(client, aid)
    return aid


def _grade(client, candidate_id="c1"):
    return client.get(f"/candidates/{candidate_id}/grade", params={"category": "backend"}).json()["grade"]


def _review(client, aid, **body):
    return client.post(f"/attempts/{aid}/review", json={"reviewer": "Инженер", "annul": False, **body})


def test_correction_makes_test_passed_and_changes_grade(make_client):
    client = make_client(ScriptedModel(text(PARTLY), text(PARTLY), text(PARTLY)))
    aid = _submitted(client)
    before = client.get(f"/attempts/{aid}/result").json()
    assert (before["ai_score"], before["final"]["passed"], _grade(client)) == (62, False, None)
    new_test = next(c for c in before["criteria"] if c["id"] == "new-test")
    # Судья ставил «частично» во всех прогонах, но его цитаты нет в материалах — критерий снят
    assert (new_test["said"], new_test["unconfirmed"], new_test["verdict"]) == (["partial"] * 3, 3, "no")

    after = _review(client, aid, comment="тесты запускал, видно по журналу", verdicts={"verified-ai": "yes"})
    assert after.status_code == 200, after.text
    after = after.json()
    assert after["ai_score"] == 62  # оценка ИИ сохраняется
    assert after["correction"]["score"] == 73 and after["correction"]["changed"] == ["verified-ai"]
    assert after["final"] == {**after["final"], "score": 73, "passed": True}
    fixed = next(c for c in after["criteria"] if c["id"] == "verified-ai")
    assert (fixed["verdict"], fixed["ai_verdict"], fixed["earned"], fixed["corrected"]) == ("yes", "no", 2, True)
    assert _grade(client) == "middle"  # итог поменялся — поменялся и грейд
    history = client.get("/candidates/c1/attempts").json()
    assert history[0]["final"]["score"] == 73 and history[0]["final"]["passed"] is True


def test_correction_makes_test_failed_and_restores_grade(make_client):
    client = make_client()  # заглушка: тесты прошли → всё «да», Middle пройден
    aid = _submitted(client)
    assert _grade(client) == "middle"
    after = _review(client, aid, verdicts={"dedup": "no"}).json()  # обязательный критерий Middle
    assert after["final"]["passed"] is False and after["correction"]["score"] == 62  # 11 из 18
    assert _grade(client) is None  # прежнего грейда не было


def test_correction_rules(make_client):
    client = make_client()
    aid = _submitted(client)
    assert _review(client, aid, verdicts={"tests-pass": "no"}).status_code == 400  # автотесты не исправляют
    assert _review(client, aid, verdicts={"dedup": "partial"}).status_code == 400  # у критерия нет «частично»
    assert _review(client, aid, verdicts={"nope": "yes"}).status_code == 400
    assert _review(client, aid, verdicts={"dedup": "maybe"}).status_code == 422
    active = start(client, "c2")["id"]
    assert _review(client, active, verdicts={"dedup": "no"}).status_code == 409  # тест ещё идёт


def test_confirm_without_changes(make_client):
    client = make_client()
    aid = _submitted(client)
    assert client.get("/candidates/c1/attempts").json()[0]["reviewed"] is False
    same = _review(client, aid, verdicts={"dedup": "yes"}).json()  # как у ИИ — это подтверждение, не правка
    assert same["correction"] is None and same["review"]["annulled"] is False and _grade(client) == "middle"
    assert client.get("/candidates/c1/attempts").json()[0]["reviewed"] is True  # «Подтверждено экспертом»
    assert _review(client, aid).status_code == 409  # решение принимается один раз


def test_review_queue_order(make_client):
    client = make_client()
    decided = _submitted(client, "c-decided")
    _review(client, decided)
    plain = _submitted(client, "c-plain")
    flagged = start(client, "c-flagged")["id"]
    client.post(f"/attempts/{flagged}/focus", json={"left": True})
    client.post(f"/attempts/{flagged}/submit")
    wait_final(client, flagged)
    start(client, "c-active")  # идёт — в очередь не попадает

    queue = client.get("/reviews").json()
    assert [q["attempt_id"] for q in queue] == [flagged, plain, decided]
    first = queue[0]
    assert (first["needs_review"], first["violations"]["count"], first["task_id"], first["level"]) == (True, 1, "V1-7C2A", "middle")
    assert queue[2]["review"]["reviewer"] == "Инженер" and queue[1]["review"] is None


# --- «Проверял работу ассистента» засчитывает сайт по журналу, без судьи ---


def _verified(client, aid) -> dict:
    client.post(f"/attempts/{aid}/submit")
    result = wait_final(client, aid)
    return next(c for c in result["criteria"] if c["id"] == "verified-ai")


def _accept_assistant_edit(client, aid) -> None:
    edits = client.post(f"/attempts/{aid}/assistant", json={"text": "исправь dedup.py"}).json()["edits"]  # заглушка предлагает правку
    client.post(f"/attempts/{aid}/edits/{edits[0]['id']}/accept")


def test_verified_when_tests_run_after_accepted_edit(make_client):
    client = make_client()
    aid = start(client, "c1")["id"]
    _accept_assistant_edit(client, aid)
    client.post(f"/attempts/{aid}/tests")
    c = _verified(client, aid)
    assert (c["verdict"], c["earned"], c["check"]) == ("yes", 2, "verified")
    assert "Кандидат принял правку" in c["evidence"] and "Тесты запустил кандидат" in c["evidence"]
    assert c["said"] == ["yes"] * 3  # судью об этом пункте не спрашивают — во всех прогонах вердикт сайта


def test_not_verified_when_accepted_edit_never_checked(make_client):
    client = make_client()
    aid = start(client, "c1")["id"]
    _accept_assistant_edit(client, aid)
    c = _verified(client, aid)
    assert (c["verdict"], c["comment"]) == ("no", "Принятые правки ассистента не проверял")


def test_verified_when_assistant_edit_rejected(make_client):
    client = make_client()
    aid = start(client, "c1")["id"]
    edits = client.post(f"/attempts/{aid}/assistant", json={"text": "исправь dedup.py"}).json()["edits"]
    client.post(f"/attempts/{aid}/edits/{edits[0]['id']}/reject", json={"reason": "не то"})
    c = _verified(client, aid)
    assert (c["verdict"], c["comment"]) == ("yes", "Отклонил предложение ассистента")


def test_not_verified_without_assistant_edits(make_client):
    client = make_client()
    aid = start(client, "c1")["id"]
    client.post(f"/attempts/{aid}/tests")  # тесты запускал, но правок ассистента не было — проверять нечего
    c = _verified(client, aid)
    assert (c["verdict"], c["comment"]) == ("no", "Правки ассистента не принимал и не отклонял")
