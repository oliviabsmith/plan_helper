import sys
import types

import pytest


class DummyTicket:
    def __init__(self, title: str, story_points: int, tech: list[str] | None = None):
        self.title = title
        self.story_points = story_points
        self.tech = tech or []


# Provide a lightweight stand-in for db.models so the real SQLAlchemy dependency
# is not required when importing the decomposer module during tests.
db_module = types.ModuleType("db")
models_module = types.ModuleType("db.models")
models_module.Ticket = DummyTicket
db_module.models = models_module
sys.modules.setdefault("db", db_module)
sys.modules["db.models"] = models_module

from logic import decomposer
from logic.llm_client import LLMClientError


def test_generate_bullets_llm_success(monkeypatch):
    captured = {}

    def fake_generate(ticket, llm_options=None):
        captured["ticket"] = ticket
        captured["llm_options"] = llm_options
        return [{"text_sub": "LLM generated", "tags": ["python"], "est_hours": 2.0}]

    monkeypatch.setattr(decomposer, "generate_subtask_bullets", fake_generate)

    ticket = DummyTicket("Add login", 3, ["python", "flask"])
    bullets = decomposer.generate_bullets(ticket, llm_options={"tone": "concise"})

    assert bullets == [{"text_sub": "LLM generated", "tags": ["python"], "est_hours": 2.0}]
    assert captured["llm_options"] == {"tone": "concise"}
    assert captured["ticket"] is ticket


def test_generate_bullets_llm_failure(monkeypatch):
    def fake_generate(ticket, llm_options=None):
        raise LLMClientError("API key missing")

    monkeypatch.setattr(decomposer, "generate_subtask_bullets", fake_generate)

    ticket = DummyTicket("Ship feature", 2, ["backend"])
    bullets = decomposer.generate_bullets(ticket)

    assert len(bullets) == decomposer.sp_to_count(ticket.story_points)
    assert all("Ship feature" in b["text_sub"] for b in bullets)
