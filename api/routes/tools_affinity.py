# api/routes/tools_affinity.py
from __future__ import annotations
from flask import request
from flask_restx import Namespace, Resource, fields
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from api.deps import SessionLocal
from db.models import Subtask, AffinityGroup, AffinityMember, SubtaskStatus
from logic.affinity import compute_affinity_groups, SubtaskLike

ns = Namespace("affinity", description="Compute & list affinity groups for batching work")

compute_in = ns.model("ComputeIn", {
    "status": fields.List(fields.String, required=False, description="Filter subtasks by status (default: todo,in_progress)"),
    "ticket_ids": fields.List(fields.String, required=False, description="Optional subset of tickets"),
    "clear_existing": fields.Boolean(required=False, default=True, description="Clear all existing groups before writing new"),
})

group_out = ns.model("AffinityGroupOut", {
    "key": fields.String,
    "members": fields.List(fields.String),
    "rationale": fields.String,
})

@ns.route("/compute")
class Compute(Resource):
    @ns.expect(compute_in)
    @ns.marshal_list_with(group_out)
    def post(self):
        body = request.get_json(force=True) or {}
        statuses = body.get("status") or ["todo", "in_progress"]
        ticket_ids = body.get("ticket_ids")
        clear_existing = bool(body.get("clear_existing", True))

        with SessionLocal() as s:  # type: Session
            # 1) Load candidate subtasks
            stmt = select(Subtask)
            if ticket_ids:
                stmt = stmt.where(Subtask.ticket_id.in_(ticket_ids))
            if statuses:
                stmt = stmt.where(Subtask.status.in_([SubtaskStatus(x) for x in statuses]))

            candidates = s.execute(stmt).scalars().all()
            as_like = [SubtaskLike(id=str(st.id), ticket_id=st.ticket_id, tags=st.tags or [], text_sub=st.text_sub)
                       for st in candidates]

            # 2) Compute groups in memory
            groups = compute_affinity_groups(as_like)

            # 3) Write to DB (clear or selective rewrite)
            if clear_existing:
                s.execute(delete(AffinityMember))
                s.execute(delete(AffinityGroup))
                s.flush()

            # Insert groups + members
            created = []
            for g in groups:
                ag = AffinityGroup(key=g.key, rationale=g.rationale)
                s.add(ag)
                s.flush()  # get ag.id
                for sid in g.member_ids:
                    s.add(AffinityMember(group_id=ag.id, subtask_id=sid))
                created.append({"key": g.key, "members": g.member_ids, "rationale": g.rationale})

            s.commit()
            return created

list_out = ns.model("AffinityGroupListItem", {
    "id": fields.String,
    "key": fields.String,
    "rationale": fields.String,
    "members": fields.List(fields.String),
})

@ns.route("/list")
class List(Resource):
    @ns.marshal_list_with(list_out)
    def get(self):
        with SessionLocal() as s:
            groups = s.execute(select(AffinityGroup)).scalars().all()
            out = []
            for g in groups:
                # load members
                m = s.execute(select(AffinityMember).where(AffinityMember.group_id == g.id)).scalars().all()
                out.append({
                    "id": str(g.id),
                    "key": g.key,
                    "rationale": g.rationale,
                    "members": [str(mm.subtask_id) for mm in m]
                })
            return out
