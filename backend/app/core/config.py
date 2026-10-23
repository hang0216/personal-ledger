"""应用配置常量（architecture §5 core/config.py）。

本模块只放 MVP-1 实际使用的常量：数据库路径、业务时区、CORS 白名单。
金额上限、日期下界等业务常量在对应 MVP 落地时再补充。
"""

import os
from pathlib import Path

# backend/app/core/config.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]

# SQLite 单文件数据库：默认 backend/ledger.db（architecture §6、§12）
# 部署/测试可用 LEDGER_DB_PATH 指向独立文件，避免测试数据写入真实账本。
_db_path_env = os.environ.get("LEDGER_DB_PATH")
DATABASE_FILE = (
    Path(_db_path_env).expanduser().resolve()
    if _db_path_env
    else BACKEND_DIR / "ledger.db"
)
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# 前端生产构建产物：存在时由后端同源托管（architecture §11）
FRONTEND_DIST_DIR = BACKEND_DIR.parent / "frontend" / "dist"

# 业务时区：全局唯一口径（spec §8 R-06）
TIMEZONE = "Asia/Shanghai"

# 开发环境 CORS 允许源（architecture §11）
CORS_ALLOW_ORIGINS = ["http://localhost:5173"]

# 应用元信息
APP_TITLE = "个人记账本 API"
APP_VERSION = "0.1.0"

# 统一接口前缀（spec §6.1）
API_PREFIX = "/api"