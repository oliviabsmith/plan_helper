# logic/morning_report.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Optional, Any
from collections import Counter, defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import select

from db.models import (
    PlanItem, PlanItemSubtask, Subtask, Ticket,
    PlanBucket, MemorySnippet
)

from logic.llm_client import LLMClientError
from logic.report_narrative import make_morning_narrative

@dataclass
class ChecklistItem:
    subtask_id: str
    ticket_id: str
    seq: int
    text_sub: str
    why_now: str
    tags: list[str]

@dataclass
class BatchOut:
    note: str                  # e.g., affinity key or "solo:<ticket>"
    plan_item_id: str
    members: list[str]         # subtask ids
    rationale: str             # echo of note or brief reason

@dataclass
class NarrativeSection:
    text: Optional[str]
    context_tags: List[str]
    memory_refs: List[str]
    error: Optional[str] = None


@dataclass
class MorningReport:
    date: str
    checklist: List[ChecklistItem]
    batches: List[BatchOut]
    risks: List[str]
    memory_top3: List[dict]    # [{id, topic, text, pinned, created_at}]
    narrative: Optional[NarrativeSection] = None

def _collect_today_plan(s: Session, d: date):
    # Pull today's plan items (Focus/Admin only – skip Meeting if you don’t use it yet)
    items = s.execute(
        select(PlanItem)
        .where(PlanItem.date == d)
        .order_by(PlanItem.bucket.desc())  # Focus first, then Admin
    ).scalars().all()

    # Map plan_item -> subtasks
    block_subtasks: Dict[str, list[Subtask]] = defaultdict(list)
    for pi in items:
        links = s.execute(
            select(PlanItemSubtask).where(PlanItemSubtask.plan_item_id == pi.id)
        ).scalars().all()
        if not links:
            continue
        subs = s.execute(
            select(Subtask).where(Subtask.id.in_([l.subtask_id for l in links]))
        ).scalars().all()
        # stable within ticket
        subs.sort(key=lambda st: (st.ticket_id, st.seq))
        block_subtasks[str(pi.id)].extend(subs)

    return items, block_subtasks

def _dominant_tags(block_subtasks: Dict[str, list[Subtask]], k: int = 3) -> list[str]:
    c = Counter()
    for subs in block_subtasks.values():
        for st in subs:
            for t in (st.tags or []):
                c[t] += 1
    return [t for t, _ in c.most_common(k)]

def _why_now(note: Optional[str], ticket_due: Optional[str]) -> str:
    bits = []
    if note:
        bits.append(f"batch: {note}")
    if ticket_due:
        bits.append(f"due {ticket_due}")
    return " + ".join(bits) if bits else "scheduled"

def _memory_for_tags(s: Session, tags: list[str], limit: int = 3) -> List[dict]:
    if not tags:
        # Fallback: recent pinned or latest snippets
        rows = s.execute(
            select(MemorySnippet)
            .order_by(MemorySnippet.pinned.desc(), MemorySnippet.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return [
            {"id": str(m.id), "topic": m.topic, "text": m.text, "pinned": m.pinned, "created_at": m.created_at.isoformat()}
            for m in rows
        ]

    # Simple heuristic: topic ilike any dominant tag
    conds = []
    from sqlalchemy import or_
    for t in tags:
        conds.append(MemorySnippet.topic.ilike(f"%{t}%"))
    rows = s.execute(
        select(MemorySnippet)
        .where(or_(*conds))
        .order_by(MemorySnippet.pinned.desc(), MemorySnippet.created_at.desc())
        .limit(limit)
    ).scalars().all()

    return [
        {"id": str(m.id), "topic": m.topic, "text": m.text, "pinned": m.pinned, "created_at": m.created_at.isoformat()}
        for m in rows
    ]

def make_morning_report(
    s: Session,
    d: date,
    *,
    include_narrative: bool = False,
    narrative_options: Optional[Dict[str, Any]] = None,
) -> MorningReport:
    items, block_subs = _collect_today_plan(s, d)

    # Join tickets for due dates
    by_ticket: Dict[str, Ticket] = {}
    if block_subs:
        ticket_ids = list({st.ticket_id for subs in block_subs.values() for st in subs})
        tickets = s.execute(select(Ticket).where(Ticket.id.in_(ticket_ids))).scalars().all()
        by_ticket = {t.id: t for t in tickets}

    checklist: List[ChecklistItem] = []
    batches: List[BatchOut] = []
    risks: List[str] = []

    # Build list in the order of plan items (Focus first)
    for pi in items:
        if pi.bucket not in (PlanBucket.Focus, PlanBucket.Admin):
            continue

        subs = block_subs.get(str(pi.id), [])
        if pi.bucket == PlanBucket.Admin:
            # Admin block → no checklist items, but still show as batch block with no members
            batches.append(BatchOut(
                note=pi.notes or "Admin",
                plan_item_id=str(pi.id),
                members=[],
                rationale=pi.notes or "Admin/Buffer"
            ))
            continue

        # Focus blocks → produce checklist items + batch descriptor
        member_ids = []
        for st in subs:
            t = by_ticket.get(st.ticket_id)
            due_s = t.due_date.isoformat() if (t and t.due_date) else None
            checklist.append(ChecklistItem(
                subtask_id=str(st.id),
                ticket_id=st.ticket_id,
                seq=st.seq,
                text_sub=st.text_sub,
                why_now=_why_now(pi.notes, due_s),
                tags=st.tags or []
            ))
            member_ids.append(str(st.id))

        batches.append(BatchOut(
            note=pi.notes or "solo",
            plan_item_id=str(pi.id),
            members=member_ids,
            rationale=pi.notes or "solo subtask"
        ))

    # Simple risk heuristic
    #  - Focus block with more than ~6 members (too chunky)
    for b in batches:
        if len(b.members) > 6 and b.note != "Admin":
            risks.append(f"Large block ({len(b.members)} subtasks) in '{b.note}': consider splitting.")

    # Memory snippets by dominant tags
    dom_tags = _dominant_tags(block_subs, k=3)
    mem = _memory_for_tags(s, dom_tags, limit=3)

    narrative_section: Optional[NarrativeSection] = None
    if include_narrative:
        memory_refs = [m["id"] for m in mem if m.get("id")]
        payload = {
            "date": d.isoformat(),
            "checklist": [
                {
                    "ticket_id": item.ticket_id,
                    "seq": item.seq,
                    "text_sub": item.text_sub,
                    "why_now": item.why_now,
                    "tags": item.tags,
                }
                for item in checklist
            ],
            "batches": [
                {
                    "note": batch.note,
                    "member_count": len(batch.members),
                    "members": batch.members,
                    "rationale": batch.rationale,
                }
                for batch in batches
            ],
            "risks": list(risks),
            "context_tags": list(dom_tags),
            "memory": mem,
        }
        try:
            text = make_morning_narrative(payload, llm_options=narrative_options or {})
            narrative_section = NarrativeSection(
                text=text.strip() if text else None,
                context_tags=list(dom_tags),
                memory_refs=memory_refs,
            )
        except LLMClientError as exc:
            narrative_section = NarrativeSection(
                text=None,
                context_tags=list(dom_tags),
                memory_refs=memory_refs,
                error=str(exc),
            )

    return MorningReport(
        date=d.isoformat(),
        checklist=checklist,
        batches=batches,
        risks=risks,
        memory_top3=mem,
        narrative=narrative_section,
    )
