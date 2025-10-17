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
    raw_text = _invoke_with_fallback(messages, options)

    try:
        return _parse_response(raw_text, ticket.tech or [])
    except LLMClientError:
        if float(options.get("temperature", 0.3)) > 0:
            logger.info("Retrying subtask generation with deterministic temperature due to parsing error")
            deterministic_options = dict(options)
            deterministic_options["temperature"] = 0.0
            raw_text = _invoke_raw(messages, deterministic_options)
            return _parse_response(raw_text, ticket.tech or [])
        raise


def reset_cached_client() -> None:
    """Clear the cached OpenAI client. Intended for use in tests."""

    _get_openai_client.cache_clear()


def _normalize_api_error(exc: Exception) -> LLMClientError:
    if isinstance(exc, RateLimitError):
        message = "OpenAI API rate limit exceeded. Please retry shortly."
    elif isinstance(exc, APIConnectionError):
        message = "Unable to reach OpenAI API. Check network connectivity and retry."
    elif isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        message = f"OpenAI API returned status {status}: {exc}"
    else:
        message = f"Unexpected error while calling OpenAI API: {exc}"
    return LLMClientError(message)


def _extract_text_from_response(response: Any) -> str:
    raw_text = getattr(response, "output_text", None)
    if raw_text and str(raw_text).strip():
        return str(raw_text).strip()

    try:
        outputs = getattr(response, "outputs", [])
        for output in outputs or []:
            content = getattr(output, "content", [])
            for piece in content or []:
                text = getattr(piece, "text", None)
                if text and str(text).strip():
                    return str(text).strip()
    except Exception as exc:  # pragma: no cover - safety net for API changes
        raise LLMClientError(f"OpenAI response parsing failed: {exc}") from exc

    raise LLMClientError("OpenAI response did not include any text output.")


def _normalize_messages(messages: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role is None or content is None:
            raise LLMClientError("All messages must include 'role' and 'content' fields.")
        normalized.append({"role": str(role), "content": str(content)})
    return normalized


def _invoke_raw(messages: Sequence[Dict[str, str]], options: Optional[Dict[str, Any]] = None) -> str:
    prepared = _normalize_messages(messages)
    call_options = dict(options or {})
    model = call_options.get("model", DEFAULT_MODEL)
    temperature = float(call_options.get("temperature", 0.3))

    try:
        client = _get_openai_client(call_options.get("api_key"))
        response = client.responses.create(
            model=model,
            input=[{"role": msg["role"], "content": msg["content"]} for msg in prepared],
            temperature=temperature,
        )
    except (APIStatusError, APIConnectionError, RateLimitError) as exc:
        raise _normalize_api_error(exc) from exc
    except Exception as exc:  # pragma: no cover - safeguard
        raise _normalize_api_error(exc) from exc

    return _extract_text_from_response(response)


def _invoke_with_fallback(
    messages: Sequence[Dict[str, str]],
    options: Optional[Dict[str, Any]] = None,
    fallback_temperature: float = 0.0,
) -> str:
    try:
        return _invoke_raw(messages, options)
    except LLMClientError as exc:
        starting_temperature = float((options or {}).get("temperature", 0.3))
        if starting_temperature <= fallback_temperature:
            raise
        logger.warning(
            "Retrying OpenAI call with deterministic fallback temperature %s after error: %s",
            fallback_temperature,
            exc,
        )
        retry_options = dict(options or {})
        retry_options["temperature"] = fallback_temperature
        return _invoke_raw(messages, retry_options)


def request_summary(subject: str, context: str, llm_options: Optional[Dict[str, Any]] = None) -> str:
    """Generate a concise summary for downstream modules."""

    messages = [
        {
            "role": "system",
            "content": (
                "You provide crisp summaries for engineering stakeholders. "
                "Highlight the most relevant outcomes and risks in 3-4 sentences."
            ),
        },
        {
            "role": "user",
            "content": f"Subject: {subject}\n\nContext:\n{context.strip()}",
        },
    ]
    return _invoke_with_fallback(messages, llm_options)


def request_rationale(decision: str, context: str, llm_options: Optional[Dict[str, Any]] = None) -> str:
    """Provide a rationale for a decision using shared templates."""

    messages = [
        {
            "role": "system",
            "content": (
                "You explain the reasoning behind engineering decisions. "
                "Structure the answer with short paragraphs covering drivers, trade-offs, and next steps."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Decision: {decision}\n\nRelevant context:\n{context.strip()}\n"
                "Summarize why this decision is sound and call out any follow-up work."
            ),
        },
    ]
    return _invoke_with_fallback(messages, llm_options)


def request_planning_guidance(goal: str, constraints: str, llm_options: Optional[Dict[str, Any]] = None) -> str:
    """Offer planning guidance without duplicating prompt templates."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a project planner who drafts lightweight execution guidance. "
                "Return actionable steps, owners if obvious, and highlight dependencies."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Goal: {goal}\n\nKnown constraints:\n{constraints.strip()}\n"
                "Provide a short ordered list of next actions."
            ),
        },
    ]
    return _invoke_with_fallback(messages, llm_options)


def single_shot_prompt(system_prompt: str, user_prompt: str, llm_options: Optional[Dict[str, Any]] = None) -> str:
    """Convenience wrapper for simple prompts."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return _invoke_with_fallback(messages, llm_options)


def conversational_prompt(
    messages: Sequence[Dict[str, str]],
    llm_options: Optional[Dict[str, Any]] = None,
    deterministic: bool = False,
) -> str:
    """Helper for multi-turn conversations with optional deterministic behavior."""

    if deterministic:
        deterministic_options = dict(llm_options or {})
        deterministic_options["temperature"] = 0.0
        return _invoke_raw(messages, deterministic_options)
    return _invoke_with_fallback(messages, llm_options)
