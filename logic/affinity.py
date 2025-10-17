# logic/affinity.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Dict, Tuple, Optional
from collections import defaultdict
import logging

from logic.llm_client import (
    LLMClientError,
    generate_affinity_group_narrative,
)

logger = logging.getLogger(__name__)

# Simple tag conventions
ENV_TAGS = {"dev", "development", "staging", "stage", "preprod", "prod", "production"}
CONTEXT_PREFIXES = ("aws.", "gcp.", "azure.", "terraform", "k8s.", "docker", "db.", "iam")

@dataclass
class SubtaskLike:
    id: str
    ticket_id: str
    tags: List[str]
    text_sub: str

@dataclass
class AffinityGroupOut:
    key: str
    member_ids: List[str]
    rationale: str

def _normalize_tag(t: str) -> str:
    return (t or "").strip().lower().replace(" ", ".")

def _extract_env(tags: Iterable[str]) -> Optional[str]:
    for t in tags:
        nt = _normalize_tag(t)
        if nt in ENV_TAGS:
            return "prod" if nt in {"prod", "production"} else ("staging" if nt in {"staging","stage","preprod"} else "dev")
    return None

def _extract_contexts(tags: Iterable[str]) -> List[str]:
    out = set()
    for t in tags:
        nt = _normalize_tag(t)
        for p in CONTEXT_PREFIXES:
            if nt.startswith(p):
                out.add(nt.split(":")[0])  # strip module qualifiers like terraform.module:xyz
                break
    return sorted(out) if out else []

def _make_key(contexts: List[str], env: Optional[str]) -> str:
    base = "+".join(contexts) if contexts else "misc"
    return f"{base}:{env}" if env else base

def compute_affinity_groups(subtasks: Iterable[SubtaskLike]) -> List[AffinityGroupOut]:
    """
    Rule-based grouping:
      - Same *contexts* (derived from tag prefixes like aws.*, terraform, iam, etc.)
      - Same *environment* if present (dev/staging/prod)
    Rationale explains the shared context & env.
    """
    buckets: Dict[str, List[SubtaskLike]] = defaultdict(list)
    sig_map: Dict[str, Tuple[List[str], Optional[str]]] = {}

    for st in subtasks:
        tags = st.tags or []
        env = _extract_env(tags)
        ctx = _extract_contexts(tags)
        key = _make_key(ctx, env)
        buckets[key].append(st)
        sig_map[key] = (ctx, env)

    groups: List[AffinityGroupOut] = []
    for key, members in buckets.items():
        if len(members) < 2:
            # batching only meaningful if there's at least 2 items
            continue
        ctx, env = sig_map[key]
        why = []
        if ctx:
            why.append(f"shared context: {', '.join(ctx)}")
        if env:
            why.append(f"same environment: {env}")
        if not why:
            why.append("similar tags")
        rationale = "; ".join(why)
        try:
            narrative = generate_affinity_group_narrative(members)
        except LLMClientError as exc:
            logger.warning("LLM affinity narrative failed for key %s: %s", key, exc)
            narrative = ""
        if narrative:
            rationale = f"{rationale} | {narrative}"
        groups.append(
            AffinityGroupOut(
                key=key,
                member_ids=[str(m.id) for m in members],
                rationale=rationale,
            )
        )
    return groups
