"""月度预算业务逻辑（选做功能 1：预算提醒）。

不感知 HTTP。预算金额与账单使用同一套金额校验与「分」存储口径；
同一月份重复设置时覆盖原值（UPSERT 语义）。
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.money import cents_to_yuan, yuan_to_cents
from app.core.timeutil import current_month, now_str
from app.core.validators import validate_amount, validate_month
from app.models.budget import Budget
from app.schemas.budget import BudgetUpsert


def get_budget(db: Session, month: str | None = None) -> dict:
    """查询指定月份预算；未设置时返回 `amount = null`。"""
    month = validate_month(month) if month is not None else current_month()
    row = db.get(Budget, month)
    return {
        "month": month,
        "amount": cents_to_yuan(row.amount) if row is not None else None,
    }


def set_budget(db: Session, payload: BudgetUpsert) -> dict:
    """设置或覆盖指定月份预算。"""
    month = validate_month(payload.month) if payload.month is not None else current_month()
    amount_cents = yuan_to_cents(validate_amount(payload.amount))
    timestamp = now_str()

    row = db.get(Budget, month)
    if row is None:
        db.add(
            Budget(
                month=month,
                amount=amount_cents,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
    else:
        row.amount = amount_cents
        row.updated_at = timestamp

    try:
        db.commit()
    except IntegrityError:
        # 并发首次写入同一月份时，退化为覆盖更新
        db.rollback()
        row = db.get(Budget, month)
        if row is None:
            raise AppError(ErrorCode.INTERNAL_ERROR) from None
        row.amount = amount_cents
        row.updated_at = timestamp
        db.commit()

    return {"month": month, "amount": cents_to_yuan(amount_cents)}
