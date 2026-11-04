# Deployment

**Status: not deployed.** No hosting or provider credentials were available. Everything below was run locally against PostgreSQL 16 with gunicorn, but there is no public URL.

## Environment variables (names only)

`APP_ENV` (`production` enforces a real `SECRET_KEY` and a non-SQLite `DATABASE_URL`), `SECRET_KEY`, `DATABASE_URL`, `APP_BASE_URL`, `REQUIRE_EMAIL_VERIFICATION`, `SESSION_COOKIE_SECURE` (set `true` behind HTTPS), `MAX_UPLOAD_BYTES`, `MAX_IMPORT_ROWS`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`.

## Local

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-app.txt
cp .env.example .env        # fill values, then export them
alembic upgrade head
flask --app wsgi run        # or: gunicorn wsgi:app
pytest                      # SQLite; set TEST_DATABASE_URL for PostgreSQL
```

## Production (any host with PostgreSQL)

1. Create a PostgreSQL database and set `DATABASE_URL` (`postgres://` URLs are accepted).
2. Set `APP_ENV=production`, a long random `SECRET_KEY`, `SESSION_COOKIE_SECURE=true`, `APP_BASE_URL`.
3. Release step: `alembic upgrade head`. Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2` (see `Procfile`).
4. Check `GET /healthz` (200 `{"status":"ok"}`; 503 if the database is unreachable).
5. For real email verification set the `SMTP_*` variables and `REQUIRE_EMAIL_VERIFICATION=true`.

## What I need from you to deploy

A hosting account (Render/Railway/Fly/etc.), a managed PostgreSQL URL, an SMTP account (or an auth provider), and a decision on the auth provider. Database backup/restore is Day 7 and not done.
