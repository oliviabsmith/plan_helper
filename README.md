# Sprint Planner

This project provides a lightweight API for breaking down engineering tickets into actionable subtasks and planning sprints.

## Prerequisites

* Python 3.10+
* PostgreSQL (for persistence)

## Environment setup

1. Create a virtual environment and install dependencies:

   ```bash
   make venv
   ```

2. Export the database URL if you need to override the default in `Makefile`.

3. **LLM access:** Several endpoints now rely on an LLM to generate detailed subtasks. Before running the API locally ensure the OpenAI API key is exported:

   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

   The helper expects the official [OpenAI Python SDK](https://pypi.org/project/openai/) credentials. If the key is missing, the application automatically falls back to template-generated subtasks.

4. Run the API server:

   ```bash
   make api-run
   ```

## Testing

The test suite uses `pytest` and includes mocks for the LLM client so the OpenAI API is never called during automated runs.

```bash
pytest
```
