from datetime import date

import pytest

from logic import llm_client


class DummyResponse:
    def __init__(self, text: str):
        self.output_text = text


class DummyClient:
    def __init__(self, texts):
        self._texts = texts
        self.calls = 0

        class _Responses:
            def __init__(self, outer):
                self._outer = outer

            def create(self, **kwargs):
                self._outer.calls += 1
                return DummyResponse(self._outer._texts[self._outer.calls - 1])

        self.responses = _Responses(self)


@pytest.fixture(autouse=True)
def clear_focus_cache():
    llm_client.reset_focus_note_cache()
    yield
    llm_client.reset_focus_note_cache()


def test_summarize_focus_block_falls_back_when_missing_items():
    assert (
        llm_client.summarize_focus_block(
            block_date=date(2025, 1, 1),
            items=[],
            fallback_note="solo:TKT-1",
        )
        == "solo:TKT-1"
    )


def test_summarize_focus_block_uses_llm_and_caches(monkeypatch):
    dummy = DummyClient(["Focus: API polish"])
    monkeypatch.setattr(llm_client, "_get_openai_client", lambda _api_key=None: dummy)

    payload = [
        {
            "subtask_id": "abc",
            "ticket_id": "TKT-7",
            "detail": "Tidy API responses",
            "due_date": "2025-01-03",
        }
    ]

    note_first = llm_client.summarize_focus_block(date(2025, 1, 2), payload, "fallback")
    note_second = llm_client.summarize_focus_block(date(2025, 1, 2), payload, "fallback")

    assert note_first == "Focus: API polish"
    assert note_second == "Focus: API polish"
    assert dummy.calls == 1


def test_summarize_focus_block_handles_llm_errors(monkeypatch):
    class BrokenClient:
        class _Responses:
            def create(self, **kwargs):
                raise llm_client.APIStatusError("boom")

        responses = _Responses()

    monkeypatch.setattr(llm_client, "_get_openai_client", lambda _api_key=None: BrokenClient())

    payload = [
        {
            "subtask_id": "abc",
            "ticket_id": "TKT-7",
            "detail": "Tidy API responses",
            "due_date": "",
        }
    ]

    note = llm_client.summarize_focus_block(date(2025, 1, 2), payload, "fallback")
    assert note == "fallback"
