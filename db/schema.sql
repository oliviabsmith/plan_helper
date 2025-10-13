-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

-- Enums
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ticket_status') THEN
    CREATE TYPE ticket_status AS ENUM ('todo','in_progress','blocked','done');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subtask_status') THEN
    CREATE TYPE subtask_status AS ENUM ('todo','in_progress','blocked','done');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan_bucket') THEN
    CREATE TYPE plan_bucket AS ENUM ('Focus','Admin','Meeting');
  END IF;
END $$;

-- Tickets
CREATE TABLE IF NOT EXISTS tickets (
  id             TEXT PRIMARY KEY,           -- e.g., "TKT-101"
  title          TEXT NOT NULL,
  description    TEXT NOT NULL,
  story_points   INT NOT NULL CHECK (story_points >= 0),
  labels         TEXT[] NOT NULL DEFAULT '{}',
  components     TEXT[] NOT NULL DEFAULT '{}',
  tech           TEXT[] NOT NULL DEFAULT '{}',    -- normalized tags e.g., {aws.lambda,terraform}
  due_date       DATE,
  sprint         TEXT,
  status         ticket_status NOT NULL DEFAULT 'todo',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Subtasks
CREATE TABLE IF NOT EXISTS subtasks (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id      TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  seq            INT NOT NULL,                       -- display order within ticket
  text           TEXT NOT NULL,
  est_hours      NUMERIC(6,2),
  tags           TEXT[] NOT NULL DEFAULT '{}',
  status         subtask_status NOT NULL DEFAULT 'todo',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT subtasks_unique_seq_per_ticket UNIQUE(ticket_id, seq)
);

-- Affinity groups + membership
CREATE TABLE IF NOT EXISTS affinity_groups (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key        TEXT NOT NULL, -- e.g., "aws.lambda+terraform:staging"
  rationale  TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS affinity_members (
  group_id   UUID NOT NULL REFERENCES affinity_groups(id) ON DELETE CASCADE,
  subtask_id UUID NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,
  PRIMARY KEY (group_id, subtask_id)
);

-- Plan items (2-week plan) + junction to subtasks
CREATE TABLE IF NOT EXISTS plan_items (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE NOT NULL,
  bucket     plan_bucket NOT NULL,
  notes      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plan_item_subtasks (
  plan_item_id UUID NOT NULL REFERENCES plan_items(id) ON DELETE CASCADE,
  subtask_id   UUID NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,
  PRIMARY KEY (plan_item_id, subtask_id)
);

-- Daily logs (evening updates)
CREATE TABLE IF NOT EXISTS daily_logs (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- status per subtask for a given day
CREATE TABLE IF NOT EXISTS daily_log_items (
  log_id     UUID NOT NULL REFERENCES daily_logs(id) ON DELETE CASCADE,
  subtask_id UUID NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,
  status     subtask_status NOT NULL,
  note       TEXT,
  PRIMARY KEY (log_id, subtask_id)
);

-- Memory snippets (with pgvector embedding)
-- Choose a dimension; 384 is common for MiniLM; adjust to your embedder
CREATE TABLE IF NOT EXISTS memory_snippets (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic       TEXT NOT NULL,
  text        TEXT NOT NULL,
  source      TEXT,
  pinned      BOOLEAN NOT NULL DEFAULT FALSE,
  embedding   VECTOR(384),           -- optional null until you add embeddings
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes (search-quality)
CREATE INDEX IF NOT EXISTS idx_tickets_due_date ON tickets(due_date);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_labels_gin ON tickets USING GIN (labels);
CREATE INDEX IF NOT EXISTS idx_tickets_components_gin ON tickets USING GIN (components);
CREATE INDEX IF NOT EXISTS idx_tickets_tech_gin ON tickets USING GIN (tech);

CREATE INDEX IF NOT EXISTS idx_subtasks_status ON subtasks(status);
CREATE INDEX IF NOT EXISTS idx_subtasks_tags_gin ON subtasks USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_plan_items_date ON plan_items(date);

-- Vector index (HNSW) for memory
-- Requires pgvector >= 0.5.0; adjust options per your version
CREATE INDEX IF NOT EXISTS idx_memory_embedding ON memory_snippets USING hnsw (embedding vector_l2_ops);
