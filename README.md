# Backend

## Run

```bash
uvicorn app.main:app --reload
```

## Seed

```bash
python seed/seed_homepage.py
```

## Alembic

```bash
.venv/bin/alembic revision -m "init"
.venv/bin/alembic upgrade head
```

## Current Scope

- `GET /health`
- `GET /api/v1/homepage`
- `POST /api/v1/track/event`
- SQLAlchemy model skeleton for homepage MVP tables
- SQL init file: `sql/init_homepage_mvp.sql`
