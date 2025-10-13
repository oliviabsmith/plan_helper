# logic/evening_update.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Optional, Iterable
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import select, insert

from db.models import (
    Subtask, SubtaskStatus,
    PlanItem, PlanItemSubtask, PlanBucket,
    DailyLog, DailyLogItem
)

WEEKDAYS = {0,1,2,3,4}  # Mon..Fri

@dataclass
class EveningPayload:
    date: date
    completed: List[str]         # subtask ids
    partial: List[str]           # subtask ids
    blocked: List[Dict[str,str]] # [{"id": subtask_id, "note": "..."}]

@dataclass
class EveningResult:
    plan_delta: List[Dict]       # newly created plan_items (id,date,bucket,notes,subtask_ids)
    notes: List[str]

def _next_workday(d: date) -> date:
    x = d + timedelta(days=1)
    while x.weekday() not in WEEKDAYS:
        x += timedelta(days=1)
    return x

def _today_plan_blocks(s: Session, d: date) -> Dict[str, Dict]:
    """Return {plan_item_id: {'pi': PlanItem, 'subtask_ids': [..]}} for today."""
    out: Dict[str, Dict] = {}
    items = s.execute(select(PlanItem).where(PlanItem.date == d)).scalars().all()
    for pi in items:
        links = s.execute(select(PlanItemSubtask).where(PlanItemSubtask.plan_item_id == pi.id)).scalars().all()
        out[str(pi.id)] = {
            "pi": pi,
            "subtask_ids": [str(l.subtask_id) for l in links]
        }
    return out

def _append_to_plan_block(s: Session, d: date, note: str, subtask_ids: Iterable[str]) -> PlanItem:
    """Find or create a Focus block on date d for 'note' and attach subtasks."""
    # try to find an existing block with same note & Focus bucket
    existing = s.execute(
        select(PlanItem).where(PlanItem.date == d, PlanItem.bucket == PlanBucket.Focus, PlanItem.notes == note)
    ).scalars().first()
    if existing:
        pi = existing
    else:
        pi = PlanItem(date=d, bucket=PlanBucket.Focus, notes=note)
        s.add(pi); s.flush()
    # attach
    for sid in subtask_ids:
        # avoid duplicate junctions
        exists = s.execute(
            select(PlanItemSubtask).where(PlanItemSubtask.plan_item_id == pi.id, PlanItemSubtask.subtask_id == sid)
        ).scalars().first()
        if not exists:
            s.add(PlanItemSubtask(plan_item_id=pi.id, subtask_id=sid))
    return pi

def process_evening_update(s: Session, payload: EveningPayload) -> EveningResult:
    d = payload.date
    today_blocks = _today_plan_blocks(s, d)

    # 1) Write or upsert daily_log for this date
    log = s.execute(select(DailyLog).where(DailyLog.date == d)).scalars().first()
    if not log:
        log = DailyLog(date=d)
        s.add(log); s.flush()

    # 2) Flatten blocked payload
    blocked_map = {b["id"]: (b.get("note") or "") for b in (payload.blocked or [])}

    # 3) Update subtask statuses + daily_log_items
    notes: List[str] = []
    updated_ids = set()

    def _mark(ids: Iterable[str], status: SubtaskStatus, note_text: Optional[str] = None):
        nonlocal updated_ids
        for sid in ids:
            st = s.get(Subtask, sid)
            if not st:
                continue
            st.status = status
            updated_ids.add(sid)
            s.add(DailyLogItem(log_id=log.id, subtask_id=sid, status=status, note=note_text))

    _mark(payload.completed or [], SubtaskStatus.done)
    _mark(payload.partial or [], SubtaskStatus.in_progress)
    for sid, n in blocked_map.items():
        _mark([sid], SubtaskStatus.blocked, n)

    # 4) Carry forward unfinished items (from today's plan, not marked done)
    #    Group by original block note (keeps batches intact)
    carry_by_note: Dict[str, List[str]] = defaultdict(list)
    for blk in today_blocks.values():
        note = blk["pi"].notes or "solo"
        for sid in blk["subtask_ids"]:
            if sid not in updated_ids or (sid in blocked_map or sid in (payload.partial or [])):
                # not touched, or explicitly partial/blocked → carry
                carry_by_note[note].append(sid)

    if carry_by_note:
        target_day = _next_workday(d)
        plan_delta: List[Dict] = []
        for note, ids in carry_by_note.items():
            pi = _append_to_plan_block(s, target_day, note, ids)
            plan_delta.append({
                "id": str(pi.id),
                "date": pi.date.isoformat(),
                "bucket": pi.bucket.value,
                "notes": pi.notes,
                "subtask_ids": list(ids)
            })
        notes.append(f"Carried {sum(len(v) for v in carry_by_note.values())} subtask(s) to {target_day.isoformat()}.")
    else:
        plan_delta = []

    s.commit()
    return EveningResult(plan_delta=plan_delta, notes=notes)
