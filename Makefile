# -----------------------------
# Sprint Planner Makefile
# -----------------------------
# Adjust these if needed
ENV_NAME = myenv310
DB_URL = postgresql+psycopg://postgres:postgres@localhost:5432/sprint_planner
PYTHON = $(ENV_NAME)/bin/python
EXPORT_ENV = export DATABASE_URL=$(DB_URL);

# Default target
help:
	@echo ""
	@echo "Available commands:"
	@echo "  make venv           - Create virtual environment and install deps"
	@echo "  make db-init        - Create DB tables"
	@echo "  make db-reset       - Drop + recreate all tables"
	@echo "  make api-run        - Run Flask API (port 8080)"
	@echo "  make seed-demo      - Upload demo tickets and decompose them"
	@echo "  make plan           - Compute affinity + plan 2 weeks"
	@echo "  make morning        - Show today's morning report"
	@echo "  make evening        - Example evening update"
	@echo "  make timeline-day   - Generate today's timeline image"
	@echo "  make timeline-week  - Generate weekly timeline"
	@echo "  make timeline-fn    - Generate fortnight timeline"
	@echo "  make clean          - Remove .pyc / cache files"
	@echo ""

# -----------------------------
# Environment setup
# -----------------------------
venv:
	python3 -m venv $(ENV_NAME)
	$(ENV_NAME)/bin/pip install -r requirements.txt

# -----------------------------
# Database management
# -----------------------------
db-init:
	$(EXPORT_ENV) $(PYTHON) -m db.models

db-reset:
	@echo "Dropping and recreating all tables..."
	$(EXPORT_ENV) $(PYTHON) -c "from db.models import Base, make_engine; e=make_engine(); Base.metadata.drop_all(e); Base.metadata.create_all(e)"
	@echo "Database reset complete."

# -----------------------------
# API server
# -----------------------------
api-run:
	$(EXPORT_ENV) $(PYTHON) -m api.app

# -----------------------------
# Demo / pipeline helpers
# -----------------------------
seed-demo:
	@echo "Seeding demo tickets..."
	echo '{"tickets":[{"id":"TKT-101","title":"Add DynamoDB TTL","story_points":3,"tech":["aws.dynamodb","terraform"],"status":"todo"},{"id":"TKT-102","title":"Lambda IAM least privilege","story_points":2,"tech":["aws.lambda","iam","terraform"],"status":"todo"}]}' > demo_tickets.json
	curl -s -X POST http://localhost:8080/tools/tickets/load_manual \
		-H 'Content-Type: application/json' -d @demo_tickets.json | jq .
	curl -s -X POST http://localhost:8080/tools/subtasks/create_for_ticket \
		-H 'Content-Type: application/json' -d '{"ticket_id":"TKT-101","mode":"replace"}' | jq .
	curl -s -X POST http://localhost:8080/tools/subtasks/create_for_ticket \
		-H 'Content-Type: application/json' -d '{"ticket_id":"TKT-102","mode":"replace"}' | jq .

plan:
	curl -s -X POST http://localhost:8080/tools/affinity/compute \
		-H 'Content-Type: application/json' \
		-d '{"status":["todo","in_progress"],"clear_existing":true}' | jq .
	curl -s -X POST http://localhost:8080/tools/planner/make_two_week_plan \
		-H 'Content-Type: application/json' \
		-d '{"start_date":"2025-10-06","days":10}' | jq .

morning:
	curl -s -X POST http://localhost:8080/tools/reports/morning \
		-H 'Content-Type: application/json' -d '{"date":"2025-10-10"}' | jq .

evening:
	curl -s -X POST http://localhost:8080/tools/reports/evening \
		-H 'Content-Type: application/json' \
		-d '{"date":"2025-10-10","completed":[],"partial":[],"blocked":[]}' | jq .

# -----------------------------
# Timeline renderers
# -----------------------------
timeline-day:
	$(EXPORT_ENV) $(PYTHON) -m scripts.timeline --mode day

timeline-week:
	$(EXPORT_ENV) $(PYTHON) -m scripts.timeline --mode week

timeline-fn:
	$(EXPORT_ENV) $(PYTHON) -m scripts.timeline --mode fortnight

# -----------------------------
# Cleanup
# -----------------------------
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
