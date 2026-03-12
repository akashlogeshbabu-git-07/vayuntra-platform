# Vayuntra — Autonomous AI Cyber Defense Platform

## Quick Start (3 steps)

### Step 1 — Set up PostgreSQL (one time only)
Open psql or pgAdmin and run:
```sql
CREATE DATABASE vayuntra;
CREATE USER vayuntra_user WITH PASSWORD 'vayuntra123';
GRANT ALL PRIVILEGES ON DATABASE vayuntra TO vayuntra_user;
```

### Step 2 — Configure database connection
Edit `backend/.env` and set:
```
DATABASE_URL=postgresql+asyncpg://vayuntra_user:vayuntra123@localhost:5432/vayuntra
```

### Step 3 — Install and run
```bash
cd backend
pip install -r requirements.txt

# Go back to root and run:
cd ..
python start.py
```

Browser opens automatically at **http://localhost:8000**

**Login:** `admin@vayuntra.demo` / `Vayuntra@123`

---

## What's included

| Component | Description |
|---|---|
| `backend/` | FastAPI backend — all APIs |
| `backend/static/index.html` | Dashboard UI (same as vayuntra-dashboard.html, wired to real API) |
| `backend/seed_data.py` | Creates demo tenant, user, 5 agents, 15 threats |
| `start.py` | One-command launcher — checks DB, seeds, starts server, opens browser |
| `ml/` | ML ensemble detector (Isolation Forest + SVM + LSTM) |
| `agent/` | Cross-platform endpoint agent |

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard UI |
| `POST /api/v1/auth/login` | Login |
| `GET /api/v1/dashboard/stats` | Dashboard stats |
| `GET /api/v1/threats/` | List all threats |
| `POST /api/v1/threats/{id}/isolate` | Isolate threat |
| `POST /api/v1/threats/{id}/remediate` | Generate playbook |
| `GET /api/v1/agents/` | List all agents |
| `GET /api/docs` | Interactive API docs |

## Architecture

```
Browser (http://localhost:8000)
    ↓ HTTPS
FastAPI Backend (port 8000)
    ↓ Serves static/index.html as dashboard
    ↓ /api/v1/* routes for data
PostgreSQL Database
    ↓ Tenants, Users, Agents, Threats, AuditLogs
```

## Cost

**₹0 — Fully free, runs entirely on your local machine.**
- No cloud required
- No paid services
- Only dependency: PostgreSQL (free)
