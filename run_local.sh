#!/usr/bin/env bash
# ============================================================
# Vayuntra — Local Machine Quick Start
# ============================================================
# Prerequisites: Python 3.11+, PostgreSQL 14+
# Usage: bash run_local.sh
# ============================================================

set -e

RESET="\033[0m"; BOLD="\033[1m"; GREEN="\033[0;32m"; CYAN="\033[0;36m"
RED="\033[0;31m"; YELLOW="\033[1;33m"

banner() {
  echo -e "${CYAN}${BOLD}"
  echo "╔══════════════════════════════════════════════════════╗"
  echo "║          VAYUNTRA — Autonomous AI Cyber Defense      ║"
  echo "║                  Local Setup Script                  ║"
  echo "╚══════════════════════════════════════════════════════╝"
  echo -e "${RESET}"
}

banner

# ── 1. Python check ──────────────────────────────────────────
echo -e "${BOLD}[1/5] Checking Python version...${RESET}"
PY=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
MAJOR=$(echo "$PY" | cut -d. -f1)
MINOR=$(echo "$PY" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
  echo -e "${RED}ERROR: Python 3.11+ required. Found: python3 $PY${RESET}"
  exit 1
fi
echo -e "  ${GREEN}✓ Python $PY${RESET}"

# ── 2. PostgreSQL check ──────────────────────────────────────
echo -e "${BOLD}[2/5] Checking PostgreSQL...${RESET}"
if ! command -v psql &>/dev/null; then
  echo -e "${RED}ERROR: psql not found. Install PostgreSQL 14+:${RESET}"
  echo "  Fedora/RHEL:  sudo dnf install postgresql-server postgresql"
  echo "  Ubuntu:       sudo apt install postgresql"
  echo "  macOS:        brew install postgresql"
  exit 1
fi
echo -e "  ${GREEN}✓ PostgreSQL found${RESET}"

# ── 3. Create DB & user ──────────────────────────────────────
echo -e "${BOLD}[3/5] Setting up database...${RESET}"
DB_NAME="vayuntra"
DB_USER="vayuntra_user"
DB_PASS="vayuntra123"

# Try to create the user and database (idempotent)
psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
echo -e "  ${GREEN}✓ Database '$DB_NAME' ready (user: $DB_USER)${RESET}"

# Write .env
cat > backend/.env << ENVEOF
APP_ENV=development
APP_VERSION=0.1.0
APP_SECRET_KEY=vayuntra-dev-secret-key-change-in-production
DEBUG=true
LOG_LEVEL=INFO

# PostgreSQL — auto-configured by run_local.sh
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}

# JWT
JWT_SECRET_KEY=vayuntra-jwt-secret-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Features
LLM_ENABLED=false
FEATURE_LLM_REMEDIATION=true
FEATURE_AUTO_ISOLATION=true
FEATURE_BEHAVIORAL_MEMORY=true
ENVEOF
echo -e "  ${GREEN}✓ backend/.env written${RESET}"

# ── 4. Python dependencies ───────────────────────────────────
echo -e "${BOLD}[4/5] Installing Python dependencies...${RESET}"
cd backend
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "  ${GREEN}✓ Dependencies installed${RESET}"
cd ..

# ── 5. Launch ────────────────────────────────────────────────
echo -e "${BOLD}[5/5] Starting Vayuntra...${RESET}"
echo ""
echo -e "${CYAN}${BOLD}"
echo "══════════════════════════════════════════════════════"
echo "  🚀 Starting on   http://localhost:8000"
echo "  📊 Dashboard:    http://localhost:8000"
echo "  📖 API Docs:     http://localhost:8000/api/docs"
echo "  🔑 Login:        admin@vayuntra.demo / Vayuntra@123"
echo "══════════════════════════════════════════════════════"
echo -e "${RESET}"

cd backend
source .venv/bin/activate
python ../start.py
