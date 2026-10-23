"""FastAPI 应用入口（architecture §5 main.py、§9 异常处理、§11 CORS）。

职责：创建应用实例、注册 CORS、注册统一异常处理器、注册路由、启动时初始化数据库。
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import (
    API_PREFIX,
    APP_TITLE,
    APP_VERSION,
    CORS_ALLOW_ORIGINS,
    FRONTEND_DIST_DIR,
)
from app.core.exceptions import register_exception_handlers
from app.database.init_db import init_db
from app.routers import budgets, categories, health, reports, transactions

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化数据库（建库 + 建表 + 预置分类，幂等）。"""
    init_db()
    yield


# 生产环境（LEDGER_ENV=production）关闭 /docs、/redoc 与 /openapi.json，避免公开调试入口
_IS_PRODUCTION = os.environ.get("LEDGER_ENV", "development").lower() == "production"

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    openapi_url=None if _IS_PRODUCTION else "/openapi.json",
)

# 开发环境 CORS：允许 Vue 开发服务器访问（architecture §11，spec §8）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# 统一错误出口（architecture §9）
register_exception_handlers(app)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(transactions.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(budgets.router, prefix=API_PREFIX)

# 生产同源托管：存在前端构建产物（frontend/dist）时，由后端统一提供页面与 API。
# 开发环境未构建 dist 时不生效，前后端仍按 5173 + 8000 分离运行。
if FRONTEND_DIST_DIR.is_dir():
    _dist_root = FRONTEND_DIST_DIR.resolve()
    _assets_dir = _dist_root / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        """静态资源原样返回；其余路径回退 index.html（vue-router history 模式）。"""
        if full_path in {"api", "docs", "redoc", "openapi.json"} or full_path.startswith(
            "api/"
        ):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_dist_root / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_dist_root):
            return FileResponse(candidate)
        return FileResponse(_dist_root / "index.html")