# Statsmed New UI (Login, Register, PostgreSQL)

This is the new user interface for statsmed, based on the CalmInvesting pattern: **Next.js** frontend, **FastAPI** backend, **PostgreSQL** for users and persisted data. Users can register and log in; all uploaded files and analysis results are saved per user.

## Quick start with Docker

1. **Start PostgreSQL, backend, and frontend:**

   ```bash
   docker compose up -d
   ```

2. **Open the app:** [http://localhost:3000](http://localhost:3000)

3. **Register** a new account, then **log in**. Upload CSV/Excel files and run tests; data is stored in PostgreSQL and in the backend uploads directory per user.

## Running locally (without Docker)

### 1. PostgreSQL

Create a database and set `DATABASE_URL`:

```bash
# Example: local Postgres
export DATABASE_URL="postgresql+psycopg://statsmed:statsmed@localhost:5432/statsmed"
createdb statsmed  # if needed
```

### 2. Backend (FastAPI)

From the **repo root** (statsmed), so that `web` and `statsmed` packages are importable:

```bash
cd /path/to/statsmed
pip install -e ".[web]"
pip install -r backend/requirements.txt
export DATABASE_URL="postgresql+psycopg://..."
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` if the API is not on the same host. Open [http://localhost:3000](http://localhost:3000).

## What’s included

- **Auth:** Register (username, email, password) and login; JWT in `Authorization` header; token and username in `localStorage` (`statsmed_token`, `statsmed_user`).
- **Database (PostgreSQL):**
  - `users` – username, email, password hash, `is_active`
  - `data_files` – per-user file metadata (original name, path on server, CSV delimiter)
  - `analysis_results` – per-file results (test id, label, text, optional figure base64, params JSON)
- **Storage:** Uploaded files are stored under `backend/uploads/<user_id>/`; metadata and results in the DB.
- **API:** See `backend/app/routers/auth.py` and `backend/app/routers/data.py` for routes (e.g. `/auth/register`, `/auth/login`, `/api/data/upload`, `/api/data/files`, `/api/data/run`, `/api/data/files/{id}/download-pdf`).

## Environment

- **Backend:** `DATABASE_URL` (required), `JWT_SECRET` (optional, default dev secret).
- **Frontend:** `NEXT_PUBLIC_API_URL` (optional, default `http://localhost:8000`).

## Caddy (reverse proxy)

If your Caddyfile lives elsewhere, copy the block from **`Caddyfile.ui.example`** into your existing Caddy config. It routes `/auth/*` and `/api/*` to the backend and everything else to the frontend. When using Caddy with Docker, run with both compose files so the stack joins `caddy_net`: `docker compose -f docker-compose.yml -f docker-compose.caddy.yml up -d` (create the network first: `docker network create caddy_net`). Adjust upstream hostnames if Caddy runs in a different stack.
