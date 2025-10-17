from flask import request
from flask_restx import Namespace, Resource, fields
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import SessionLocal
from db.models import Ticket, TicketStatus

#ns = Namespace("ticket_store", description="Manual upload & search tickets")
ns = Namespace("tickets", description="Manual upload & search tickets", path="")


upload_in = ns.model("UploadIn", {
    "tickets": fields.List(fields.Raw, required=True, description="Array of ticket dicts")
})

upload_out = ns.model("UploadOut", {
    "inserted": fields.Integer,
    "updated": fields.Integer,
    "warnings": fields.List(fields.String),
})

search_in = ns.model("SearchIn", {
    "ids": fields.List(fields.String, required=False),
    "status": fields.List(fields.String, required=False),
    "text": fields.String(required=False),
    "tech": fields.List(fields.String, required=False),
})

ticket_out = ns.model("Ticket", {
    "id": fields.String, "title": fields.String, "description": fields.String,
    "story_points": fields.Integer, "labels": fields.List(fields.String),
    "components": fields.List(fields.String), "tech": fields.List(fields.String),
    "due_date": fields.String, "sprint": fields.String, "status": fields.String
})

def _normalize_tech(val):
    if not val: return []
    return [str(t).strip().lower().replace(" ", ".") for t in val]

@ns.route("/load_manual")
class LoadManual(Resource):
    @ns.expect(upload_in)
    @ns.marshal_with(upload_out)
    def post(self):
        payload = request.get_json(force=True)
        rows = payload.get("tickets", [])
        warnings = []
        inserted = 0
        updated = 0

        with SessionLocal() as s:  # type: Session
            for r in rows:
                tid = str(r.get("id") or "").strip()
                if not tid:
                    warnings.append("Row missing id; skipped.")
                    continue
                sp = r.get("story_points")
                if sp is None:
                    warnings.append(f"{tid}: missing story_points")
                t = s.get(Ticket, tid)
                data = dict(
                    title=r.get("title","").strip(),
                    description=r.get("description","").strip(),
                    story_points=int(sp or 0),
                    labels=r.get("labels") or [],
                    components=r.get("components") or [],
                    tech=_normalize_tech(r.get("tech")),
                    due_date=r.get("due_date"),
                    sprint=r.get("sprint"),
                    status=TicketStatus(r.get("status","todo")),
                )
                if t:
                    for k,v in data.items():
                        setattr(t, k, v)
                    updated += 1
                else:
                    s.add(Ticket(id=tid, **data))
                    inserted += 1
            s.commit()

        return {"inserted": inserted, "updated": updated, "warnings": warnings}

@ns.route("/search")
class Search(Resource):
    @ns.expect(search_in)
    @ns.marshal_list_with(ticket_out)
    def post(self):
        q = request.get_json(force=True) or {}
        ids = q.get("ids")
        status = q.get("status")
        text = q.get("text")
        tech = q.get("tech")

        with SessionLocal() as s:
            stmt = select(Ticket)
            if ids:
                stmt = stmt.where(Ticket.id.in_(ids))
            if status:
                stmt = stmt.where(Ticket.status.in_([TicketStatus(x) for x in status]))
            if text:
                like = f"%{text}%"
                from sqlalchemy import or_
                stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))
            if tech:
                stmt = stmt.where(Ticket.tech.op("&&")(tech))
            tickets = s.execute(stmt.order_by(Ticket.id)).scalars().all()
            return [
                {
                    "id": t.id, "title": t.title, "description": t.description,
                    "story_points": t.story_points, "labels": t.labels,
                    "components": t.components, "tech": t.tech,
                    "due_date": str(t.due_date) if t.due_date else None,
                    "sprint": t.sprint, "status": t.status.value
                } for t in tickets
            ]
