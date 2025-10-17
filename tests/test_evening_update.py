from __future__ import annotations

from datetime import date
import sys
import types
from types import SimpleNamespace

import pytest

# Provide lightweight db.models stubs so evening_update can be imported without SQLAlchemy.
db_module = types.ModuleType("db")
models_module = types.ModuleType("db.models")


class SubtaskStatus:
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"


class PlanBucket:
    Focus = SimpleNamespace(value="Focus")
    Admin = SimpleNamespace(value="Admin")
    Meeting = SimpleNamespace(value="Meeting")


class Subtask:
    def __init__(self, id=None):
        self.id = id


class PlanItem:
    date = None
    bucket = None
    notes = None

    def __init__(self, date=None, bucket=None, notes=None):
        self.date = date
        self.bucket = bucket
        self.notes = notes
        self.id = None


class PlanItemSubtask:
    def __init__(self, plan_item_id=None, subtask_id=None):
        self.plan_item_id = plan_item_id
        self.subtask_id = subtask_id


class DailyLog:
    date = None

    def __init__(self, date):
        self.date = date
        self.id = None


class DailyLogItem:
    def __init__(self, log_id, subtask_id, status, note=None):
        self.log_id = log_id
        self.subtask_id = subtask_id
        self.status = status
        self.note = note


class Ticket:
    def __init__(self, title="", story_points=0, tech=None):
        self.title = title
        self.story_points = story_points
        self.tech = tech or []


models_module.SubtaskStatus = SubtaskStatus
models_module.PlanBucket = PlanBucket
models_module.PlanItem = PlanItem
models_module.PlanItemSubtask = PlanItemSubtask
models_module.Subtask = Subtask
models_module.DailyLog = DailyLog
models_module.DailyLogItem = DailyLogItem
models_module.Ticket = Ticket

db_module.models = models_module
sys.modules.setdefault("db", db_module)
sys.modules["db.models"] = models_module

from logic import evening_update
from logic.llm_client import BlockedSummary, EveningSummaryContext, LLMClientError


@pytest.fixture
def summary_context() -> EveningSummaryContext:
    return EveningSummaryContext(
        date=date(2024, 1, 1),
        completed=["Ticket A: Finish API"],
        in_progress=["Ticket B: Write tests"],
        blocked=[BlockedSummary(item="Ticket C: Deploy", note="waiting on ops")],
        carry_over=["Focus: Ticket D follow-up"],
        notes=["Carried 2 items"],
    )


def test_generate_summary_with_retry_eventual_success(monkeypatch, summary_context):
    attempts: list[int] = []

    def fake_generate(context):
        attempts.append(1)
        if len(attempts) < 2:
            raise LLMClientError("temporary failure")
        return " Great progress today. "

    monkeypatch.setattr(evening_update, "generate_evening_summary", fake_generate)
    monkeypatch.setattr(evening_update.time, "sleep", lambda _: None)

    summary = evening_update._generate_summary_with_retry(summary_context, max_attempts=3, base_delay=0.1)

    assert summary == "Great progress today."
    assert len(attempts) == 2


def test_generate_summary_with_retry_failure(monkeypatch, summary_context):
    attempts: list[int] = []

    def fake_generate(context):
        attempts.append(1)
        raise LLMClientError("still broken")

    monkeypatch.setattr(evening_update, "generate_evening_summary", fake_generate)
    monkeypatch.setattr(evening_update.time, "sleep", lambda _: None)

    summary = evening_update._generate_summary_with_retry(summary_context, max_attempts=2, base_delay=0.1)

    assert summary is None
    assert len(attempts) == 2


class FakeSession:
    def __init__(self, subtasks: dict[str, SimpleNamespace]):
        self._subtasks = subtasks
        self._log = None
        self.added = []
        self.committed = False

    class _Result:
        def __init__(self, obj):
            self._obj = obj

        def scalars(self):
            return self

        def first(self):
            return self._obj

    def execute(self, _stmt):
        return FakeSession._Result(self._log)

    def get(self, _model, sid):
        return self._subtasks.get(sid)

    def add(self, obj):
        if isinstance(obj, evening_update.DailyLog):
            if getattr(obj, "id", None) is None:
                obj.id = "log-id"
            self._log = obj
        self.added.append(obj)

    def flush(self):
        pass

    def commit(self):
        self.committed = True


def make_subtask(text: str) -> SimpleNamespace:
    return SimpleNamespace(status=evening_update.SubtaskStatus.todo, text_sub=text, ticket_id="T1")


def test_process_evening_update_returns_summary(monkeypatch):
    subtasks = {
        "c1": make_subtask("Finish docs"),
        "p1": make_subtask("Refactor module"),
        "b1": make_subtask("Deploy service"),
    }
    session = FakeSession(subtasks)

    payload = evening_update.EveningPayload(
        date=date(2024, 1, 2),
        completed=["c1"],
        partial=["p1"],
        blocked=[{"id": "b1", "note": "waiting on ops"}],
    )

    monkeypatch.setattr(evening_update, "_today_plan_blocks", lambda s, d: {})
    monkeypatch.setattr(
        evening_update,
        "_load_subtask_details",
        lambda s, ids: {
            "c1": "Ticket A: Finish docs",
            "p1": "Ticket B: Refactor module",
            "b1": "Ticket C: Deploy service",
        },
    )
    class _DummySelect:
        def where(self, *args, **kwargs):
            return self

    monkeypatch.setattr(evening_update, "select", lambda *args, **kwargs: _DummySelect())

    def fake_generate(context):
        assert session.committed is True
        assert isinstance(context, EveningSummaryContext)
        return "Summary text"

    monkeypatch.setattr(evening_update, "_generate_summary_with_retry", fake_generate)

    result = evening_update.process_evening_update(session, payload)

    assert result.summary == "Summary text"
    assert session.committed is True


def test_process_evening_update_handles_summary_failure(monkeypatch):
    session = FakeSession({})
    payload = evening_update.EveningPayload(
        date=date(2024, 1, 2),
        completed=[],
        partial=[],
        blocked=[],
    )

    monkeypatch.setattr(evening_update, "_today_plan_blocks", lambda s, d: {})
    monkeypatch.setattr(evening_update, "_load_subtask_details", lambda s, ids: {})
    class _DummySelect:
        def where(self, *args, **kwargs):
            return self

    monkeypatch.setattr(evening_update, "select", lambda *args, **kwargs: _DummySelect())

    def fake_generate(_context):
        raise RuntimeError("boom")

    monkeypatch.setattr(evening_update, "_generate_summary_with_retry", fake_generate)

    result = evening_update.process_evening_update(session, payload)

    assert result.summary is None
    assert session.committed is True
