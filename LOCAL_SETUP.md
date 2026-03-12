# Vayuntra — Local Machine Setup

## Quick Start (Recommended)

```bash
bash run_local.sh
```

The script auto-detects your environment, creates the PostgreSQL database, installs Python dependencies, and launches the server.

**Default login:** `admin@vayuntra.demo` / `Vayuntra@123`

---

## Manual Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (running locally)

### Step 1 — PostgreSQL

```sql
-- Run in psql as postgres superuser
CREATE DATABASE vayuntra;
CREATE USER vayuntra_user WITH PASSWORD 'vayuntra123';
GRANT ALL PRIVILEGES ON DATABASE vayuntra TO vayuntra_user;
```

**Fedora/RHEL:**
```bash
sudo dnf install postgresql-server postgresql
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo -u postgres psql
```

**Ubuntu/Debian:**
```bash
sudo apt install postgresql
sudo -u postgres psql
```

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
psql postgres
```

### Step 2 — Configure `.env`

Edit `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://vayuntra_user:vayuntra123@localhost:5432/vayuntra
```

### Step 3 — Install Dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4 — Run

```bash
# From project root
python start.py
```

The startup script will:
1. Test the PostgreSQL connection
2. Create all database tables
3. Seed demo data (tenant, admin user, 5 agents, 15 threats)
4. Start FastAPI on `http://localhost:8000`
5. Open the dashboard in your browser

---

## Optional — Local LLM (Mistral 7B)

By default the platform uses **rule-based remediation playbooks**. To enable the local Mistral LLM:

```bash
# 1. Install llama-cpp-python (CPU build)
pip install llama-cpp-python

# For GPU acceleration (CUDA):
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python

# 2. Download the model (3.8 GB)
mkdir -p /models
wget -O /models/mistral-7b-instruct-v0.2.Q4_K_M.gguf \
  https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf

# 3. Enable in backend/.env
LLM_ENABLED=true
LLM_MODEL_PATH=/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
LLM_N_THREADS=8          # Set to your CPU core count
LLM_N_GPU_LAYERS=0       # Set >0 for GPU offload (e.g. 35 for full offload)
```

Restart `python start.py` after enabling.

---

## Docker Alternative

```bash
# Requires Docker + Docker Compose
docker compose up --build
```

Services started: FastAPI backend, PostgreSQL, (optional) Redis, Prometheus.

---

## URLs

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Dashboard |
| `http://localhost:8000/api/docs` | Swagger UI |
| `http://localhost:8000/api/redoc` | ReDoc |
| `http://localhost:8000/api/v1/threats/` | Threats API |
| `http://localhost:8000/api/v1/dashboard/stats` | Dashboard stats |

---

## Troubleshooting

**`asyncpg.exceptions.ConnectionDoesNotExistError`**
→ PostgreSQL is not running. Start it with `sudo systemctl start postgresql`.

**`sqlalchemy.exc.OperationalError: FATAL: role does not exist`**
→ User not created. Run the SQL in Step 1 above.

**`ModuleNotFoundError: No module named 'asyncpg'`**
→ Activate the venv: `source backend/.venv/bin/activate`

**Port 8000 already in use**
→ `lsof -i :8000` then kill the process, or change the port in `start.py`.
