import pytest

from logic.affinity import SubtaskLike, compute_affinity_groups
from logic.llm_client import LLMClientError


@pytest.fixture
def sample_subtasks():
    return [
        SubtaskLike(
            id="1",
            ticket_id="T-100",
            tags=["aws.lambda", "prod"],
            text_sub="Create deployment pipeline",
        ),
        SubtaskLike(
            id="2",
            ticket_id="T-101",
            tags=["aws.lambda", "production"],
            text_sub="Configure IAM roles",
        ),
    ]


def test_affinity_group_includes_llm_narrative(monkeypatch, sample_subtasks):
    def fake_narrative(members):
        assert [m.id for m in members] == ["1", "2"]
        return "Both focus on preparing the Lambda stack for production releases."

    monkeypatch.setattr(
        "logic.affinity.generate_affinity_group_narrative",
        fake_narrative,
    )

    groups = compute_affinity_groups(sample_subtasks)
    assert groups
    rationale = groups[0].rationale
    assert rationale.startswith("shared context: aws.lambda; same environment: prod")
    assert "Both focus on preparing the Lambda stack for production releases." in rationale


def test_affinity_group_falls_back_when_llm_unavailable(monkeypatch, sample_subtasks):
    def raise_llm_error(members):
        raise LLMClientError("API unavailable")

    monkeypatch.setattr(
        "logic.affinity.generate_affinity_group_narrative",
        raise_llm_error,
    )

    groups = compute_affinity_groups(sample_subtasks)
    assert groups
    # Should retain the deterministic explanation only
    assert groups[0].rationale == "shared context: aws.lambda; same environment: prod"
