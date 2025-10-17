"""Utility script to drop and recreate all Sprint Planner tables."""

import argparse
import sys

from sqlalchemy import text

from db.models import Base, make_engine


ENUM_TYPES = (
    "ticket_status",
    "subtask_status",
    "plan_bucket",
)


def reset_database(*, skip_confirmation: bool = False, echo: bool = False) -> None:
    """Drop every table (and enum type) then recreate the schema."""
    if not skip_confirmation:
        try:
            answer = input(
                "This will permanently delete all Sprint Planner data. Continue? [y/N]: "
            )
        except KeyboardInterrupt:
            print("\nAborted.")
            return
        if answer.lower() not in {"y", "yes"}:
            print("Aborted.")
            return

    engine = make_engine(echo=echo)
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
        for enum_name in ENUM_TYPES:
            conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
        Base.metadata.create_all(bind=conn)

    print("Database reset complete.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drop and recreate the Sprint Planner database schema."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    parser.add_argument(
        "--echo",
        action="store_true",
        help="Log SQL emitted while resetting.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    reset_database(skip_confirmation=args.force, echo=args.echo)


if __name__ == "__main__":
    main(sys.argv[1:])
