from flask import request
from flask_restx import Namespace, Resource, fields
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import SessionLocal
from db.models import Ticket, Subtask, SubtaskStatus
from db.queries import mark_subtasks_status
from logic.decomposer import generate_bullets
from logic.llm_client import LLMClientError

ns = Namespace("subtasks", description="Create/list subtasks")

create_in = ns.model("CreateIn", {
    "ticket_id": fields.String(required=True),
    "bullets": fields.List(fields.Raw, required=False, description="Optional explicit bullets [{text_sub,tags,est_hours}]"),
    "mode": fields.String(required=False, default="append", description="append|replace"),
    "llm_options": fields.Raw(
        required=False,
        description="Optional LLM overrides such as tone, extra_context, model, or temperature. Requires OPENAI_API_KEY."
    ),
})

subtask_out = ns.model("SubtaskOut", {
    "id": fields.String, "ticket_id": fields.String, "seq": fields.Integer,
    "text_sub": fields.String, "tags": fields.List(fields.String),
    "status": fields.String, "est_hours": fields.Float
})

list_in = ns.model("ListIn", {
    "ticket_id": fields.String(required=False),
    "status": fields.List(fields.String, required=False)
})

mark_status_in = ns.model(
    "MarkStatusIn",
    {
        "subtask_ids": fields.List(fields.String, required=True, description="IDs to update"),
        "status": fields.String(required=True, description="New status value"),
    },
)

mark_status_out = ns.model(
    "MarkStatusOut",
    {
        "updated": fields.Integer,
    },
)

@ns.route("/create_for_ticket")
class CreateForTicket(Resource):
    @ns.expect(create_in)
    @ns.marshal_list_with(subtask_out)
    def post(self):
        """Create subtasks for a ticket. Requires OPENAI_API_KEY for LLM generation."""

        body = request.get_json(force=True)
        tid = body["ticket_id"]
        bullets = body.get("bullets")
        mode = (body.get("mode") or "append").lower()
        llm_options = body.get("llm_options") or {}

        with SessionLocal() as s:  # type: Session
            t = s.get(Ticket, tid)
            if not t:
                return [], 404

            # replace mode: delete existing subtasks for this ticket
            if mode == "replace":
                s.query(Subtask).filter(Subtask.ticket_id == tid).delete()

            # figure out next seq
            existing = s.execute(
                select(Subtask).where(Subtask.ticket_id == tid).order_by(Subtask.seq.asc())
            ).scalars().all()
            next_seq = (existing[-1].seq + 1) if existing else 1

            # generate bullets if not provided
            if not bullets:
                try:
                    bullets = generate_bullets(t, llm_options=llm_options)
                except LLMClientError as exc:
                    ns.abort(502, message=str(exc))
                except Exception as exc:  # pragma: no cover - guardrail
                    ns.abort(500, message=f"Unexpected error generating subtasks: {exc}")

            created = []
            for i, b in enumerate(bullets, start=next_seq):
                st = Subtask(
                    ticket_id=tid,
                    seq=i,
                    text_sub=b["text_sub"],
                    tags=b.get("tags", []),
                    est_hours=b.get("est_hours"),
                    status=SubtaskStatus.todo
                )
                s.add(st)
                created.append(st)
            s.commit()

            return [
                {
                    "id": str(st.id), "ticket_id": st.ticket_id, "seq": st.seq,
                    "text_sub": st.text_sub, "tags": st.tags,
                    "status": st.status.value, "est_hours": float(st.est_hours) if st.est_hours is not None else None
                } for st in created
            ]

@ns.route("/list")
class List(Resource):
    @ns.expect(list_in)
    @ns.marshal_list_with(subtask_out)
    def post(self):
        body = request.get_json(force=True) or {}
        tid = body.get("ticket_id")
        statuses = body.get("status")

        with SessionLocal() as s:
            stmt = select(Subtask)
            if tid:
                stmt = stmt.where(Subtask.ticket_id == tid)
            if statuses:
                stmt = stmt.where(Subtask.status.in_([SubtaskStatus(x) for x in statuses]))
            subs = s.execute(stmt.order_by(Subtask.ticket_id, Subtask.seq)).scalars().all()
            return [
                {
                    "id": str(st.id), "ticket_id": st.ticket_id, "seq": st.seq,
                    "text_sub": st.text_sub, "tags": st.tags,
                    "status": st.status.value, "est_hours": float(st.est_hours) if st.est_hours is not None else None
                } for st in subs
            ]


@ns.route("/mark_status")
class MarkStatus(Resource):
    @ns.expect(mark_status_in)
    @ns.marshal_with(mark_status_out)
    def post(self):
        body = request.get_json(force=True) or {}
        ids = body.get("subtask_ids") or []
        status_value = body.get("status")

        if not status_value:
            ns.abort(400, message="status is required")

        try:
            status = SubtaskStatus(status_value)
        except ValueError:
            ns.abort(400, message=f"Unknown subtask status: {status_value}")

        if not ids:
            return {"updated": 0}

        with SessionLocal() as s:
            updated = mark_subtasks_status(s, ids, status)
            s.commit()
            return {"updated": updated}
