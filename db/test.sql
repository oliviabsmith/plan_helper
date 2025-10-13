tickets (id PK) 1---* subtasks (id PK, ticket_id FK)
subtasks *---* plan_items via plan_item_subtasks
subtasks *---* affinity_groups via affinity_members
daily_logs (id PK, date unique) 1---* daily_log_items (log_id, subtask_id PKs, status)
memory_snippets (id PK)  // optional vector index on embedding
