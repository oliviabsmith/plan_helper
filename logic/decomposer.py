from db.models import Ticket

def sp_to_count(sp: int) -> int:
    if sp <= 1: return 1
    if sp == 2: return 2
    if sp == 3: return 3
    if sp >= 5: return 5
    return 3

def generate_bullets(ticket: Ticket) -> list[dict]:
    n = sp_to_count(ticket.story_points)
    base = ticket.title.strip()
    tags = (ticket.tech or [])[:]
    templates = [
        f"Scope & prep: confirm requirements for '{base}'",
        f"Implement core change for '{base}'",
        f"Validate in staging: tests/runbook for '{base}'",
        f"Prepare prod change window: checklist for '{base}'",
        f"Deploy & verify in prod: metrics/logs for '{base}'",
    ]
    out = []
    for i in range(n):
        out.append({"text_sub": templates[i], "tags": tags, "est_hours": 1.0 if i == 0 else 1.5})
    return out
