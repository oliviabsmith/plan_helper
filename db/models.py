from __future__ import annotations
import os
from datetime import datetime, date
from typing import List, Optional
from enum import Enum

from sqlalchemy import (
    create_engine, MetaData, Enum as PgEnum, CheckConstraint,
    func, text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from sqlalchemy.dialects.postgresql import ARRAY, TIMESTAMP, UUID, TEXT, DATE
from sqlalchemy import String, Integer, Numeric, Boolean
import uuid

# --- Engine helper (read DATABASE_URL from env) ---
def make_engine(echo: bool = False):
    url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/sprint_planner")
    return create_engine(url, echo=echo, future=True)

# --- Base ---
class Base(DeclarativeBase):
    metadata = MetaData()

# --- Enums (mirror Postgres enums) ---
class TicketStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"

class SubtaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"

class PlanBucket(str, Enum):
    Focus = "Focus"
    Admin = "Admin"
    Meeting = "Meeting"

# --- Models ---
class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(TEXT, nullable=False)
    description: Mapped[str] = mapped_column(TEXT, nullable=False)
    story_points: Mapped[int] = mapped_column(Integer, nullable=False)
    labels: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, server_default=text("'{}'"))
    components: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, server_default=text("'{}'"))
    tech: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, server_default=text("'{}'"))
    due_date: Mapped[Optional[date]] = mapped_column(DATE)
    sprint: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[TicketStatus] = mapped_column(PgEnum(TicketStatus, name="ticket_status"), default=TicketStatus.todo, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    subtasks: Mapped[List["Subtask"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("story_points >= 0", name="ck_ticket_sp_nonneg"),
    )

class Subtask(Base):
    __tablename__ = "subtasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    text_sub: Mapped[str] = mapped_column(TEXT, nullable=False)
    est_hours: Mapped[Optional[float]] = mapped_column(Numeric(6,2))
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, server_default=text("'{}'"))
    status: Mapped[SubtaskStatus] = mapped_column(PgEnum(SubtaskStatus, name="subtask_status"), default=SubtaskStatus.todo, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    ticket: Mapped["Ticket"] = relationship(back_populates="subtasks")
    plan_items: Mapped[List["PlanItem"]] = relationship(secondary="plan_item_subtasks", back_populates="subtasks")
    affinity_groups: Mapped[List["AffinityGroup"]] = relationship(secondary="affinity_members", back_populates="subtasks")

    __table_args__ = (
        UniqueConstraint("ticket_id", "seq", name="uq_subtasks_ticket_seq"),
    )

class AffinityGroup(Base):
    __tablename__ = "affinity_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(TEXT, nullable=False)
    rationale: Mapped[str] = mapped_column(TEXT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    subtasks: Mapped[List["Subtask"]] = relationship(secondary="affinity_members", back_populates="affinity_groups")

class AffinityMember(Base):
    __tablename__ = "affinity_members"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("affinity_groups.id", ondelete="CASCADE"), primary_key=True)
    subtask_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subtasks.id", ondelete="CASCADE"), primary_key=True)

class PlanItem(Base):
    __tablename__ = "plan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(DATE, nullable=False)
    bucket: Mapped[PlanBucket] = mapped_column(PgEnum(PlanBucket, name="plan_bucket"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(TEXT)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    subtasks: Mapped[List["Subtask"]] = relationship(secondary="plan_item_subtasks", back_populates="plan_items")

class PlanItemSubtask(Base):
    __tablename__ = "plan_item_subtasks"

    plan_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_items.id", ondelete="CASCADE"), primary_key=True)
    subtask_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subtasks.id", ondelete="CASCADE"), primary_key=True)

class DailyLog(Base):
    __tablename__ = "daily_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(DATE, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    items: Mapped[List["DailyLogItem"]] = relationship(back_populates="log", cascade="all, delete-orphan")

class DailyLogItem(Base):
    __tablename__ = "daily_log_items"

    log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_logs.id", ondelete="CASCADE"), primary_key=True)
    subtask_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subtasks.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[SubtaskStatus] = mapped_column(PgEnum(SubtaskStatus, name="subtask_status"), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(TEXT)

    log: Mapped["DailyLog"] = relationship(back_populates="items")
    subtask: Mapped["Subtask"] = relationship()

class MemorySnippet(Base):
    __tablename__ = "memory_snippets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic: Mapped[str] = mapped_column(TEXT, nullable=False)
    text: Mapped[str] = mapped_column(TEXT, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(TEXT)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # store as vector column; SQLAlchemy doesn't have a native type, so keep as TEXT/ARRAY or bind literal SQL.
    # For now we’ll keep it nullable and set via raw SQL on insert/update when you add embeddings:
    # embedding VECTOR(384)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
