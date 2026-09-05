# FlowForge

Open-source visual workflow automation platform for developers.

FlowForge lets you build automation workflows as a graph of typed nodes, run them,
and inspect exactly what happened on every step of every run.

> Work in progress — see the roadmap at the bottom of this file.

## Repository layout

```
backend/    FastAPI service, workflow engine, PostgreSQL persistence
frontend/   Next.js application and visual workflow editor
docs/       Architecture and developer documentation
```

## Requirements

- Python 3.12+
- Node.js 20+
- Docker (for the local PostgreSQL instance)

## Quick start

```bash
docker compose up -d          # PostgreSQL on localhost:5432
cd backend && make dev        # FastAPI on localhost:8000
cd frontend && npm run dev    # Next.js on localhost:3000
```

## Roadmap

- [ ] Workflow persistence and visual editor
- [ ] Synchronous execution engine
- [ ] Execution history and inspection
- [ ] Webhook triggers
