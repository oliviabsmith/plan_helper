# api/routes/tools_reports.py
from __future__ import annotations
from datetime import date, datetime
from flask import request
from flask_restx import Namespace, Resource, fields
from sqlalchemy.orm import Session

from api.deps import SessionLocal
from logic.morning_report import make_morning_report

ns = Namespace("reports", description="Daily reports (morning/evening)")

morning_in = ns.model("MorningIn", {
    "date": fields.String(required=False, description="YYYY-MM-DD; default: today (server tz)"),
    "narrative": fields.Raw(
        required=False,
        description="Set to true to include an LLM narrative or provide {enabled: bool, llm_options: {...}}."
    ),
})

checklist_item = ns.model("ChecklistItem", {
    "subtask_id": fields.String,
    "ticket_id": fields.String,
    "seq": fields.Integer,
    "text_sub": fields.String,
    "why_now": fields.String,
    "tags": fields.List(fields.String),
})

batch_out = ns.model("BatchOut", {
    "note": fields.String,
    "plan_item_id": fields.String,
    "members": fields.List(fields.String),
    "rationale": fields.String,
})

memory_item = ns.model("MemoryItem", {
    "id": fields.String,
    "topic": fields.String,
    "text": fields.String,
    "pinned": fields.Boolean,
    "created_at": fields.String,
})

narrative_out = ns.model("MorningNarrative", {
    "text": fields.String,
    "context_tags": fields.List(fields.String),
    "memory_refs": fields.List(fields.String),
    "error": fields.String,
})

morning_out = ns.model("MorningReport", {
    "date": fields.String,
    "checklist": fields.List(fields.Nested(checklist_item)),
    "batches": fields.List(fields.Nested(batch_out)),
    "risks": fields.List(fields.String),
    "memory_top3": fields.List(fields.Nested(memory_item)),
    "narrative": fields.Nested(narrative_out, allow_null=True),
})

@ns.route("/morning")
class Morning(Resource):
    @ns.expect(morning_in)
    @ns.marshal_with(morning_out)
    def post(self):
        body = request.get_json(force=True) or {}
        ds = body.get("date")
        if ds:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        else:
            d = date.today()  # if you need Europe/Madrid specifically, adjust at app level

        narrative_cfg = body.get("narrative")
        include_narrative = False
        narrative_options = None
        if isinstance(narrative_cfg, dict):
            include_narrative = narrative_cfg.get("enabled", True)
            narrative_options = narrative_cfg.get("llm_options") or narrative_cfg.get("options")
        elif isinstance(narrative_cfg, bool):
            include_narrative = narrative_cfg
        elif isinstance(narrative_cfg, str):
            include_narrative = narrative_cfg.strip().lower() not in {"", "false", "0", "no"}
        elif narrative_cfg is not None:
            include_narrative = bool(narrative_cfg)

        with SessionLocal() as s:  # type: Session
            rpt = make_morning_report(
                s,
                d,
                include_narrative=include_narrative,
                narrative_options=narrative_options,
            )

            # Serialize dataclasses to dict
            return {
                "date": rpt.date,
                "checklist": [
                    {
                        "subtask_id": x.subtask_id,
                        "ticket_id": x.ticket_id,
                        "seq": x.seq,
                        "text_sub": x.text_sub,
                        "why_now": x.why_now,
                        "tags": x.tags,
                    } for x in rpt.checklist
                ],
                "batches": [
                    {
                        "note": b.note,
                        "plan_item_id": b.plan_item_id,
                        "members": b.members,
                        "rationale": b.rationale
                    } for b in rpt.batches
                ],
                "risks": rpt.risks,
                "memory_top3": rpt.memory_top3,
                "narrative": (
                    {
                        "text": rpt.narrative.text,
                        "context_tags": rpt.narrative.context_tags,
                        "memory_refs": rpt.narrative.memory_refs,
                        "error": rpt.narrative.error,
                    }
                    if rpt.narrative else None
                ),
            }

# api/routes/tools_reports.py  (append)

evening_in = ns.model("EveningIn", {
    "date": fields.String(required=False, description="YYYY-MM-DD; default: today"),
    "completed": fields.List(fields.String, required=False, description="subtask ids"),
    "partial": fields.List(fields.String, required=False, description="subtask ids"),
    "blocked": fields.List(fields.Raw, required=False, description='[{"id": subtask_id, "note": "..."}]')
})

evening_out = ns.model("EveningOut", {
    "plan_delta": fields.List(fields.Nested(ns.model("PlanDelta", {
        "id": fields.String, "date": fields.String, "bucket": fields.String,
        "notes": fields.String, "subtask_ids": fields.List(fields.String)
    }))),
    "notes": fields.List(fields.String),
})

@ns.route("/evening")
class Evening(Resource):
    @ns.expect(evening_in)
    @ns.marshal_with(evening_out)
    def post(self):
        from datetime import date, datetime
        from logic.evening_update import process_evening_update, EveningPayload

        body = request.get_json(force=True) or {}
        ds = body.get("date")
        if ds:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
        else:
            d = date.today()

        payload = EveningPayload(
            date=d,
            completed=body.get("completed") or [],
            partial=body.get("partial") or [],
            blocked=body.get("blocked") or [],
        )

        with SessionLocal() as s:
            result = process_evening_update(s, payload)
            return {
                "plan_delta": result.plan_delta,
                "notes": result.notes
            }
