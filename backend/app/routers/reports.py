"""月度报表路由（api-design §3.8）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ok
from app.database.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.report import MonthlyReportOut, ReportQuery
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly", response_model=ApiResponse[MonthlyReportOut])
def monthly_report(
    query: Annotated[ReportQuery, Query()],
    db: Session = Depends(get_db),
) -> dict:
    """查询指定月份的收入总额、支出总额、结余与支出分类占比。"""
    return ok(report_service.monthly_report(db, month=query.month))