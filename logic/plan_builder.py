# logic/plan_builder.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, List, Dict, Set, Optional, Tuple
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, delete

from db.models import (
    Ticket, Subtask, SubtaskStatus,
    AffinityGroup, AffinityMember,
    PlanItem, PlanItemSubtask, PlanBucket
)
from logic.llm_client import summarize_focus_block

# --------------------------
# Constraints + parameters
# --------------------------
@dataclass
class PlanConstraints:
    max_contexts_per_day: int = 2
    max_focus_blocks_per_day: int = 4
    buffer_ratio: float = 0.20  # 20% of blocks kept as slack
    workdays: tuple[int, ...] = (0, 1, 2, 3, 4)  # Mon..Fri (Python weekday: Mon=0)

# --------------------------
# Helpers
# --------------------------
def _iter_workdays(start: date, days: int, workdays: tuple[int, ...]) -> List[date]:
    out: List[date] = []
    d = start
    while len(out) < days:
        if d.weekday() in workdays:
            out.append(d)
        d += timedelta(days=1)
    return out

def _load_open_subtasks(s: Session, ticket_ids: Optional[List[str]] = None) -> List[Subtask]:
    stmt = select(Subtask).where(Subtask.status.in_([SubtaskStatus.todo, SubtaskStatus.in_progress]))
    if ticket_ids:
        stmt = stmt.where(Subtask.ticket_id.in_(ticket_ids))
    # stable order: by ticket then seq
    stmt = stmt.order_by(Subtask.ticket_id, Subtask.seq)
    return s.execute(stmt).scalars().all()

def _due_map(s: Session, ticket_ids: Iterable[str]) -> Dict[str, Optional[date]]:
    if not ticket_ids:
        return {}
    tks = s.execute(select(Ticket).where(Ticket.id.in_(list(set(ticket_ids))))).scalars().all()
    return {t.id: t.due_date for t in tks}

def _load_affinity_groups(s: Session) -> Dict[str, Tuple[str, List[str]]]:
    """
    Returns: group_id -> (key, [subtask_ids])
    """
    groups = s.execute(select(AffinityGroup)).scalars().all()
    out: Dict[str, Tuple[str, List[str]]] = {}
    for g in groups:
        members = s.execute(select(AffinityMember).where(AffinityMember.group_id == g.id)).scalars().all()
        out[str(g.id)] = (g.key, [str(m.subtask_id) for m in members])
    return out

def _dominant_key_for_subtask(affinity: Dict[str, Tuple[str, List[str]]], subtask_id: str) -> Optional[str]:
    """
    If a subtask appears in multiple groups (rare), pick lexicographically smallest key for stability.
    Returns the affinity key (e.g., "aws.lambda+terraform:staging") or None.
    """
    keys = []
    for _, (k, members) in affinity.items():
        if subtask_id in members:
            keys.append(k)
    return sorted(keys)[0] if keys else None

# --------------------------
# Core planning algorithm
# --------------------------
@dataclass
class PlannedBlock:
    date: date
    bucket: PlanBucket  # Focus/Admin/Meeting
    note: Optional[str]
    subtask_ids: List[str]

def build_plan(
    s: Session,
    start: date,
    days: int = 10,
    constraints: PlanConstraints = PlanConstraints(),
    clear_existing_from_start: bool = True,
    ticket_subset: Optional[List[str]] = None,
) -> List[PlannedBlock]:
    """
    Build a 10-workday plan from open subtasks & affinity groups.
    Writes to plan_items + plan_item_subtasks if you call persist_plan().
    Returns the in-memory PlannedBlocks for inspection/testing.
    """
    workdays = _iter_workdays(start, days, constraints.workdays)

    subtasks = _load_open_subtasks(s, ticket_subset)
    if not subtasks:
        return []

    due = _due_map(s, [st.ticket_id for st in subtasks])
    aff = _load_affinity_groups(s)

    # Partition subtasks by affinity key (batch first), then solo items.
    by_key: Dict[Optional[str], List[Subtask]] = defaultdict(list)
    for st in subtasks:
        key = _dominant_key_for_subtask(aff, str(st.id))
        by_key[key].append(st)

    affinity_batches: List[Tuple[str, List[Subtask]]] = []
    for key, sts in by_key.items():
        if key is not None and len(sts) >= 2:
            # order inside batch: earlier due date first, then ticket, seq
            sts_sorted = sorted(sts, key=lambda x: (due.get(x.ticket_id) or date.max, x.ticket_id, x.seq))
            affinity_batches.append((key, sts_sorted))
    # Sort batches by earliest due among their members
    affinity_batches.sort(key=lambda kv: min([(due.get(st.ticket_id) or date.max) for st in kv[1]]))

    # Remaining singletons
    singleton_subtasks: List[Subtask] = []
    for key, sts in by_key.items():
        if key is None or len(sts) == 1:
            singleton_subtasks.extend(sts)
    singleton_subtasks = sorted(singleton_subtasks, key=lambda x: (due.get(x.ticket_id) or date.max, x.ticket_id, x.seq))

    # Per-day schedule
    planned: List[PlannedBlock] = []
    used_subtasks: Set[str] = set()

    # How many Focus blocks/day after buffer?
    raw_blocks = constraints.max_focus_blocks_per_day
    buffer_blocks = max(1, int(round(raw_blocks * constraints.buffer_ratio)))
    focus_blocks_per_day = max(1, raw_blocks - buffer_blocks)

    # Fill days
    batch_idx = 0
    singleton_idx = 0

    for d in workdays:
        day_contexts: Set[str] = set()
        blocks_today: List[PlannedBlock] = []

        # 1) Allocate affinity batches in morning Focus blocks, respecting contexts/day
        fb = 0
        while fb < focus_blocks_per_day and batch_idx < len(affinity_batches):
            key, sts = affinity_batches[batch_idx]
            batch_idx += 1
            # Context control
            ctx_part = key.split(":")[0] if ":" in key else key
            if len(day_contexts) < constraints.max_contexts_per_day or ctx_part in day_contexts:
                day_contexts.add(ctx_part)
                ids = [str(st.id) for st in sts if str(st.id) not in used_subtasks]
                if ids:
                    note_payload = []
                    for st in sts:
                        if str(st.id) in ids:
                            due_date = due.get(st.ticket_id)
                            note_payload.append(
                                {
                                    "subtask_id": str(st.id),
                                    "ticket_id": st.ticket_id,
                                    "detail": st.text_sub,
                                    "due_date": due_date.isoformat() if due_date else "",
                                }
                            )
                    note_text = summarize_focus_block(
                        block_date=d,
                        items=note_payload,
                        fallback_note=key,
                    )
                    blocks_today.append(PlannedBlock(date=d, bucket=PlanBucket.Focus, note=note_text, subtask_ids=ids))
                    used_subtasks.update(ids)
                    fb += 1
            # else: skip this batch for today (it will be reconsidered tomorrow)
        # Rewind skipped batches logic: simple MVP — skipped batches are effectively lost today;
        # they will be placed as singletons pass if members remain unplanned.

        # 2) Fill remaining Focus slots with singletons, respecting contexts/day
        while fb < focus_blocks_per_day and singleton_idx < len(singleton_subtasks):
            # Pick next not-yet-used singleton
            pick: Optional[Subtask] = None
            while singleton_idx < len(singleton_subtasks) and not pick:
                cand = singleton_subtasks[singleton_idx]
                singleton_idx += 1
                if str(cand.id) not in used_subtasks:
                    pick = cand
            if not pick:
                break

            # Determine "context key" from its dominant affinity (if any) for context control
            dom_key = _dominant_key_for_subtask(aff, str(pick.id))
            ctx_part = (dom_key.split(":")[0] if dom_key and ":" in dom_key else dom_key) or f"{pick.ticket_id}"
            if len(day_contexts) >= constraints.max_contexts_per_day and ctx_part not in day_contexts:
                # can't add a new context today; push to next day by just not scheduling now
                continue

            fallback_note = dom_key or f"solo:{pick.ticket_id}"
            pick_due = due.get(pick.ticket_id)
            note_text = summarize_focus_block(
                block_date=d,
                items=[
                    {
                        "subtask_id": str(pick.id),
                        "ticket_id": pick.ticket_id,
                        "detail": pick.text_sub,
                        "due_date": pick_due.isoformat() if pick_due else "",
                    }
                ],
                fallback_note=fallback_note,
            )
            blocks_today.append(PlannedBlock(
                date=d, bucket=PlanBucket.Focus,
                note=note_text,
                subtask_ids=[str(pick.id)]
            ))
            used_subtasks.add(str(pick.id))
            day_contexts.add(ctx_part)
            fb += 1

        # 3) Add Admin buffer block (no subtasks assigned)
        blocks_today.append(PlannedBlock(date=d, bucket=PlanBucket.Admin, note="Buffer/Slack", subtask_ids=[]))

        planned.extend(blocks_today)

    # Clear existing plan from start forward (optional)
    if clear_existing_from_start:
        s.execute(delete(PlanItem).where(PlanItem.date >= workdays[0]))
        s.flush()

    return planned

def persist_plan(s: Session, planned: List[PlannedBlock]) -> None:
    """
    Take PlannedBlocks and write rows to plan_items + plan_item_subtasks.
    """
    for blk in planned:
        pi = PlanItem(date=blk.date, bucket=blk.bucket, notes=blk.note)
        s.add(pi)
        s.flush()
        for sid in blk.subtask_ids:
            s.add(PlanItemSubtask(plan_item_id=pi.id, subtask_id=sid))
    s.commit()
