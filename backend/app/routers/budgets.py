"""月度预算路由（选做功能 1）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ok
from app.database.session import get_db
from app.schemas.budget import BudgetOut, BudgetQuery, BudgetUpsert
from app.schemas.common import ApiResponse
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=ApiResponse[BudgetOut])
def get_budget(
    query: Annotated[BudgetQuery, Query()],
    db: Session = Depends(get_db),
) -> dict:
    """查询月度预算；未设置时 `amount` 为 null。"""
    return ok(budget_service.get_budget(db, month=query.month))


@router.put("", response_model=ApiResponse[BudgetOut])
def set_budget(
    payload: BudgetUpsert,
    db: Session = Depends(get_db),
) -> dict:
    """设置或覆盖月度预算。"""
    return ok(budget_service.set_budget(db, payload))
