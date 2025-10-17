"""LLM helper utilities for generating subtasks."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence

from openai import OpenAI
from openai import APIStatusError, APIConnectionError, RateLimitError

from db.models import Ticket

logger = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    """Raised when the LLM client cannot fulfill a request."""


DEFAULT_MODEL = "gpt-4o-mini"


@lru_cache(maxsize=1)
def _get_openai_client(api_key: Optional[str] = None) -> OpenAI:
    """Return a cached OpenAI client instance.

    Parameters
    ----------
    api_key:
        Optional override for the API key. Primarily used for testing.
    """

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise LLMClientError(
            "OPENAI_API_KEY environment variable is not configured."
        )
    return OpenAI(api_key=key)


def _build_prompt(ticket: Ticket, llm_options: Dict[str, Any]) -> List[Dict[str, str]]:
    tags: Iterable[str] = ticket.tech or []
    tone = llm_options.get("tone")
    extra_context = llm_options.get("extra_context")
    max_items = llm_options.get("max_subtasks") or 5
    requested_model = llm_options.get("model")

    system_lines = [
        "You are an experienced software delivery lead helping to break down work.",
        "Produce well-scoped, actionable bullet items for engineers.",
        "Respond with a JSON array where each element has keys 'text_sub', 'tags', and 'est_hours'.",
        "Do not include markdown or commentary outside of JSON.",
    ]
    if tone:
        system_lines.append(f"Write the text_sub field with a {tone} tone.")

    user_lines = [
        f"Ticket title: {ticket.title.strip()}",
        f"Story points: {ticket.story_points}",
        f"Tags: {', '.join(tags) if tags else 'none'}",
        f"Create at most {max_items} subtasks.",
        "Each subtask should estimate hours as a number (may be fractional).",
    ]
    if extra_context:
        user_lines.append(f"Additional context: {extra_context}")

    messages = [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": "\n".join(user_lines)},
    ]

    if requested_model:
        llm_options["model"] = requested_model

    return messages


def _parse_response(raw_text: str, default_tags: Iterable[str]) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"Unable to parse LLM response as JSON: {exc}") from exc

    if not isinstance(payload, list):
        raise LLMClientError("LLM response must be a JSON array of subtasks.")

    normalized: List[Dict[str, Any]] = []
    default_tag_list = [str(tag) for tag in default_tags if str(tag).strip()]

    for item in payload:
        if not isinstance(item, dict):
            logger.debug("Skipping non-dict item in LLM response: %r", item)
            continue

        text = item.get("text_sub") or item.get("text")
        if not text or not str(text).strip():
            logger.debug("Skipping LLM item without text_sub: %r", item)
            continue

        tags = item.get("tags")
        if tags is None:
            tags_list = list(default_tag_list)
        elif isinstance(tags, (list, tuple)):
            tags_list = [str(t).strip() for t in tags if str(t).strip()]
        else:
            tags_list = [str(tags).strip()] if str(tags).strip() else list(default_tag_list)

        est = item.get("est_hours")
        if est is None or est == "":
            est_hours: Optional[float] = None
        else:
            try:
                est_hours = float(est)
            except (TypeError, ValueError):
                logger.debug("Invalid est_hours in LLM response, dropping value: %r", est)
                est_hours = None

        normalized.append({
            "text_sub": str(text).strip(),
            "tags": tags_list,
            "est_hours": est_hours,
        })

    if not normalized:
        raise LLMClientError("LLM response did not include any usable subtasks.")

    return normalized


def generate_subtask_bullets(ticket: Ticket, llm_options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Generate subtasks for a ticket using the OpenAI API.

    Parameters
    ----------
    ticket:
        The ticket model to summarize.
    llm_options:
        Optional overrides such as tone, extra_context, model, or max_subtasks.
    """

    options = dict(llm_options or {})
    messages = _build_prompt(ticket, options)
    model = options.get("model", DEFAULT_MODEL)

    try:
        client = _get_openai_client(options.get("api_key"))
        response = client.responses.create(
            model=model,
            input=[{"role": m["role"], "content": m["content"]} for m in messages],
            temperature=float(options.get("temperature", 0.3)),
        )
    except (APIStatusError, APIConnectionError, RateLimitError) as exc:
        raise LLMClientError(f"OpenAI API error: {exc}") from exc
    except Exception as exc:  # pragma: no cover - safeguard
        raise LLMClientError(f"Unexpected error while calling OpenAI API: {exc}") from exc

    raw_text = getattr(response, "output_text", None)
    if not raw_text:
        # Attempt to recover from the structured format when output_text is unavailable
        try:
            raw_text = response.outputs[0].content[0].text  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - safety net for API changes
            raise LLMClientError(f"OpenAI response did not include text output: {exc}") from exc

    return _parse_response(raw_text, ticket.tech or [])


def _format_affinity_members(members: Sequence[Any]) -> str:
    lines: List[str] = []
    for idx, member in enumerate(members, start=1):
        text = getattr(member, "text_sub", "") or ""
        tags = getattr(member, "tags", None)
        ticket_id = getattr(member, "ticket_id", "") or ""
        normalized_tags = ", ".join(str(tag).strip() for tag in (tags or []) if str(tag).strip())
        desc_parts = [f"{idx}."]
        if ticket_id:
            desc_parts.append(f"ticket {ticket_id}")
        if getattr(member, "id", None):
            desc_parts.append(f"subtask {getattr(member, 'id')}")
        if text:
            desc_parts.append(f"\"{str(text).strip()}\"")
        if normalized_tags:
            desc_parts.append(f"tags: {normalized_tags}")
        lines.append(" ".join(desc_parts))
    if not lines:
        raise LLMClientError("Affinity narrative requires at least one subtask description.")
    return "\n".join(lines)


def generate_affinity_group_narrative(
    members: Iterable[Any],
    llm_options: Optional[Dict[str, Any]] = None,
) -> str:
    """Produce a natural-language rationale for a set of related subtasks."""

    member_list = list(members)
    formatted_members = _format_affinity_members(member_list)

    options = dict(llm_options or {})
    model = options.get("model", DEFAULT_MODEL)
    messages = [
        {
            "role": "system",
            "content": (
                "You are helping project managers explain why subtasks can be batched together. "
                "Respond with one or two concise sentences summarizing the shared objective."
            ),
        },
        {
            "role": "user",
            "content": (
                "Here are the subtasks that will be batched:\n"
                f"{formatted_members}\n"
                "Explain the common theme or dependency they share."
            ),
        },
    ]

    try:
        client = _get_openai_client(options.get("api_key"))
        response = client.responses.create(
            model=model,
            input=[{"role": m["role"], "content": m["content"]} for m in messages],
            temperature=float(options.get("temperature", 0.2)),
        )
    except (APIStatusError, APIConnectionError, RateLimitError) as exc:
        raise LLMClientError(f"OpenAI API error: {exc}") from exc
    except Exception as exc:  # pragma: no cover - safeguard
        raise LLMClientError(f"Unexpected error while calling OpenAI API: {exc}") from exc

    raw_text = getattr(response, "output_text", None)
    if not raw_text:
        try:
            raw_text = response.outputs[0].content[0].text  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - safety net for API changes
            raise LLMClientError(f"OpenAI response did not include text output: {exc}") from exc

    narrative = str(raw_text).strip()
    if not narrative:
        raise LLMClientError("LLM affinity narrative was empty.")

    return narrative


def reset_cached_client() -> None:
    """Clear the cached OpenAI client. Intended for use in tests."""

    _get_openai_client.cache_clear()
