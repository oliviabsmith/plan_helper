import argparse, json, sys
from sqlalchemy.orm import Session
from sqlalchemy import select

from db.models import Ticket, TicketStatus
from api.deps import SessionLocal
from logic.decomposer import generate_bullets
from db.models import Subtask, SubtaskStatus

def cmd_load(path: str):
    data = json.load(open(path)) if path.endswith(".json") else None
    if data is None:
        print("Only JSON supported in this quick CLI. Use API for CSV.", file=sys.stderr); return
    rows = data["tickets"]
    ins, upd = 0, 0
    with SessionLocal() as s:
        for r in rows:
            tid = r["id"].strip()
            t = s.get(Ticket, tid)
            payload = dict(
                title=r["title"], description=r.get("description",""),
                story_points=int(r.get("story_points") or 0),
                labels=r.get("labels") or [], components=r.get("components") or [],
                tech=[x.lower().replace(" ",".") for x in (r.get("tech") or [])],
                sprint=r.get("sprint"),
                status=TicketStatus(r.get("status","todo")),
            )
            if t:
                for k,v in payload.items(): setattr(t, k, v); upd += 1
            else:
                s.add(Ticket(id=tid, **payload)); ins += 1
        s.commit()
    print(f"Loaded tickets: inserted={ins}, updated={upd}")

def cmd_decompose(ticket_id: str, mode: str):
    with SessionLocal() as s:  # type: Session
        t = s.get(Ticket, ticket_id)
        if not t: print("Ticket not found"); return
        if mode == "replace":
            s.query(Subtask).filter(Subtask.ticket_id == ticket_id).delete()
            next_seq = 1
        else:
            existing = s.execute(select(Subtask).where(Subtask.ticket_id == ticket_id).order_by(Subtask.seq)).scalars().all()
            next_seq = existing[-1].seq + 1 if existing else 1
        bullets = generate_bullets(t)
        for i, b in enumerate(bullets, start=next_seq):
            s.add(Subtask(ticket_id=ticket_id, seq=i, text_sub=b["text_sub"], tags=b.get("tags", []),
                          est_hours=b.get("est_hours"), status=SubtaskStatus.todo))
        s.commit()
        print(f"Created {len(bullets)} subtasks for {ticket_id} (mode={mode})")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("load", help="Load tickets from JSON")
    p1.add_argument("--path", required=True)

    p2 = sub.add_parser("decompose", help="Generate subtasks for a ticket")
    p2.add_argument("--ticket-id", required=True)
    p2.add_argument("--mode", choices=["append","replace"], default="append")

    args = ap.parse_args()
    if args.cmd == "load":
        cmd_load(args.path)
    elif args.cmd == "decompose":
        cmd_decompose(args.ticket_id, args.mode)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
