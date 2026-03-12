# Vayuntra — Autonomous AI Cyber Defense Platform

> Real-time threat detection · Behavioral analysis · Autonomous remediation  
> Runs entirely on your local machine. **Cost: ₹0**

![Status](https://img.shields.io/badge/Status-Live-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![React](https://img.shields.io/badge/React-18-61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791)

---

## What is Vayuntra?

Vayuntra is an autonomous AI cybersecurity platform that:

- 🔴 **Detects** threats in real-time using ML ensemble (Isolation Forest + SVM + LSTM)
- 🗺️ **Maps** attacks to MITRE ATT&CK framework automatically
- 🔒 **Isolates** compromised endpoints with one click
- 🤖 **Remediates** threats with AI-generated step-by-step playbooks
- 📡 **Monitors** all endpoints via lightweight cross-platform agents
- 📊 **Visualizes** everything on a live cyberpunk SOC dashboard

---

## Prerequisites

Install these before starting:

| Tool | Version | Install |
|---|---|---|
| Git | any | https://git-scm.com |
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| PostgreSQL | 14+ | https://postgresql.org |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/akashlogeshbabu-git-07/vayuntra-platform.git
cd vayuntra-platform
```

---

## Step 2 — PostgreSQL Database Setup

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
psql postgres
```

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install postgresql postgresql-client -y
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -u postgres psql
```

**Fedora:**
```bash
sudo dnf install postgresql postgresql-server -y
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -u postgres psql
```

**Windows:**
- Download from https://postgresql.org/download/windows
- Install and open pgAdmin or psql shell

**Inside psql — run these 3 commands:**
```sql
CREATE DATABASE vayuntra;
CREATE USER vayuntra_user WITH PASSWORD 'vayuntra123';
GRANT ALL PRIVILEGES ON DATABASE vayuntra TO vayuntra_user;
\q
```

**Verify it worked:**
```bash
psql postgresql://vayuntra_user:vayuntra123@localhost:5432/vayuntra -c "SELECT 1;"
# Output: ?column? = 1
```

---

## Step 3 — Configure Backend .env

```bash
nano backend/.env
```

Make sure it contains exactly this:
```env
APP_ENV=development
APP_VERSION=0.1.0
APP_SECRET_KEY=vayuntra-dev-secret-key-change-in-production
DEBUG=true
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://vayuntra_user:vayuntra123@localhost:5432/vayuntra

JWT_SECRET_KEY=vayuntra-jwt-secret-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

LLM_ENABLED=false
FEATURE_LLM_REMEDIATION=true
FEATURE_AUTO_ISOLATION=true
FEATURE_BEHAVIORAL_MEMORY=true
```

Save: `Ctrl+X` → `Y` → `Enter`

---

## Step 4 — Backend Python Environment

```bash
cd backend

python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
# venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

cd ..
```

---

## Step 5 — Seed Database (30 threats + 5 agents)

```bash
cd backend
source venv/bin/activate
python seed_data.py
cd ..
```

Expected output:
```
✅ Tenant created: Vayuntra Demo Corp
✅ User created: admin@vayuntra.demo / Vayuntra@123
✅ 5 agents ready
✅ 30 new threats seeded
🚀 Seed complete!
```

---

## Step 6 — Start Backend Server

```bash
source backend/venv/bin/activate
python start.py
```

You will see:
```
✅ PostgreSQL connection OK
✅ Database tables ready
✅ Demo data already exists
🚀 Starting Vayuntra on http://localhost:8000
INFO: Uvicorn running on http://0.0.0.0:8000
```

> The cursor keeps blinking — **that is normal**. Server is live.  
> Keep this terminal open. Open a **new terminal** for next steps.

**Verify:**
```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0"}
```

**Backend live at:**
- Dashboard → http://localhost:8000
- API Docs → http://localhost:8000/api/docs
- Login → `admin@vayuntra.demo` / `Vayuntra@123`

---

## Step 7 — Frontend Setup (React)

Open a **new terminal** (keep backend running).

```bash
cd frontend
npm install
```

**Configure frontend to point at backend:**
```bash
cat frontend/.env
# Should show: VITE_API_URL=http://localhost:8000
```

If the file is missing:
```bash
echo "VITE_API_URL=http://localhost:8000" > frontend/.env
```

**Start frontend:**
```bash
cd frontend
npm run dev
```

You will see:
```
  VITE v5.x  ready in 800ms
  ➜  Local:   http://localhost:5173/
```

**Frontend live at:** http://localhost:5173

> Login with same credentials: `admin@vayuntra.demo` / `Vayuntra@123`

---

## Both Running — Full Stack Summary

You now have **two terminals running**:

| Terminal | Command | URL |
|---|---|---|
| Terminal 1 | `python start.py` | http://localhost:8000 |
| Terminal 2 | `npm run dev` (inside frontend/) | http://localhost:5173 |

Both connect to the same PostgreSQL database.

---

## Step 8 — Live Threat Demo

Open a **third terminal**.

### Get auth token first:
```bash
cd vayuntra-platform/backend
source venv/bin/activate

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@vayuntra.demo&password=Vayuntra@123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Token ready"
```

### Run the full demo (10 threats, one every 5 seconds):
```bash
cd ..
bash demo.sh
```

Watch http://localhost:8000 — threats appear live on dashboard.

### Inject one threat manually:
```bash
curl -s -X POST http://localhost:8000/api/v1/threats/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Ransomware Pre-Detonation — WORKSTATION-047",
    "severity": "critical",
    "mitre_tactic": "Impact",
    "mitre_technique": "T1486",
    "source_ip": "172.16.0.47",
    "dest_ip": "185.220.101.34",
    "process_name": "unknown.exe",
    "confidence_score": 0.97,
    "anomaly_score": 0.94,
    "description": "Mass file encryption. 2000+ files renamed .locked. Shadow copies deleted."
  }' | python3 -m json.tool
```

### Isolate a threat:
```bash
# Get first threat ID
THREAT_ID=$(curl -s http://localhost:8000/api/v1/threats/ \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['threats'][0]['id'])")

# Isolate it
curl -s -X POST http://localhost:8000/api/v1/threats/$THREAT_ID/isolate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"isolation_type": "network", "reason": "Ransomware detected"}' \
  | python3 -m json.tool
```

### Generate AI remediation playbook:
```bash
curl -s -X POST http://localhost:8000/api/v1/threats/$THREAT_ID/remediate \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

### Get dashboard stats:
```bash
curl -s http://localhost:8000/api/v1/dashboard/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### List all threats:
```bash
curl -s http://localhost:8000/api/v1/threats/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### List all agents:
```bash
curl -s http://localhost:8000/api/v1/agents/ \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## All URLs

| URL | What you see |
|---|---|
| http://localhost:8000 | SOC Dashboard |
| http://localhost:5173 | React Frontend |
| http://localhost:8000/api/docs | Swagger API Docs |
| http://localhost:8000/api/v1/threats/ | Threats JSON |
| http://localhost:8000/api/v1/agents/ | Agents JSON |
| http://localhost:8000/api/v1/dashboard/stats | Live stats JSON |
| http://localhost:8000/health | Health check |

---

## Full Demo Flow (step by step)

```
1.  Open http://localhost:8000
2.  Login → admin@vayuntra.demo / Vayuntra@123
3.  Dashboard loads → active threats, agents, anomaly trend visible
4.  Open new terminal → run: bash demo.sh
5.  Refresh dashboard → threats appear live every 5 seconds
6.  Click VIEW on any threat → full details + MITRE mapping
7.  Click ISOLATE → endpoint status changes to ISOLATED
8.  Click REMEDIATE → AI generates step-by-step remediation playbook
9.  Click Agents tab → see which agents are online / isolated / offline
10. Visit http://localhost:8000/api/docs → explore all APIs live
```

---

## 30 Pre-loaded Threats

### 🔴 CRITICAL (10)
| Threat | MITRE | Simulates |
|---|---|---|
| Ransomware Pre-Detonation | T1486 | LockBit encrypting 2000+ files |
| C2 Beacon — Cobalt Strike | T1071 | Attacker C2 communication |
| LSASS Dump — Mimikatz | T1003.001 | Domain credential harvesting |
| Rootkit Kernel Injection | T1014 | Hidden process via DKOM |
| Zero-Day Log4Shell RCE | T1190 | CVE-2021-44228 exploitation |
| Supply Chain NPM Backdoor | T1195.002 | Trojanized package exfiltration |
| PowerShell Empire Fileless | T1059.001 | In-memory attack, no disk writes |
| Kerberoasting | T1558.003 | Service ticket offline cracking |
| Golden Ticket Attack | T1550.003 | Forged Kerberos TGT |
| WannaCry SMB Worm | T1210 | EternalBlue propagation |

### 🟠 HIGH (10)
| Threat | MITRE | Simulates |
|---|---|---|
| Lateral Movement Pass-the-Hash | T1021.002 | NTLM hash reuse via SMB |
| Data Exfiltration 4.7GB | T1041 | Large outbound transfer |
| Phishing Office Macro | T1566.001 | Emotet dropper via Word doc |
| DLL Hollowing Explorer | T1055.012 | Code injection into explorer.exe |
| DNS Tunneling C2 | T1048.001 | Covert channel via DNS |
| WMI Abuse LOTL | T1047 | Fileless execution via wmic.exe |
| Privilege Escalation Token | T1134.001 | SYSTEM via SeImpersonatePrivilege |
| Cobalt Strike PSEXEC | T1569.002 | Lateral move to domain controller |
| O365 Credential Stuffing | T1110.004 | 14,000 automated login attempts |
| BEC CEO Impersonation | T1566.002 | Wire fraud via lookalike domain |

### 🟡 MEDIUM (10)
| Threat | MITRE | Simulates |
|---|---|---|
| Port Scan Reconnaissance | T1046 | Nmap full subnet scan |
| SSH Brute Force 8400 | T1110.001 | Password spray from Romania |
| Malicious Scheduled Task | T1053.005 | Persistence via task scheduler |
| Registry Run Key | T1547.001 | Startup persistence via registry |
| Off-Hours TOR Login | T1078 | Admin login from TOR exit node |
| XMRig Cryptominer | T1496 | Monero miner on prod server |
| USB Exfiltration 3.2GB | T1052.001 | Sensitive files to USB drive |
| RDP Brute Force DC | T1110.003 | 5200 attempts on domain controller |
| Cron Reverse Shell | T1053.003 | Bash reverse shell via cron |
| Shadow IT Dropbox | T1567.002 | 14GB corp data to personal cloud |

---

## Project Structure

```
vayuntra-platform/
├── start.py                          ← One-command launcher
├── demo.sh                           ← Live threat injection demo
├── README.md                         ← This file
│
├── backend/
│   ├── app/
│   │   ├── main.py                   ← FastAPI app entry point
│   │   ├── api/v1/endpoints/
│   │   │   ├── auth.py               ← Login, JWT tokens
│   │   │   ├── threats.py            ← Threat CRUD, isolate, remediate
│   │   │   ├── agents.py             ← Agent management
│   │   │   ├── dashboard.py          ← Live stats
│   │   │   ├── behavioral.py         ← Behavioral analysis
│   │   │   ├── remediation.py        ← AI playbook engine
│   │   │   ├── llm.py                ← LLM integration (Mistral)
│   │   │   └── telemetry.py          ← Agent telemetry ingestion
│   │   ├── core/
│   │   │   ├── config.py             ← Settings from .env
│   │   │   ├── database.py           ← PostgreSQL async engine
│   │   │   ├── auth.py               ← JWT dependency injection
│   │   │   └── security.py           ← Password hashing (bcrypt)
│   │   ├── db/models/models.py       ← SQLAlchemy ORM models
│   │   ├── services/
│   │   │   ├── threat/               ← Threat detection + isolation
│   │   │   └── ml/                   ← AI remediation playbooks
│   │   └── schemas/                  ← Pydantic request/response types
│   ├── static/index.html             ← Full SOC Dashboard UI
│   ├── seed_data.py                  ← Seeds 30 threats + 5 agents
│   ├── requirements.txt              ← Python dependencies
│   └── .env                          ← Database + secrets config
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   ← Main React app + routing
│   │   ├── pages/                    ← Dashboard, Threats, Agents pages
│   │   ├── components/               ← Reusable UI components
│   │   ├── hooks/                    ← useAuth, useWebSocket, useTenant
│   │   ├── utils/api.ts              ← Axios API client
│   │   └── types/index.ts            ← TypeScript type definitions
│   ├── package.json                  ← Node dependencies
│   ├── vite.config.ts                ← Vite build config
│   └── .env                          ← VITE_API_URL=http://localhost:8000
│
├── ml/
│   ├── models/anomaly/               ← Ensemble anomaly detector
│   └── pipelines/inference/serve.py  ← ML inference API (port 8001)
│
├── agent/
│   └── src/                          ← Endpoint monitoring agent
│
├── infrastructure/
│   ├── kubernetes/                   ← K8s deployment manifests
│   └── monitoring/                   ← Prometheus + Grafana configs
│
└── docker-compose.yml                ← Full Docker stack (optional)
```

---

## API Reference

### Auth
```
POST  /api/v1/auth/login         Login → returns JWT token
POST  /api/v1/auth/register      Register new user + tenant
GET   /api/v1/auth/me            Current logged-in user info
```

### Threats
```
GET   /api/v1/threats/                   List all threats (paginated)
POST  /api/v1/threats/                   Create / inject threat
GET   /api/v1/threats/stats              Stats by severity
GET   /api/v1/threats/{id}               Threat detail
PATCH /api/v1/threats/{id}               Update status / analyst notes
POST  /api/v1/threats/{id}/isolate       Isolate the endpoint
POST  /api/v1/threats/{id}/remediate     Generate AI playbook
```

### Agents
```
GET   /api/v1/agents/                    List all agents
POST  /api/v1/agents/                    Register new agent
GET   /api/v1/agents/{id}                Agent detail
PATCH /api/v1/agents/{id}/status         Update agent status
```

### Dashboard
```
GET   /api/v1/dashboard/stats            Live dashboard statistics
```

### System
```
GET   /health                            Server health check
GET   /api/docs                          Swagger UI
GET   /api/openapi.json                  OpenAPI schema
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named sqlalchemy"
```bash
# venv not activated
source backend/venv/bin/activate
```

### "PostgreSQL connection failed"
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test credentials manually
psql postgresql://vayuntra_user:vayuntra123@localhost:5432/vayuntra -c "SELECT 1;"

# Recreate user if needed
sudo -u postgres psql -c "DROP USER IF EXISTS vayuntra_user;"
sudo -u postgres psql -c "CREATE USER vayuntra_user WITH PASSWORD 'vayuntra123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vayuntra TO vayuntra_user;"
```

### "Port 8000 already in use"
```bash
lsof -i :8000 | grep LISTEN
kill -9 <PID>
```

### "Port 5173 already in use"
```bash
lsof -i :5173 | grep LISTEN
kill -9 <PID>
```

### Frontend not connecting to backend
```bash
# Verify frontend .env
cat frontend/.env
# Must be: VITE_API_URL=http://localhost:8000

# Verify backend is running
curl http://localhost:8000/health
```

### Token expired
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@vayuntra.demo&password=Vayuntra@123" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### npm install fails
```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL + SQLAlchemy async |
| Auth | JWT — python-jose + bcrypt |
| ML | Scikit-learn (Isolation Forest + SVM) |
| Frontend | React 18 + Vite + TypeScript |
| Styling | Tailwind CSS |
| Agent | Python + psutil |
| Containers | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |

---

## Demo Credentials

| | |
|---|---|
| URL | http://localhost:8000 |
| Email | admin@vayuntra.demo |
| Password | Vayuntra@123 |
| API Docs | http://localhost:8000/api/docs |

---

Built by **Akash** — Vayuntra Autonomous AI Cyber Defense Platform
