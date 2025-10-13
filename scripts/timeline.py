# scripts/timeline.py
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import SessionLocal
from db.models import PlanItem, PlanItemSubtask, Subtask, PlanBucket

# Simple color palette per bucket
COLORS = {
    PlanBucket.Focus: "#3b82f6",   # blue
    PlanBucket.Admin: "#facc15",   # yellow
    PlanBucket.Meeting: "#22c55e", # green
}

WORKDAYS = {0,1,2,3,4}  # Mon..Fri


def most_recent_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday==0


def iter_workdays(start: date, n_days: int) -> List[date]:
    out: List[date] = []
    cur = start
    while len(out) < n_days:
        if cur.weekday() in WORKDAYS:
            out.append(cur)
        cur += timedelta(days=1)
    return out


def fetch_plan_for_dates(s: Session, days: Iterable[date]) -> List[Tuple[PlanItem, List[Subtask]]]:
    rows: List[Tuple[PlanItem, List[Subtask]]] = []
    for d in days:
        items = (
            s.execute(select(PlanItem).where(PlanItem.date == d).order_by(PlanItem.bucket.desc()))
            .scalars().all()
        )
        for pi in items:
            links = s.execute(
                select(PlanItemSubtask).where(PlanItemSubtask.plan_item_id == pi.id)
            ).scalars().all()
            subtasks = []
            if links:
                subs = s.execute(
                    select(Subtask).where(Subtask.id.in_([l.subtask_id for l in links]))
                ).scalars().all()
                subtasks = sorted(subs, key=lambda st: (st.ticket_id, st.seq))
            rows.append((pi, subtasks))
    return rows


def _format_block_label(pi: PlanItem) -> str:
    note = (pi.notes or "").strip()
    if note and len(note) > 60:
        note = note[:57] + "…"
    return f"{pi.date.isoformat()} | {pi.bucket.value}: {note}"


def plot_range_timeline(start: date, days: int, outfile: str = "timeline.png") -> None:
    with SessionLocal() as s:  # type: Session
        day_list = iter_workdays(start, days)
        data = fetch_plan_for_dates(s, day_list)

        if not data:
            print(f"No plan_items across {day_list[0]} → {day_list[-1]}.")
            return

        # One row per plan item, ordered by date then bucket
        height = max(2.0, 0.9 * len(data))
        fig, ax = plt.subplots(figsize=(12, height))

        ylabels, ytick_pos = [], []
        y = 0

        for pi, subtasks in data:
            color = COLORS.get(pi.bucket, "#9ca3af")
            label = _format_block_label(pi)

            ylabels.append(label)
            ytick_pos.append(y)

            if subtasks:
                for i, st in enumerate(subtasks):
                    # Each subtask becomes a “segment”
                    ax.broken_barh([(i * 2, 1.8)], (y - 0.35, 0.7), facecolors=color)
                    ax.text(i * 2 + 0.08, y, f"{st.ticket_id}:{st.seq}", va="center", ha="left", fontsize=8, color="white")
            else:
                # Empty admin/meeting blocks show a faint placeholder
                ax.broken_barh([(0, 1.8)], (y - 0.35, 0.7), facecolors=color, alpha=0.35)
                ax.text(0.2, y, "(no subtasks)", va="center", ha="left", fontsize=8)

            y += 1

        ax.set_ylim(-1, y)
        # X-range: show up to 20 segments (expand if you routinely have more)
        ax.set_xlim(0, 20)
        ax.set_yticks(ytick_pos)
        ax.set_yticklabels(ylabels, fontsize=9)
        ax.set_xticks([])
        ax.set_title(f"Plan timeline: {day_list[0].isoformat()} → {day_list[-1].isoformat()}", fontsize=12, pad=10)
        plt.tight_layout()
        plt.savefig(outfile, dpi=150)
        plt.close(fig)
        print(f"Saved {outfile}")


def main():
    ap = argparse.ArgumentParser(description="Render plan timeline images")
    ap.add_argument("--mode", choices=["day", "week", "fortnight"], default="day")
    ap.add_argument("--start", help="YYYY-MM-DD (optional; week/fortnight default to most recent Monday)")
    ap.add_argument("--outfile", help="Output PNG file (optional)")
    args = ap.parse_args()

    today = date.today()
    start = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else None

    if args.mode == "day":
        start = start or today
        days = 1
        outfile = args.outfile or f"timeline_{start.isoformat()}.png"
    elif args.mode == "week":
        start = start or most_recent_monday(today)
        days = 5  # Mon–Fri
        outfile = args.outfile or f"timeline_week_{start.isoformat()}.png"
    else:  # fortnight
        start = start or most_recent_monday(today)
        days = 10  # two work weeks
        outfile = args.outfile or f"timeline_fortnight_{start.isoformat()}.png"

    plot_range_timeline(start, days, outfile)


if __name__ == "__main__":
    main()
