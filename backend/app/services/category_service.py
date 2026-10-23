"""分类业务逻辑：查询、新增、删除（spec §5.2 / §7.5、api-design §3.5–§3.7）。

不感知 HTTP。删除采用"有引用则拒绝"策略（spec §7.5 R-18）：
应用层引用计数 + 数据库 `ON DELETE RESTRICT` 双重防护，不产生孤儿账单。
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.validators import validate_category_name
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.category import CategoryCreate


def _to_dict(category: Category) -> dict:
    return {"id": category.id, "name": category.name, "type": category.type}


def list_categories(db: Session, type_: str | None = None) -> list[dict]:
    """查询分类列表：可按收支类型筛选，排序为 type 升序、id 升序（api-design §3.5）。"""
    stmt = select(Category)
    if type_ is not None:
        stmt = stmt.where(Category.type == type_)
    stmt = stmt.order_by(Category.type.asc(), Category.id.asc())
    return [_to_dict(row) for row in db.execute(stmt).scalars().all()]


def create_category(db: Session, payload: CategoryCreate) -> dict:
    """新增分类：名称规范化后校验，同类型下不可重名（spec E-09 / E-10）。"""
    name = validate_category_name(payload.name)

    duplicated = db.scalar(
        select(func.count())
        .select_from(Category)
        .where(Category.name == name, Category.type == payload.type)
    )
    if duplicated:
        raise AppError(ErrorCode.CATEGORY_NAME_DUPLICATE)

    category = Category(name=name, type=payload.type)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        # 唯一约束兜底：并发下应用层校验可能漏过（spec E-09）
        db.rollback()
        raise AppError(ErrorCode.CATEGORY_NAME_DUPLICATE) from None
    db.refresh(category)
    return _to_dict(category)


def delete_category(db: Session, category_id: int) -> None:
    """删除分类：不存在 → 1007；被账单引用 → 1010（spec E-11 / E-17）。"""
    category = db.get(Category, category_id)
    if category is None:
        raise AppError(ErrorCode.CATEGORY_NOT_FOUND)

    referenced = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.category_id == category_id)
    )
    if referenced:
        # 文案严格取自 spec §9 E-11，不返回引用条数
        raise AppError(ErrorCode.CATEGORY_IN_USE)

    db.delete(category)
    try:
        db.commit()
    except IntegrityError:
        # 数据库 ON DELETE RESTRICT 兜底（spec §7.5 双重防护）
        db.rollback()
        raise AppError(ErrorCode.CATEGORY_IN_USE) from None