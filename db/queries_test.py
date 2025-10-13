# db/queries.py
from __future__ import annotations

from typing import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import (
    make_engine,
    Base,
    Ticket, Subtask,
    TicketStatus, SubtaskStatus
)

# ---------- Helper functions ----------

def upsert_ticket(s: Session, t: Ticket) -> Ticket:
    """
    Insert or update a Ticket by primary key (id).
    Only updates core fields if it already exists.
    """
    existing = s.get(Ticket, t.id)
    if existing:
        # update selected fields
        for f in ("title", "description", "story_points", "labels",
                  "components", "tech", "due_date", "sprint", "status"):
            setattr(existing, f, getattr(t, f))
        return existing

    s.add(t)
    return t


def create_subtasks(s: Session, ticket_id: str, bullets: Iterable[dict]) -> list[Subtask]:
    """
    Create subtasks for a given ticket. Auto-assigns seq by appending to existing.
    bullets: list of dicts like {"text": "...", "tags": ["aws.lambda"], "est_hours": 1.5}
    """
    # current max seq for the ticket
    existing = s.execute(
        select(Subtask).where(Subtask.ticket_id == ticket_id).order_by(Subtask.seq.asc())
    ).scalars().all()

    next_seq = (existing[-1].seq + 1) if existing else 1
    created: list[Subtask] = []

    for i, b in enumerate(bullets, start=next_seq):
        st = Subtask(
            ticket_id=ticket_id,
            seq=i,
            text_sub=b["text"],
            tags=b.get("tags", []),
            est_hours=b.get("est_hours"),
        )
        s.add(st)
        created.append(st)

    return created


def find_tickets_by_tech_overlap(s: Session, any_of: Sequence[str]) -> list[Ticket]:
    """
    Use PostgreSQL array overlap operator (&&) to find tickets whose tech[] intersects with any_of.
    """
    stmt = select(Ticket).where(Ticket.tech.op("&&")(list(any_of)))
    return s.execute(stmt).scalars().all()


def mark_subtasks_status(s: Session, subtask_ids: Sequence[str], status: SubtaskStatus) -> int:
    """
    Bulk update subtask status. Returns number of rows updated.
    """
    result = s.execute(
        update(Subtask).where(Subtask.id.in_(list(subtask_ids))).values(status=status)
    )
    return result.rowcount or 0


# ---------- Validation script (run directly) ----------

@dataclass
class Bullet:
    text: str
    tags: list[str]
    est_hours: float | None = None


def _print_ticket(t: Ticket):
    print(f"- {t.id} | SP={t.story_points} | tech={t.tech} | status={t.status.value}")
    print(f"  title: {t.title}")


def _print_subtask(st: Subtask):
    print(f"  • {st.id}  [seq {st.seq}]  status={st.status.value}  tags={st.tags}")
    print(f"    {st.text_sub}")


def seed_if_missing(s: Session):
    """Seed minimal tickets if they aren't present yet."""
    if not s.get(Ticket, "TKT-101"):
        upsert_ticket(s, Ticket(
            id="TKT-101",
            title="Add DynamoDB TTL",
            description="Enable TTL on sessions table; apply IaC; verify expiry.",
            story_points=3,
            tech=["aws.dynamodb", "terraform"],
            status=TicketStatus.todo
        ))
    if not s.get(Ticket, "TKT-102"):
        upsert_ticket(s, Ticket(
            id="TKT-102",
            title="Lambda IAM least privilege",
            description="Tighten IAM for two Lambdas via Terraform; smoke test.",
            story_points=2,
            tech=["aws.lambda", "iam", "terraform"],
            status=TicketStatus.todo
        ))


def main():
    engine = make_engine(echo=False)
    # Ensure tables exist (normally Alembic handles this)
    Base.metadata.create_all(engine)

    with Session(engine) as s:
        # Seed tickets (idempotent)
        seed_if_missing(s)
        s.commit()

        print("== Tickets after upsert ==")
        for t in s.execute(select(Ticket).order_by(Ticket.id)).scalars():
            _print_ticket(t)

        # Create subtasks for TKT-101 (auto seq)
        print("\n== Creating subtasks for TKT-101 ==")
        bullets_101 = [
            Bullet("Terraform: add ttl attribute to sessions table", ["terraform", "aws.dynamodb"], 1.0).__dict__,
            Bullet("Apply plan in staging and verify expiry", ["terraform", "aws.dynamodb", "staging"], 1.5).__dict__,
            Bullet("Promote to prod during morning window", ["terraform", "aws.dynamodb", "prod"], 1.0).__dict__,
        ]
        create_subtasks(s, "TKT-101", bullets_101)

        # Create subtasks for TKT-102 (auto seq)
        print("\n== Creating subtasks for TKT-102 ==")
        bullets_102 = [
            Bullet("Write IAM policy for Lambda A (least privilege)", ["aws.lambda", "iam", "terraform"], 1.0).__dict__,
            Bullet("Attach policy & run smoke test", ["aws.lambda", "iam", "terraform", "staging"], 1.0).__dict__,
        ]
        create_subtasks(s, "TKT-102", bullets_102)

        s.commit()

        # Show subtasks for each ticket
        print("\n== Subtasks for each ticket ==")
        for t in s.execute(select(Ticket).order_by(Ticket.id)).scalars():
            print(f"\nTicket {t.id}:")
            subs = s.execute(
                select(Subtask).where(Subtask.ticket_id == t.id).order_by(Subtask.seq.asc())
            ).scalars().all()
            for st in subs:
                _print_subtask(st)

        # Try to violate unique (ticket_id, seq) to prove the constraint works
        print("\n== Attempting duplicate seq to trigger unique constraint (expected failure) ==")
        try:
            # Force seq=1 again on TKT-101
            dup = Subtask(ticket_id="TKT-101", seq=1, text_sub="(should fail)", tags=["test"])
            s.add(dup)
            s.commit()
        except IntegrityError as e:
            s.rollback()
            print("✅ Unique constraint enforced:", str(e.orig).split("\n")[0])

        # Query tickets by tech overlap (&&)
        print("\n== Tickets overlapping tech {'aws.lambda'} ==")
        lambda_tickets = find_tickets_by_tech_overlap(s, ["aws.lambda"])
        for t in lambda_tickets:
            _print_ticket(t)

        # Update some subtask statuses
        print("\n== Mark first subtask of each ticket as in_progress, then done ==")
        for t in s.execute(select(Ticket).order_by(Ticket.id)).scalars():
            first = s.execute(
                select(Subtask).where(Subtask.ticket_id == t.id).order_by(Subtask.seq.asc()).limit(1)
            ).scalars().first()
            if first:
                count = mark_subtasks_status(s, [str(first.id)], SubtaskStatus.in_progress)
                print(f"Updated {count} row(s) to in_progress for ticket {t.id}")
        s.commit()

        # Show updated statuses
        for t in s.execute(select(Ticket).order_by(Ticket.id)).scalars():
            first = s.execute(
                select(Subtask).where(Subtask.ticket_id == t.id).order_by(Subtask.seq.asc()).limit(1)
            ).scalars().first()
            if first:
                print(f"First subtask {first.id} of {t.id} now: {first.status.value}")

        # Finally mark them done
        ids_to_done = []
        for t in s.execute(select(Ticket).order_by(Ticket.id)).scalars():
            first = s.execute(
                select(Subtask).where(Subtask.ticket_id == t.id).order_by(Subtask.seq.asc()).limit(1)
            ).scalars().first()
            if first:
                ids_to_done.append(str(first.id))
        count = mark_subtasks_status(s, ids_to_done, SubtaskStatus.done)
        s.commit()
        print(f"\nMarked {count} first-subtask(s) as done.")
        for tid in ids_to_done:
            st = s.get(Subtask, tid)
            print(f"- {st.id} status = {st.status.value}")


if __name__ == "__main__":
    main()
