"""
Vayuntra — One-Command Startup Script
Run: python start.py

What this does:
1. Checks PostgreSQL connection
2. Creates all database tables
3. Seeds demo data (only if empty)
4. Starts FastAPI on http://localhost:8000
5. Opens browser automatically

Login: admin@vayuntra.demo / Vayuntra@123
"""
import subprocess
import sys
import os
import time
import asyncio
import webbrowser

# ── Change to backend directory ──────────────────────
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

def banner():
    print("""
╔══════════════════════════════════════════════════════╗
║          VAYUNTRA — Autonomous AI Cyber Defense      ║
║                   Starting Platform...               ║
╚══════════════════════════════════════════════════════╝
""")

async def check_db():
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL connection OK")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("""
Fix: Make sure PostgreSQL is running and update backend/.env:
  DATABASE_URL=postgresql+asyncpg://YOUR_USER:YOUR_PASSWORD@localhost:5432/vayuntra

Quick setup (run in psql):
  CREATE DATABASE vayuntra;
  CREATE USER vayuntra_user WITH PASSWORD 'vayuntra123';
  GRANT ALL PRIVILEGES ON DATABASE vayuntra TO vayuntra_user;

Then update .env:
  DATABASE_URL=postgresql+asyncpg://vayuntra_user:vayuntra123@localhost:5432/vayuntra
""")
        return False

async def seed_if_needed():
    from app.core.database import engine, AsyncSessionLocal
    from app.db.models.models import Base, User
    from sqlalchemy import select

    # Create tables
    from app.db.models.models import Base as ModelBase
    async with engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.create_all)
    print("✅ Database tables ready")

    # Check if threats are fully seeded (expect 30)
    from app.db.models.models import Threat
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Threat))
        threat_count = len(result.scalars().all())
        if threat_count >= 30:
            print(f"✅ Demo data already exists ({threat_count} threats) — skipping seed")
            return
        print(f"🌱 Only {threat_count} threats found — reseeding to 30...")

    # Run seed
    print("🌱 Seeding demo data...")
    proc = subprocess.run([sys.executable, "seed_data.py"], capture_output=True, text=True)
    if proc.returncode == 0:
        print(proc.stdout)
    else:
        print("⚠️  Seed warning:", proc.stderr[:200])

def main():
    banner()

    # Run async setup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ok = loop.run_until_complete(check_db())
    if not ok:
        sys.exit(1)

    loop.run_until_complete(seed_if_needed())

    print("""
══════════════════════════════════════════════════════
  🚀 Starting Vayuntra on http://localhost:8000
  📊 Dashboard:  http://localhost:8000
  📖 API Docs:   http://localhost:8000/api/docs
  🔑 Login:      admin@vayuntra.demo / Vayuntra@123
══════════════════════════════════════════════════════
""")

    # Open browser after 2 seconds
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Start uvicorn
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])

if __name__ == "__main__":
    main()
