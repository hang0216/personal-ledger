"""月度报表业务逻辑（spec §6.3 / §7.6 / §7.8、api-design §3.8）。

口径要点：
- 月份归属按业务日期 `date`，区间 `[当月第一天, 下月第一天)`，跨年正确；
- 所有汇总在整数「分」上完成，仅在输出时转「元」；
- `percentage` 由后端唯一计算并保留 2 位小数（ROUND_HALF_UP）；
- 总支出为 0 时 `expense_by_category` 直接返回 `[]`，**不做除法** → 不会出现 NaN。
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.money import cents_to_yuan
from app.core.timeutil import current_month, month_range
from app.core.validators import validate_month
from app.models.category import Category
from app.models.transaction import Transaction

_ONE_HUNDREDTH = Decimal("0.01")


def _percentage(amount_cents: int, total_cents: int) -> float:
    """占比 = 该分类支出 ÷ 总支出 × 100，保留 2 位小数（spec §6.3 R-21）。

    仅在 total_cents > 0 时被调用，从数学上排除除零与 NaN。
    """
    value = (
        Decimal(amount_cents) / Decimal(total_cents) * 100
    ).quantize(_ONE_HUNDREDTH, rounding=ROUND_HALF_UP)
    return float(value)


def _sum_cents(db: Session, type_: str, start: str, end: str) -> int:
    """区间内指定类型的金额合计（整数分），无记录记 0。"""
    total = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.type == type_,
            Transaction.date >= start,
            Transaction.date < end,
        )
    )
    return int(total or 0)


def monthly_report(db: Session, month: str | None = None) -> Any:
    """生成指定月份的报表；`month` 缺省回退业务时区当前月。"""
    month = validate_month(month) if month is not None else current_month()
    month_start, next_month_start = month_range(month)

    total_income_cents = _sum_cents(db, "income", month_start, next_month_start)
    total_expense_cents = _sum_cents(db, "expense", month_start, next_month_start)

    # 支出按分类分组求和，按金额降序（并列时按 id 升序保证结果稳定）
    rows = db.execute(
        select(
            Category.id,
            Category.name,
            func.sum(Transaction.amount).label("amount_cents"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.type == "expense",
            Transaction.date >= month_start,
            Transaction.date < next_month_start,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc(), Category.id.asc())
    ).all()

    expense_by_category = [
        {
            "category_id": category_id,
            "category_name": category_name,
            "amount": cents_to_yuan(amount_cents),
            "percentage": _percentage(amount_cents, total_expense_cents),
        }
        for category_id, category_name, amount_cents in rows
    ]

    return {
        "month": month,
        "total_income": cents_to_yuan(total_income_cents),
        "total_expense": cents_to_yuan(total_expense_cents),
        "balance": cents_to_yuan(total_income_cents - total_expense_cents),
        "expense_by_category": expense_by_category,
    }