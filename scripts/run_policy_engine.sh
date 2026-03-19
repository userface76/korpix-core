#!/bin/bash
# KorPIX Policy Engine 실행 스크립트
set -e
 
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
 
[ -f ".env" ] && export $(grep -v '^#' .env | xargs)
 
PORT=${POLICY_ENGINE_PORT:-8001}
 
echo "============================================"
echo "  KorPIX Policy Engine v0.1.0  →  :$PORT"
echo "============================================"
 
exec uvicorn services.policy_engine.src.main:app \
  --host 0.0.0.0 --port "$PORT" \
  --log-level "${LOG_LEVEL:-info}" --reload
 
