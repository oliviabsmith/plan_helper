"""Narrative helpers shared across report generators."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from openai import APIConnectionError, APIStatusError, RateLimitError

from logic.llm_client import DEFAULT_MODEL, LLMClientError, _get_openai_client


# Keys that can be forwarded directly to the OpenAI responses.create call.
_ALLOWED_REQUEST_KEYS = {
    "max_output_tokens",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "response_format",
}


def make_morning_narrative(payload: Dict[str, Any], llm_options: Optional[Dict[str, Any]] = None) -> str:
    """Generate a short narrative for the morning report using the shared LLM helper."""

    if not isinstance(payload, dict):
        raise ValueError("payload must be a dictionary of report data")

    options = dict(llm_options or {})
    api_key = options.pop("api_key", None)
    model = options.pop("model", DEFAULT_MODEL)
    temperature = float(options.pop("temperature", 0.35))
    tone = options.pop("tone", None)

    request_kwargs = {k: options[k] for k in _ALLOWED_REQUEST_KEYS if k in options}

    client = _get_openai_client(api_key)

    system_lines = [
        "You are the user's planning copilot writing a concise morning briefing.",
        "Summaries should help the user glide into their day and respect the provided structure.",
        "Mention context tags as hashtags (e.g., #aws.lambda) when relevant.",
        "Reference memory snippets using [mem:<id>] if they materially inform the plan.",
        "Keep the tone practical and forward-looking.",
        "Write 2 short paragraphs, no bullet lists, and keep the total under 120 words.",
    ]
    if tone:
        system_lines.append(f"Adopt a {tone} tone while staying professional.")

    user_payload = {
        "date": payload.get("date"),
        "context_tags": payload.get("context_tags", []),
        "risks": payload.get("risks", []),
        "batches": payload.get("batches", []),
        "checklist": payload.get("checklist", []),
        "memory": payload.get("memory", []),
    }
    user_prompt = (
        "Here is the structured data for today's plan."
        "\n```json\n"
        f"{json.dumps(user_payload, indent=2)}"
        "\n```\n"
        "Write the narrative now."
    )

    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "\n".join(system_lines)},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            **request_kwargs,
        )
    except (APIStatusError, APIConnectionError, RateLimitError) as exc:
        raise LLMClientError(f"OpenAI API error while generating narrative: {exc}") from exc
    except Exception as exc:  # pragma: no cover - protective guardrail
        raise LLMClientError(f"Unexpected error while generating narrative: {exc}") from exc

    text = getattr(response, "output_text", None)
    if not text:
        try:
            text = response.outputs[0].content[0].text  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - handle SDK response drift
            raise LLMClientError(f"OpenAI response missing text output: {exc}") from exc

    return text.strip()
