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

Threats span 6 real-world domains — proving Vayuntra works across every sector.

### 🔴 CRITICAL (10)
| Domain | Threat | MITRE | Simulates |
|---|---|---|---|
| 🏛️ GOV | Ransomware Pre-Detonation on Ministry of Defence Server | T1486 | LockBit encrypting 3000+ classified files |
| 🏦 BANK | C2 Beacon on Core Banking SWIFT Payment System | T1071 | FIN7 Cobalt Strike beacon on payment server |
| 🏥 HOSPITAL | Credential Dump on Patient Records Database Server | T1003.001 | Mimikatz — 50,000 patient records exposed |
| 🏛️ GOV | Rootkit on Power Grid SCADA Control System | T1014 | DKOM hiding process — 2M citizens at risk |
| 💻 IT | Log4Shell Zero-Day on DevOps CI/CD Pipeline | T1190 | CVE-2021-44228 on Jenkins server |
| 💻 IT | Supply Chain Attack via Malicious NPM Package | T1195.002 | Trojanized package exfiltrating API keys |
| 🏢 CORP | PowerShell Empire Fileless Attack on HR System | T1059.001 | In-memory attack — 8,000 employee records |
| 🏢 CORP | Kerberoasting Attack on Corporate Active Directory | T1558.003 | Rubeus — service ticket offline cracking |
| 🏛️ GOV | Golden Ticket Forged on Election Commission Database | T1550.003 | Forged Kerberos TGT — voter data at risk |
| 🏥 HOSPITAL | WannaCry Worm Spreading Across ICU Network | T1210 | EternalBlue — 12 medical devices encrypted |

### 🟠 HIGH (10)
| Domain | Threat | MITRE | Simulates |
|---|---|---|---|
| 🏦 BANK | Lateral Movement on SWIFT Interbank Payment Network | T1021.002 | Pass-the-Hash — ₹200 crore exposure |
| 🏢 CORP | 4.7GB Customer PII Database Exfiltrated to Russia | T1041 | Aadhaar + transaction data exfiltrated |
| 🏦 BANK | Spearphishing Email Targeting Finance Team | T1566.001 | Emotet dropper — RBI audit lure |
| 💻 IT | DLL Hollowing on Security Operations Workstation | T1055.012 | Code injection — SOC tools compromised |
| 🏛️ GOV | DNS Tunneling from Intelligence Agency Network | T1048.001 | Iodine — covert exfil bypassing firewall |
| 🏢 CORP | WMI Abuse Living-off-the-Land on CEO Workstation | T1047 | Fileless — board strategy docs at risk |
| 🏥 HOSPITAL | Privilege Escalation on MRI Machine Controller | T1134.001 | PrintSpoofer — SYSTEM on medical device |
| 🏛️ GOV | Cobalt Strike Moving to Defence Ministry DC | T1569.002 | PSEXEC lateral move to domain controller |
| 🏦 BANK | 14,000 Credential Stuffing on Online Banking Portal | T1110.004 | 3 accounts compromised — ₹85 lakh risk |
| 🏦 BANK | BEC CEO Impersonation — ₹47 Lakh Wire Fraud | T1566.002 | Lookalike domain — finance team targeted |

### 🟡 MEDIUM (10)
| Domain | Threat | MITRE | Simulates |
|---|---|---|---|
| 💻 IT | Internal Recon Port Scan Across Cloud Infrastructure | T1046 | Nmap — database ports probed |
| 👤 PERSONAL | SSH Brute Force — 8,400 Attempts on Home Server | T1110.001 | Romanian IP — root account targeted |
| 🏢 CORP | Malicious Scheduled Task on Payroll Server | T1053.005 | Encoded PowerShell every 5 min |
| 👤 PERSONAL | Registry Run Key Persistence on Personal Laptop | T1547.001 | Fake AdobeUpdater — cracked software |
| 🏛️ GOV | Off-Hours TOR Login to Income Tax Department Portal | T1078 | 2.3 lakh taxpayer records accessed |
| 👤 PERSONAL | XMRig Cryptominer on Student Laptop — CPU 98% | T1496 | Monero miner — pirated software install |
| 🏢 CORP | Insider Threat — 3.2GB Files Copied to USB | T1052.001 | Resigning employee — board docs stolen |
| 🏥 HOSPITAL | RDP Brute Force on Hospital Administration System | T1110.003 | 5,200 attempts — billing system targeted |
| 💻 IT | Cron Reverse Shell on Production Web Server | T1053.003 | Bash shell every 5 min — RCE precursor |
| 👤 PERSONAL | Shadow IT — 14GB Corporate Files to Personal Dropbox | T1567.002 | WFH employee — source code + contacts |

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
