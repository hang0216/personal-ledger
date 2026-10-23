"""统一业务校验函数（spec §5.1 R-14、architecture §10）。

本模块只包含**不依赖数据库与 HTTP 的纯函数**（architecture §13 约束：
core 禁止依赖上层模块）。分类存在性与类型一致性需要数据库访问，
放在 services 层，与这些纯函数一起构成 POST / PUT 共用的同一套校验。

错误码严格对齐 spec §9 / api-design §2.2。
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.errors import AppError, ErrorCode
from app.core.timeutil import today

# 金额上限：99,999,999.99 元（spec §5.1）
MAX_AMOUNT_YUAN = Decimal("99999999.99")
# 日期下界（spec §5.1 R-24）
MIN_DATE = date(2000, 1, 1)
# 备注上限（spec §5.1，按 Unicode 码点计数）
MAX_NOTE_LENGTH = 100
# 分类名称上限（spec §5.2，去首尾空格后按 Unicode 码点计数）
MAX_CATEGORY_NAME_LENGTH = 20
# 账单搜索关键词上限（与备注上限一致，按 Unicode 码点计数）
MAX_KEYWORD_LENGTH = 100

_DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_MONTH_PATTERN = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


def validate_amount(raw: Any) -> Decimal:
    """校验金额并返回元值 Decimal。

    规则：合法数字、> 0、最多 2 位小数（spec E-01 → 1002）；
          超过 99,999,999.99 元（spec E-02 → 1003）。
    """
    if raw is None or isinstance(raw, bool):
        raise AppError(ErrorCode.AMOUNT_INVALID)
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise AppError(ErrorCode.AMOUNT_INVALID) from None
    if not amount.is_finite():
        raise AppError(ErrorCode.AMOUNT_INVALID)
    if amount <= 0:
        raise AppError(ErrorCode.AMOUNT_INVALID)
    if amount.as_tuple().exponent < -2:  # 超过 2 位小数
        raise AppError(ErrorCode.AMOUNT_INVALID)
    if amount > MAX_AMOUNT_YUAN:
        raise AppError(ErrorCode.AMOUNT_OUT_OF_RANGE)
    return amount


def validate_date(raw: Any) -> str:
    """校验业务日期并返回标准 YYYY-MM-DD 字符串。

    规则：严格补零格式；≥ 2000-01-01；≤ 业务时区"今天"（spec E-06 → 1004）。
    """
    if not isinstance(raw, str) or not _DATE_PATTERN.match(raw):
        raise AppError(ErrorCode.DATE_INVALID)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        raise AppError(ErrorCode.DATE_INVALID) from None
    if parsed < MIN_DATE or parsed > today():
        raise AppError(ErrorCode.DATE_INVALID)
    return raw


def validate_month(raw: Any) -> str:
    """校验月份并返回 YYYY-MM 字符串（spec E-07 → 1005）。"""
    if not isinstance(raw, str) or not _MONTH_PATTERN.match(raw):
        raise AppError(ErrorCode.MONTH_INVALID)
    return raw


def validate_date_range(
    start: Any, end: Any
) -> tuple[str | None, str | None]:
    """校验搜索日期范围：两端均可选，格式与上下界复用 validate_date。

    开始日期晚于结束日期时返回 1004「日期范围不合法」。
    """
    start_str = validate_date(start) if start else None
    end_str = validate_date(end) if end else None
    if start_str is not None and end_str is not None and start_str > end_str:
        raise AppError(ErrorCode.DATE_INVALID, "日期范围不合法")
    return start_str, end_str


def validate_keyword(raw: Any) -> str | None:
    """校验备注搜索关键词：去首尾空格，空串视为未提供，最长 100 码点。"""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise AppError(ErrorCode.PARAM_INVALID)
    keyword = raw.strip()
    if not keyword:
        return None
    if len(keyword) > MAX_KEYWORD_LENGTH:
        raise AppError(ErrorCode.PARAM_INVALID, "关键词长度超限")
    return keyword


def validate_note(raw: Any) -> str | None:
    """校验备注（spec E-08 → 1001，专用文案"备注长度超限"）。"""
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise AppError(ErrorCode.PARAM_INVALID)
    if len(raw) > MAX_NOTE_LENGTH:  # 按 Unicode 码点计数
        raise AppError(ErrorCode.PARAM_INVALID, "备注长度超限")
    return raw


def validate_category_name(raw: Any) -> str:
    """校验并规范化分类名称：去首尾空格后 1–20 个 Unicode 码点。

    spec E-10：名称为空 / 超长 → 1001 且文案为专用文案"分类名称不合法"
    （区别于 E-03 的通用"参数不合法"）。
    返回去空格后的名称，供重名比较与入库使用（spec §4.1 唯一约束口径）。
    """
    if not isinstance(raw, str):
        raise AppError(ErrorCode.PARAM_INVALID, "分类名称不合法")
    name = raw.strip()
    if not 1 <= len(name) <= MAX_CATEGORY_NAME_LENGTH:
        raise AppError(ErrorCode.PARAM_INVALID, "分类名称不合法")
    return name