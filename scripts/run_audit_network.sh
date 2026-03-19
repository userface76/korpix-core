#!/bin/bash
# KorPIX Audit Network 실행 스크립트
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

[ -f ".env" ] && export $(grep -v '^#' .env | xargs)

PORT=${AUDIT_GATEWAY_PORT:-8002}

echo "============================================"
echo "  KorPIX Audit Network v0.3.0  →  :$PORT"
echo "============================================"

exec uvicorn services.audit_network.src.main:app \
  --host 0.0.0.0 --port "$PORT" \
  --log-level "${LOG_LEVEL:-info}" --reload
