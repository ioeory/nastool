# AGENTS.md

This file gives coding agents the minimum project context needed to work safely and quickly in this repository.

## Primary References

- Project overview and deployment notes: [README.md](README.md)
- Backend dependencies and dev extras: [backend/pyproject.toml](backend/pyproject.toml)
- Frontend scripts/dependencies: [frontend/package.json](frontend/package.json)
- Container setup: [docker-compose.yml](docker-compose.yml), [docker-compose.dev.yml](docker-compose.dev.yml)

## Repository Map

- `backend/app/`: FastAPI backend (`app.main` is the app entrypoint).
- `frontend/src/`: Vue 3 + Vite UI.
- `data/`: runtime data mounts (db/logs/media/torrents).
- `backend/tests/`: backend tests (pytest).

## Common Commands

Run from repo root unless noted.

- Backend local setup:
  - `cd backend && python3.11 -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt && pip install -e ".[dev]"`
- Backend dev server:
  - `cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 3001`
- Backend tests:
  - `cd backend && pytest -q`
- Frontend dev server:
  - `cd frontend && npm install && npm run dev`
- Frontend production build check:
  - `cd frontend && npm run build`
- Docker (production-like):
  - `docker compose up -d`
- Docker (hot reload for backend + frontend dev service):
  - `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`

## Architecture Boundaries

- Backend and frontend are intentionally decoupled; keep API contract changes synchronized across:
  - backend routes under `backend/app/api/v1/`
  - frontend API callers under `frontend/src/api/`
- FastAPI lifecycle/bootstrap behavior is centralized in `backend/app/main.py`; startup/shutdown side effects should stay there.
- Scheduler/task wiring is in backend runtime modules (`backend/app/scheduler.py`, related module managers).

## Project-Specific Pitfalls

- Do not bind-mount `./backend/app` into `/app/app` when using base `docker-compose.yml`; this can overwrite container code and break `app.main` imports. Use `docker-compose.dev.yml` for reload workflows.
- Backend expects Python 3.11 semantics/tooling (matching Docker image and local setup).
- `requirements.txt` and `pyproject.toml` both exist; if dependency changes affect runtime, keep both in sync unless there is an explicit migration decision.

## Agent Working Rules

- Prefer minimal, targeted edits; avoid broad refactors unless requested.
- Preserve API route prefixes and schema compatibility unless the task explicitly changes contract behavior.
- After changes:
  - run relevant tests (`pytest`) for backend work;
  - run `npm run build` for frontend-impacting work;
  - include migration/compatibility notes in PR descriptions when behavior changes.

## When Unsure

- Start with [README.md](README.md) for deployment/runtime assumptions.
- Use existing patterns in neighboring files before introducing new abstractions.