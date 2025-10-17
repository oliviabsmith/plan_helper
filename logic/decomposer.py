import logging
from typing import Any, Dict, List, Optional

from db.models import Ticket
from logic.llm_client import LLMClientError, generate_subtask_bullets

logger = logging.getLogger(__name__)


def sp_to_count(sp: int) -> int:
    if sp <= 1: return 1
    if sp == 2: return 2
    if sp == 3: return 3
    if sp >= 5: return 5
    return 3


def _template_fallback(ticket: Ticket) -> List[Dict[str, Any]]:
    n = sp_to_count(ticket.story_points)
    base = ticket.title.strip()
    tags = (ticket.tech or [])[:]
    templates = [
        f"Scope & prep: confirm requirements for '{base}'",
        f"Implement core change for '{base}'",
        f"Validate in staging: tests/runbook for '{base}'",
        f"Prepare prod change window: checklist for '{base}'",
        f"Deploy & verify in prod: metrics/logs for '{base}'",
    ]
    out = []
    for i in range(n):
        out.append({"text_sub": templates[i], "tags": tags, "est_hours": 1.0 if i == 0 else 1.5})
    return out


def generate_bullets(ticket: Ticket, *, llm_options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Generate subtasks for a ticket via LLM with template fallback."""

    try:
        bullets = generate_subtask_bullets(ticket, llm_options=llm_options)
        if bullets:
            return bullets
    except LLMClientError as exc:
        logger.warning("LLM subtask generation failed; using template fallback: %s", exc)

    return _template_fallback(ticket)
