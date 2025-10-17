from typing import Iterable
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from db.models import Ticket, Subtask, SubtaskStatus

def upsert_ticket(s: Session, t: Ticket):
    existing = s.get(Ticket, t.id)
    if existing:
        for f in ("title","description","story_points","labels","components","tech","due_date","sprint","status"):
            setattr(existing, f, getattr(t, f))
        return existing
    s.add(t)
    return t

def create_subtasks(s: Session, ticket_id: str, bullets: Iterable[dict]):
    # bullets: [{"text": "...", "tags": ["aws.lambda"], "est_hours": 1.5}, ...]
    existing = s.execute(select(Subtask).where(Subtask.ticket_id == ticket_id)).scalars().all()
    seq_start = len(existing) + 1
    created = []
    for i, b in enumerate(bullets, start=seq_start):
        st = Subtask(ticket_id=ticket_id, seq=i, text=b["text"], tags=b.get("tags", []), est_hours=b.get("est_hours"))
        s.add(st); created.append(st)
    return created

def mark_subtasks_status(s: Session, subtask_ids: list, status: SubtaskStatus) -> int:
    result = s.execute(update(Subtask).where(Subtask.id.in_(subtask_ids)).values(status=status))
    return int(result.rowcount or 0)

def find_tickets_by_tech(s: Session, tech_any: list[str]):
    stmt = select(Ticket).where(Ticket.tech.op("&&")(tech_any))  # overlap operator
    return s.execute(stmt).scalars().all()
