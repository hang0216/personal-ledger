"""分类路由（api-design §3.5–§3.7）。

仅做参数解析、调用 service 与统一响应组装，不含业务规则（architecture §7.1）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ok
from app.database.session import get_db
from app.schemas.category import CategoryCreate, CategoryOut, CategoryQuery
from app.schemas.common import ApiResponse
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=ApiResponse[list[CategoryOut]])
def list_categories(
    query: Annotated[CategoryQuery, Query()],
    db: Session = Depends(get_db),
) -> dict:
    """查询分类列表，可按收支类型筛选（`data` 恒为数组）。"""
    return ok(category_service.list_categories(db, type_=query.type))


@router.post("", response_model=ApiResponse[CategoryOut])
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
) -> dict:
    """新增收入 / 支出分类。"""
    return ok(category_service.create_category(db, payload))


@router.delete("/{category_id}", response_model=ApiResponse[dict | None])
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """删除分类：存在账单引用时拒绝删除。"""
    category_service.delete_category(db, category_id)
    return ok(None)