"""AI reading of different wording: guarded, labelled, and never required."""
import copy

from sqlalchemy import select

from app.adapters import llm
from app.db.base import session_factory
from app.db.models import Complaint, Overlap, User
from app.services import issue_judge


def _c(title, desc=""):
    return Complaint(title=title, description=desc)


def test_valid_answer_is_accepted_and_labelled(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: 'Sure: {"same_issue": true, "confidence": 0.9, "reason": "Both are about unreturned admission money."}')
    r = issue_judge.judge(_c("Ghost fees kept"), _c("Deposit not repaid"))
    assert r["same_issue"] is True and r["kind"] == "AI-written" and "admission money" in r["reason"]


def test_low_confidence_is_not_a_match(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: '{"same_issue": true, "confidence": 0.4, "reason": "maybe"}')
    assert issue_judge.judge(_c("a"), _c("b"))["same_issue"] is False


def test_garbage_or_missing_answer_gives_none(monkeypatch):
    for bad in ("not json", '{"same_issue": "yes", "confidence": 2, "reason": "x"}', '{"confidence": 0.9}', None):
        monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400, bad=bad: bad)
        assert issue_judge.judge(_c("a"), _c("b")) is None


def test_accusing_reason_is_not_shown(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: '{"same_issue": true, "confidence": 0.9, "reason": "This is fraud, see SMV-2026-000001"}')
    r = issue_judge.judge(_c("a"), _c("b"))
    assert "fraud" not in r["reason"] and "SMV" not in r["reason"]


def test_only_titles_and_descriptions_are_sent(monkeypatch):
    seen = {}

    def fake(s, u, max_tokens=400):
        seen["u"] = u

    monkeypatch.setattr(llm, "complete", fake)
    c = _c("Refund pending", "money not returned")
    c.complainant_name_enc = "SECRET-NAME"
    issue_judge.judge(c, _c("x"))
    assert "SECRET-NAME" not in seen["u"] and seen["u"].count("<complaint>") == 2


def test_needs_a_key_and_rescan_adds_labelled_ai_reading(client, tokens, monkeypatch):
    h = tokens["admin"]
    monkeypatch.setattr(llm, "available", lambda: False)
    assert client.post("/api/v1/admin/jobs/ai-rescan", headers=h).status_code == 409
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: '{"same_issue": true, "confidence": 0.95, "reason": "Same underlying complaint."}')
    with session_factory()() as db:
        o = db.scalars(select(Overlap).where(Overlap.status == "SUGGESTED", Overlap.overlap_type == "O1")).first() \
            or db.scalars(select(Overlap).where(Overlap.status == "SUGGESTED")).first()
        r = copy.deepcopy(o.receipt_json)
        r["layers"]["L3_issue"]["concepts"]["shared_concepts"] = []   # as if the word list found nothing
        r["layers"]["L3_issue"].pop("ai", None)
        o.receipt_json, oid, before = r, o.id, len(r["layers"]["L4_rules"]["reasons"])
        db.commit()
    done = client.post("/api/v1/admin/jobs/ai-rescan", headers=h)
    assert done.status_code == 200 and done.json()["now_same_issue"] >= 1
    with session_factory()() as db:
        o = db.get(Overlap, oid)
        ai = o.receipt_json["layers"]["L3_issue"]["ai"]
        assert ai["kind"] == "AI-written" and ai["same_issue"] is True
        assert len(o.receipt_json["layers"]["L4_rules"]["reasons"]) == before + 1


def test_gemini_request_shape_and_parsing(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    sent = {}

    class Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"candidates": [{"content": {"parts": [{"text": '{"same_issue": true, '}, {"text": '"confidence": 0.8, "reason": "ok"}'}]}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.update(url=url, headers=headers, body=json)
        return Resp()

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    assert llm.provider() == "gemini" and llm.available()
    r = issue_judge.judge(_c("a"), _c("b"))
    assert r["same_issue"] is True and r["model"] == "gemini-3.8-flash"
    assert sent["url"].startswith("https://generativelanguage.googleapis.com/") and ":generateContent" in sent["url"]
    assert sent["headers"]["x-goog-api-key"] == "test-key" and "test-key" not in sent["url"]


def test_provider_errors_mean_no_answer(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(llm.httpx, "post", boom)
    assert llm.complete("s", "u") is None
    monkeypatch.delenv("GEMINI_API_KEY")
    assert llm.provider() is None and llm.complete("s", "u") is None


def test_failure_reason_is_recorded_without_the_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-key-123")

    class Bad(Exception):
        response = type("R", (), {"status_code": 404, "text": "model not found for secret-key-123"})()

    def boom(*a, **k):
        raise Bad()

    monkeypatch.setattr(llm.httpx, "post", boom)
    assert llm.complete("s", "u") is None
    err = llm.last_error()
    assert "404" in err and "model not found" in err and "secret-key-123" not in err


def test_admin_connection_test_reports_result_or_reason(client, tokens, monkeypatch):
    h = tokens["admin"]
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    off = client.post("/api/v1/admin/ai/test", headers=h).json()
    assert off["ok"] is False and "key" in off["error"]
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(llm, "complete", lambda s, u, max_tokens=400: '{"same_issue": true, "confidence": 0.9, "reason": "Both are about a hostel deposit."}')
    ok = client.post("/api/v1/admin/ai/test", headers=h).json()
    assert ok["ok"] is True and ok["answer"]["same_issue"] is True
    assert client.post("/api/v1/admin/ai/test", headers=tokens["officer.rb"]).status_code == 403


def test_gemini_retries_without_thinking_setting_on_400(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    calls = []

    class Resp:
        def __init__(self, code): self.status_code = code
        def raise_for_status(self):
            if self.status_code >= 400: raise RuntimeError("bad")
        def json(self): return {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append("thinkingConfig" in json["generationConfig"])
        return Resp(400 if len(calls) == 1 else 200)

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    assert llm.complete("s", "u") == "OK" and calls == [True, False]


def test_gemini_retries_when_busy_then_succeeds_or_gives_up(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)

    def make(codes):
        calls = []

        class Resp:
            def __init__(self, code): self.status_code, self.text = code, "busy"
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise llm.httpx.HTTPStatusError("x", request=None, response=self)
            def json(self): return {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append(1)
            return Resp(codes[min(len(calls) - 1, len(codes) - 1)])

        return fake_post, calls

    post, calls = make([503, 503, 200])
    monkeypatch.setattr(llm.httpx, "post", post)
    assert llm.complete("s", "u") == "OK" and len(calls) == 3
    post, calls = make([503])
    monkeypatch.setattr(llm.httpx, "post", post)
    assert llm.complete("s", "u") is None and len(calls) == 4 and "503" in llm.last_error()
