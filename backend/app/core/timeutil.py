"""业务时区与月份区间工具（spec §5.3 / §7.6、architecture §5 timeutil.py）。

业务时区统一为 Asia/Shanghai（spec §8 R-06）；"今天 / 当前月"由服务端计算。
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)


def now() -> datetime:
    """业务时区当前时间。"""
    return datetime.now(TZ)


def now_str() -> str:
    """业务时区时间戳，格式 YYYY-MM-DD HH:MM:SS（database-design §2.2）。"""
    return now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> date:
    """业务时区"今天"。"""
    return now().date()


def current_month() -> str:
    """业务时区"当前月"，格式 YYYY-MM。"""
    return now().strftime("%Y-%m")


def month_range(month: str) -> tuple[str, str]:
    """返回月份区间 [当月第一天(含), 下月第一天(不含))，按自然月进位（含跨年）。

    例如 month="2025-12" -> ("2025-12-01", "2026-01-01")。
    """
    year = int(month[:4])
    mon = int(month[5:7])
    start = f"{year:04d}-{mon:02d}-01"
    if mon == 12:
        next_year, next_mon = year + 1, 1
    else:
        next_year, next_mon = year, mon + 1
    return start, f"{next_year:04d}-{next_mon:02d}-01"