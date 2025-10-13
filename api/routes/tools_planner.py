# api/routes/tools_planner.py
from __future__ import annotations
from datetime import date, datetime
from flask import request
from flask_restx import Namespace, Resource, fields
from sqlalchemy.orm import Session
from sqlalchemy import select

from api.deps import SessionLocal
from db.models import PlanItem, PlanItemSubtask
from logic.plan_builder import build_plan, persist_plan, PlanConstraints

ns = Namespace("planner", description="Two-week planner")

make_in = ns.model("MakePlanIn", {
    "start_date": fields.String(required=False, description="YYYY-MM-DD; default: today"),
    "days": fields.Integer(required=False, default=10),
    "constraints": fields.Raw(required=False, description="max_contexts_per_day, max_focus_blocks_per_day, buffer_ratio"),
    "clear_existing_from_start": fields.Boolean(required=False, default=True),
    "ticket_ids": fields.List(fields.String, required=False, description="Optional subset of tickets"),
})

plan_block = ns.model("PlannedBlock", {
    "date": fields.String,
    "bucket": fields.String,
    "note": fields.String,
    "subtask_ids": fields.List(fields.String),
})

@ns.route("/make_two_week_plan")
class MakePlan(Resource):
    @ns.expect(make_in)
    @ns.marshal_list_with(plan_block)
    def post(self):
        body = request.get_json(force=True) or {}
        start_s = body.get("start_date")
        days = int(body.get("days") or 10)
        clear_existing = bool(body.get("clear_existing_from_start", True))
        ticket_ids = body.get("ticket_ids")

        if start_s:
            start = datetime.strptime(start_s, "%Y-%m-%d").date()
        else:
            start = date.today()

        c = body.get("constraints") or {}
        cons = PlanConstraints(
            max_contexts_per_day=int(c.get("max_contexts_per_day", 2)),
            max_focus_blocks_per_day=int(c.get("max_focus_blocks_per_day", 4)),
            buffer_ratio=float(c.get("buffer_ratio", 0.20)),
            workdays=(0,1,2,3,4)
        )

        with SessionLocal() as s:  # type: Session
            planned = build_plan(
                s=s, start=start, days=days,
                constraints=cons,
                clear_existing_from_start=clear_existing,
                ticket_subset=ticket_ids
            )
            # persist to DB
            from logic.plan_builder import persist_plan
            persist_plan(s, planned)

            # format for response (read back what we wrote)
            out = []
            for blk in planned:
                out.append({
                    "date": blk.date.isoformat(),
                    "bucket": blk.bucket.value,
                    "note": blk.note,
                    "subtask_ids": blk.subtask_ids
                })
            return out

list_out = ns.model("PlanItemOut", {
    "id": fields.String,
    "date": fields.String,
    "bucket": fields.String,
    "notes": fields.String,
    "subtask_ids": fields.List(fields.String),
})

@ns.route("/list")
class ListPlan(Resource):
    @ns.marshal_list_with(list_out)
    def get(self):
        with SessionLocal() as s:
            items = s.execute(select(PlanItem).order_by(PlanItem.date)).scalars().all()
            out = []
            for pi in items:
                # fetch linked subtasks
                links = s.execute(
                    select(PlanItemSubtask).where(PlanItemSubtask.plan_item_id == pi.id)
                ).scalars().all()
                out.append({
                    "id": str(pi.id),
                    "date": pi.date.isoformat(),
                    "bucket": pi.bucket.value,
                    "notes": pi.notes,
                    "subtask_ids": [str(l.subtask_id) for l in links]
                })
            return out
