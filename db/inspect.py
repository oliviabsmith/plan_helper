# db/inspect.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models import make_engine, Ticket, Subtask

def show_current():
    engine = make_engine()
    with Session(engine) as s:
        print("\n=== Tickets ===")
        tickets = s.execute(select(Ticket).order_by(Ticket.id)).scalars().all()
        if not tickets:
            print("(none)")
        for t in tickets:
            print(f"- {t.id} | {t.title} | SP={t.story_points} | status={t.status.value}")
            print(f"  tech={t.tech} | due={t.due_date}")

            # subtasks for this ticket
            subs = s.execute(
                select(Subtask)
                .where(Subtask.ticket_id == t.id)
                .order_by(Subtask.seq)
            ).scalars().all()
            if subs:
                for st in subs:
                    print(f"    • [{st.seq}] {st.text_sub}  ({st.status.value}) tags={st.tags}")
            else:
                print("    (no subtasks yet)")

if __name__ == "__main__":
    show_current()
