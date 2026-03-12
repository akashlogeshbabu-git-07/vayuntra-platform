#!/usr/bin/env bash
# ============================================================================
# Vayuntra — Development Environment Setup
# Run once after cloning the repository
# ============================================================================

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${CYAN}[VAYUNTRA]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Vayuntra — Development Environment Setup    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ── Prerequisites check ──────────────────────────────────────────────────
log "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || error "Python 3.11+ required"
command -v node >/dev/null 2>&1 || error "Node.js 20+ required"
command -v docker >/dev/null 2>&1 || error "Docker required"
command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1 || error "Docker Compose required"
command -v git >/dev/null 2>&1 || error "Git required"

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)

[[ "${PYTHON_VERSION}" > "3.10" ]] || error "Python 3.11+ required (found ${PYTHON_VERSION})"
[[ "${NODE_VERSION}" -ge "18" ]] || error "Node 20+ required (found ${NODE_VERSION})"

success "Prerequisites OK"

# ── Environment file ──────────────────────────────────────────────────────
log "Setting up environment files..."

if [ ! -f .env ]; then
    cp .env.example .env
    success "Created .env from template"
    warn "IMPORTANT: Edit .env and fill in required values before running"
else
    warn ".env already exists — skipping"
fi

# ── Generate dev certificates ─────────────────────────────────────────────
log "Generating development TLS certificates..."

mkdir -p certs

if [ ! -f certs/ca.crt ]; then
    # Generate CA
    openssl genrsa -out certs/ca.key 4096 2>/dev/null
    openssl req -new -x509 -key certs/ca.key -sha256 -subj "/C=IN/O=Vayuntra/CN=Dev-CA" \
        -out certs/ca.crt -days 3650 2>/dev/null
    
    # Generate server cert
    openssl genrsa -out certs/server.key 2048 2>/dev/null
    openssl req -new -key certs/server.key -subj "/C=IN/O=Vayuntra/CN=localhost" \
        -out certs/server.csr 2>/dev/null
    openssl x509 -req -in certs/server.csr -CA certs/ca.crt -CAkey certs/ca.key \
        -CAcreateserial -out certs/server.crt -days 365 2>/dev/null
    
    # Generate agent cert
    openssl genrsa -out certs/agent.key 2048 2>/dev/null
    openssl req -new -key certs/agent.key -subj "/C=IN/O=Vayuntra/CN=dev-agent-001" \
        -out certs/agent.csr 2>/dev/null
    openssl x509 -req -in certs/agent.csr -CA certs/ca.crt -CAkey certs/ca.key \
        -CAcreateserial -out certs/agent.crt -days 365 2>/dev/null
    
    success "Development certificates generated"
else
    warn "Certificates already exist — skipping"
fi

# ── Backend Python environment ────────────────────────────────────────────
log "Setting up backend Python environment..."

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install -r requirements-dev.txt -q
deactivate
cd ..

success "Backend Python environment ready"

# ── ML Python environment ─────────────────────────────────────────────────
log "Setting up ML Python environment..."

cd ml
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate
cd ..

success "ML Python environment ready"

# ── Agent Python environment ──────────────────────────────────────────────
log "Setting up agent Python environment..."

cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate
cd ..

success "Agent Python environment ready"

# ── Frontend Node environment ─────────────────────────────────────────────
log "Setting up frontend Node environment..."

cd frontend
npm install --silent
cd ..

success "Frontend dependencies installed"

# ── Docker infrastructure ─────────────────────────────────────────────────
log "Starting Docker infrastructure..."

docker compose up -d postgres timescaledb redis zookeeper kafka minio

log "Waiting for services to be healthy..."
sleep 15

# Check postgres
until docker compose exec -T postgres pg_isready -U vayuntra_app -d vayuntra >/dev/null 2>&1; do
    sleep 2
done
success "PostgreSQL ready"

# Check redis
until docker compose exec -T redis redis-cli ping >/dev/null 2>&1; do
    sleep 2
done
success "Redis ready"

success "Docker infrastructure running"

# ── Database migrations ───────────────────────────────────────────────────
log "Running database migrations..."

cd backend
source .venv/bin/activate
export $(grep -v '^#' ../.env | xargs) 2>/dev/null || true
export DB_HOST=localhost
export DB_PASSWORD=dev_password_change_in_prod
export DB_SSL_MODE=disable
alembic upgrade head
deactivate
cd ..

success "Database migrations complete"

# ── Final summary ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Development Environment Ready!              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Start backend:    cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  Start frontend:   cd frontend && npm run dev"
echo "  Start ML service: cd ml && source .venv/bin/activate && python -m pipelines.inference.serve"
echo "  Start agent:      cd agent && source .venv/bin/activate && python src/main.py --config configs/dev.yaml"
echo ""
echo "  API Docs:      http://localhost:8000/api/docs"
echo "  Dashboard:     http://localhost:3000"
echo "  MinIO Console: http://localhost:9001  (admin/minioadmin123)"
echo ""
echo -e "${YELLOW}  IMPORTANT: Edit .env before deploying to any environment${NC}"
echo ""
