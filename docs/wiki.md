# Plan Helper Project Wiki

## Overview
Plan Helper combines a Flask REST API with a React (Vite + TypeScript) single-page application to ingest tickets, decompose work into subtasks, batch related effort, generate plans, and publish daily reports. The backend exposes `/tools/*` namespaces for all planner operations, while the frontend provides a unified operator console that calls those endpoints via a shared API client. 【F:api/app.py†L1-L24】【F:frontend/src/App.tsx†L1-L26】

## Architecture
- **Backend** – Flask + Flask-RESTX app packaged under `api/` with SQLAlchemy data access and business logic in `logic/`. Each namespace in `api/routes/` covers a functional area: manual ticket storage, subtask creation, affinity batching, planner scheduling, and report generation. 【F:api/routes/tools_ticket_store.py†L1-L103】【F:api/routes/tools_subtasks.py†L1-L116】【F:api/routes/tools_affinity.py†L1-L95】【F:api/routes/tools_planner.py†L1-L84】【F:api/routes/tools_reports.py†L1-L137】
- **Database** – PostgreSQL (with pgvector support) stores tickets, subtasks, affinity groups, plans, and memory items. Local development can use the provided Docker Compose configuration for the database only. 【F:docker-compose.yml†L1-L14】
- **Frontend** – Vite + React + TypeScript UI housed in `frontend/`, organized into feature modules (`tickets`, `subtasks`, `affinity`, `planner`, `reports`) backed by a typed REST client in `src/api/client.ts`. Tailwind CSS provides the styling primitives and the layout keeps persistent navigation with routed feature pages. 【F:frontend/package.json†L1-L35】【F:frontend/src/api/client.ts†L1-L205】【F:frontend/src/features/tickets/TicketsPage.tsx†L1-L184】【F:frontend/src/layouts/AppLayout.tsx†L1-L44】

## Backend capabilities
### Ticket store (`/tools/tickets`)
- `POST /load_manual` – upsert tickets from JSON payloads, normalizing tech tags and story points. Returns counts plus warnings for incomplete rows. 【F:api/routes/tools_ticket_store.py†L11-L74】
- `POST /search` – filter tickets by ID, status, full-text snippet, or tech tags using SQLAlchemy query helpers. 【F:api/routes/tools_ticket_store.py†L76-L103】

### Subtasks (`/tools/subtasks`)
- `POST /create_for_ticket` – generate or import ordered subtasks for a ticket. Supports append/replace modes, optional manual bullet definitions, and LLM overrides; errors propagate with clear messages. 【F:api/routes/tools_subtasks.py†L23-L86】
- `POST /list` – fetch subtasks optionally filtered by ticket or status, returning sequence, tags, status, and estimates. 【F:api/routes/tools_subtasks.py†L88-L116】

### Affinity batching (`/tools/affinity`)
- `POST /compute` – load eligible subtasks, calculate affinity groups (shared tags/context), optionally clear prior results, and persist new groups plus members. 【F:api/routes/tools_affinity.py†L13-L69】
- `GET /list` – retrieve affinity groups with their rationales and member subtask IDs. 【F:api/routes/tools_affinity.py†L71-L95】

### Planner (`/tools/planner`)
- `POST /make_two_week_plan` – build multi-day schedules honoring configurable constraints (max contexts, focus blocks, buffer ratio), persist items, and return planned blocks. 【F:api/routes/tools_planner.py†L13-L66】
- `GET /list` – list persisted plan items with linked subtask IDs. 【F:api/routes/tools_planner.py†L68-L84】

### Reports (`/tools/reports`)
- `POST /morning` – produce morning checklists, affinity batches, risk calls, and optional LLM narrative. 【F:api/routes/tools_reports.py†L13-L94】
- `POST /evening` – accept completion payloads, compute plan deltas, and surface narrative summaries. 【F:api/routes/tools_reports.py†L96-L137】

## Frontend experience
The SPA routes mirror backend domains and are available in the sidebar navigation. React Query handles data fetching/caching and shared components provide consistent UI affordances.
- **Tickets workspace** – JSON upload form with inline validation, and a searchable results table with status badges and tag chips. 【F:frontend/src/features/tickets/TicketsPage.tsx†L1-L184】
- **Subtasks view** – filter by ticket/status, generate subtasks via modal workflows, and inspect metadata. 【F:frontend/src/features/subtasks/SubtasksPage.tsx†L1-L206】
- **Affinity groups** – recompute affinity batches with filters and review grouped cards summarizing rationales. 【F:frontend/src/features/affinity/AffinityPage.tsx†L1-L118】
- **Planner dashboard** – configure constraints, persist plans, and visualize timeline buckets for generated or stored schedules. 【F:frontend/src/features/planner/PlannerPage.tsx†L1-L234】
- **Reports hub** – request morning/evening reports, toggle narratives, and inspect deltas and summaries. 【F:frontend/src/features/reports/ReportsPage.tsx†L1-L248】
- **Shared layout** – persistent shell with navigation links and responsive design built from Tailwind utility classes. 【F:frontend/src/layouts/AppLayout.tsx†L1-L44】
- **API layer** – typed client centralizes REST access and shapes request/response contracts for all features. 【F:frontend/src/api/client.ts†L1-L205】

## Local development workflow
1. **Database** – start PostgreSQL (with pgvector) locally or via Docker:
   ```bash
   docker compose up db
   ```
2. **Python environment** – create the virtualenv and install dependencies:
   ```bash
   make venv
   ```
   Override `DATABASE_URL` if the connection string differs from the Makefile default. Run migrations or use `make db-init`/`make db-reset` to manage schema. 【F:Makefile†L1-L72】
3. **Backend server** – launch Flask API (port 8080):
   ```bash
   make api-run
   ```
4. **Frontend** – install Node dependencies and start the dev server (port 5173). The new Makefile targets wrap the npm commands:
   ```bash
   make frontend-install
   make frontend-dev
   ```
   Set `VITE_API_BASE_URL=http://localhost:8080` (and optionally `VITE_API_PROXY=http://localhost:8080`) in `frontend/.env` for cross-origin access. 【F:frontend/README.md†L5-L33】【F:Makefile†L55-L64】
5. **Combined dev helper** – run both servers simultaneously with one command (the recipe backgrounds each process and traps signals for clean shutdown):
   ```bash
   make dev-stack
   ```
   This spawns the Flask API and Vite dev server in the foreground so that logs remain visible; cancel with `Ctrl+C` to stop both. 【F:Makefile†L66-L71】

## Testing & quality
- **Backend** – execute `pytest` from the repo root; tests rely on mocks so no OpenAI calls occur. 【F:README.md†L25-L32】
- **Frontend** – run `npm run lint`, `npm run test` (if configured), or `npm run build` for type checking. Tailwind/Prettier configs keep styling consistent. 【F:frontend/README.md†L35-L56】

## Deployment considerations
- Serve the compiled frontend (`npm run build`) from any static host and point `VITE_API_BASE_URL` at the deployed Flask service. 【F:frontend/README.md†L37-L54】
- The backend expects `OPENAI_API_KEY` for narrative/subtask generation; without it the system falls back to template responses. Configure environment variables in your runtime environment or via Docker secrets. 【F:README.md†L11-L24】【F:api/routes/tools_subtasks.py†L28-L57】【F:api/routes/tools_reports.py†L17-L50】

## Operational runbooks
- **Seed demo data** – `make seed-demo` loads sample tickets and decomposes them via the API, ideal for populating the UI. 【F:Makefile†L76-L84】
- **Plan generation** – `make plan` triggers affinity computation and builds a two-week plan using default constraints. 【F:Makefile†L86-L92】
- **Reports** – `make morning` and `make evening` hit the corresponding endpoints for quick CLI verification. 【F:Makefile†L94-L101】
- **Timeline visuals** – `make timeline-day|week|fn` render PNG timelines from persisted plan data for slideware-ready artifacts. 【F:Makefile†L106-L113】
