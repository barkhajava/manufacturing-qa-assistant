#!/usr/bin/env bash
set -e

# ── colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✔]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
abort() { echo -e "${RED}[✘]${NC} $1"; exit 1; }

echo ""
echo "  Manufacturing QA Assistant — local setup"
echo "  ─────────────────────────────────────────"
echo ""

# ── 1. virtual environment ──────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  warn ".venv not found — creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
info "Virtual environment active"

# ── 2. dependencies ─────────────────────────────────────────────────────────
pip install -q -r requirements.txt
info "Dependencies installed"

# ── 3. .env check ───────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  abort ".env was missing — created from .env.example.\n       Open .env and add your ANTHROPIC_API_KEY, then re-run ./start.sh"
fi

if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
  abort "ANTHROPIC_API_KEY not set in .env\n       Get your key at https://console.anthropic.com/ then re-run ./start.sh"
fi
info ".env looks good"

# ── 4. seed database (only if empty) ────────────────────────────────────────
if [ ! -f "data/manufacturing.db" ]; then
  warn "Database not found — seeding 90 days of mock data..."
  python scripts/seed_data.py
  info "Database seeded"
else
  info "Database already exists — skipping seed"
fi

# ── 5. start server ─────────────────────────────────────────────────────────
echo ""
info "Starting server → http://localhost:8000"
echo ""
uvicorn app.main:app --reload
