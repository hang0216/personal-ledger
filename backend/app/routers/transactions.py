"""账单路由（api-design §3.1–§3.4）。

仅做参数解析、调用 service 与统一响应组装，不含业务规则（architecture §7.1）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ok
from app.database.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionQuery,
    TransactionUpdate,
)
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=ApiResponse[list[TransactionOut]])
def list_transactions(
    query: Annotated[TransactionQuery, Query()],
    db: Session = Depends(get_db),
) -> dict:
    """查询账单列表：按月筛选，或按日期范围 / 备注关键词跨月搜索。

    可选按类型 / 分类筛选；无数据或筛选矛盾时返回 `[]`（HTTP 200）。
    """
    return ok(
        transaction_service.list_transactions(
            db,
            month=query.month,
            type_=query.type,
            category_id=query.category_id,
            start_date=query.start_date,
            end_date=query.end_date,
            keyword=query.keyword,
        )
    )


@router.post("", response_model=ApiResponse[TransactionOut])
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
) -> dict:
    """新增一笔账单。"""
    return ok(transaction_service.create_transaction(db, payload))


@router.put("/{transaction_id}", response_model=ApiResponse[TransactionOut])
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """编辑一笔账单（全量覆盖，校验与新增一致）。"""
    return ok(transaction_service.update_transaction(db, transaction_id, payload))


@router.delete("/{transaction_id}", response_model=ApiResponse[dict | None])
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """删除一笔账单。"""
    transaction_service.delete_transaction(db, transaction_id)
    return ok(None)