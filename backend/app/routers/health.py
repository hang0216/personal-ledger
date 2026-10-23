"""健康检查接口（MVP-1 基础设施接口，不属于 spec §6.1 的 8 个业务端点）。

用途：验证后端进程与 SQLite 连接是否可用。
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import TIMEZONE
from app.core.response import ok
from app.database.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """返回服务状态与数据库连接状态；按统一响应结构输出（spec §6.2）。"""
    db.execute(text("SELECT 1"))
    return ok(
        {
            "status": "ok",
            "database": "connected",
            "timezone": TIMEZONE,
            "server_time": datetime.now(ZoneInfo(TIMEZONE)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
    )