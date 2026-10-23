#!/usr/bin/env bash
# CloudStudio / Linux 一键启动：前后端同源，后端同时提供页面与 /api
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# 生产模式：关闭 /docs、/redoc、/openapi.json
export LEDGER_ENV="${LEDGER_ENV:-production}"

# 数据目录放在代码目录之外，重新上传代码不会覆盖账本
export LEDGER_DB_PATH="${LEDGER_DB_PATH:-$HOME/personal-ledger-data/ledger.db}"
mkdir -p "$(dirname "$LEDGER_DB_PATH")"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

# 安装后端依赖（首次启动或依赖变更时）
"$PY" -m pip install --quiet -r backend/requirements.txt

# 前端产物缺失时才构建，避免免费空间因 npm install 内存不足
if [ ! -f frontend/dist/index.html ]; then
  (cd frontend && npm install && npm run build)
fi

cd backend
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
