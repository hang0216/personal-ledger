"""账单业务逻辑：新增、查询、修改、删除（spec §7.1–§7.3、api-design §3.1–§3.4）。

本模块是账单的唯一业务入口，不感知 HTTP。
POST 与 PUT 共用同一个 `_validate_payload`，保证"同输入同错误码"（spec R-14 / AC-24）。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.money import cents_to_yuan, yuan_to_cents
from app.core.timeutil import current_month, month_range, now_str
from app.core.validators import (
    validate_amount,
    validate_date,
    validate_date_range,
    validate_keyword,
    validate_month,
    validate_note,
)
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate


def _validate_payload(db: Session, payload: TransactionCreate) -> tuple[int, str, str | None]:
    """POST / PUT 共用的统一校验：返回 (金额分, 日期, 备注)。

    顺序：金额 → 日期 → 备注 → 分类存在性 → 分类类型一致性。
    """
    amount_yuan = validate_amount(payload.amount)
    date_str = validate_date(payload.date)
    note = validate_note(payload.note)

    category = db.get(Category, payload.category_id)
    if category is None:
        # spec E-05 / api-design §2.2：分类不存在
        raise AppError(ErrorCode.CATEGORY_NOT_FOUND)
    if category.type != payload.type:
        # spec E-04：分类类型与收支类型不一致
        raise AppError(ErrorCode.CATEGORY_TYPE_MISMATCH)

    return yuan_to_cents(amount_yuan), date_str, note


def _to_dict(transaction: Transaction) -> dict:
    """ORM 实体 → 接口输出（金额分 → 元）。"""
    return {
        "id": transaction.id,
        "amount": cents_to_yuan(transaction.amount),
        "type": transaction.type,
        "category_id": transaction.category_id,
        "date": transaction.date,
        "note": transaction.note,
    }


def list_transactions(
    db: Session,
    month: str | None = None,
    type_: str | None = None,
    category_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
) -> list[dict]:
    """查询账单列表：普通模式按月，搜索模式按日期范围 / 备注关键词。

    - 普通模式：月份归属按业务日期 `date`（spec R-03）；
    - 搜索模式：提供 `start_date` / `end_date` / `keyword` 任一参数时启用，
      跨月查询，`month` 不生效；
    - 两种模式都支持 `type` / `category_id` 进一步筛选；
    - 排序 `date DESC, id DESC`（spec R-12）；
    - `category_id` 不校验分类是否存在；矛盾筛选自然返回空数组。
    """
    start_str, end_str = validate_date_range(start_date, end_date)
    keyword = validate_keyword(keyword)
    search_mode = start_str is not None or end_str is not None or keyword is not None

    stmt = select(Transaction)
    if search_mode:
        if start_str is not None:
            stmt = stmt.where(Transaction.date >= start_str)
        if end_str is not None:
            stmt = stmt.where(Transaction.date <= end_str)
        if keyword is not None:
            # autoescape：备注中的 % / _ 按字面量匹配
            stmt = stmt.where(Transaction.note.contains(keyword, autoescape=True))
    else:
        month = validate_month(month) if month is not None else current_month()
        month_start, next_month_start = month_range(month)
        stmt = stmt.where(
            Transaction.date >= month_start, Transaction.date < next_month_start
        )

    if type_ is not None:
        stmt = stmt.where(Transaction.type == type_)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())

    return [_to_dict(row) for row in db.execute(stmt).scalars().all()]


def create_transaction(db: Session, payload: TransactionCreate) -> dict:
    """新增一笔账单。"""
    amount_cents, date_str, note = _validate_payload(db, payload)
    timestamp = now_str()

    transaction = Transaction(
        amount=amount_cents,
        type=payload.type,
        category_id=payload.category_id,
        date=date_str,
        note=note,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return _to_dict(transaction)


def update_transaction(db: Session, transaction_id: int, payload: TransactionCreate) -> dict:
    """全量覆盖更新一笔账单（校验与新增完全一致）。"""
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        # spec E-12：编辑不存在的记录
        raise AppError(ErrorCode.TRANSACTION_NOT_FOUND)

    amount_cents, date_str, note = _validate_payload(db, payload)

    transaction.amount = amount_cents
    transaction.type = payload.type
    transaction.category_id = payload.category_id
    transaction.date = date_str
    transaction.note = note
    transaction.updated_at = now_str()  # database-design §4.2 A-08：应用层维护

    db.commit()
    db.refresh(transaction)
    return _to_dict(transaction)


def delete_transaction(db: Session, transaction_id: int) -> None:
    """删除一笔账单。"""
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise AppError(ErrorCode.TRANSACTION_NOT_FOUND)

    db.delete(transaction)
    db.commit()