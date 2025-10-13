from db.models import Base, make_engine, Ticket, Subtask, TicketStatus
from sqlalchemy.orm import Session

def create_all():
    engine = make_engine()
    Base.metadata.create_all(engine)
    print("Tables created.")

def seed_basic():
    engine = make_engine()
    with Session(engine) as s:
        t1 = Ticket(
            id="TKT-101",
            title="Add DynamoDB TTL",
            description="Enable TTL for sessions table; update IaC; verify expiry.",
            story_points=3,
            tech=["aws.dynamodb","terraform"],
            status=TicketStatus.todo
        )
        t2 = Ticket(
            id="TKT-102",
            title="Lambda IAM least privilege",
            description="Tighten IAM for two Lambdas; update Terraform; smoke test.",
            story_points=2,
            tech=["aws.lambda","iam","terraform"],
        )
        s.add_all([t1, t2])
        s.commit()
    print("Seeded tickets.")

if __name__ == "__main__":
    create_all()
    seed_basic()
