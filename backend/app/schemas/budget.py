"""月度预算数据契约（选做功能 1）。"""

from typing import Any

from pydantic import BaseModel


class BudgetUpsert(BaseModel):
    """设置月度预算请求体；`amount` 单位为「元」。"""

    month: str | None = None
    amount: Any


class BudgetQuery(BaseModel):
    """查询月度预算；`month` 缺省回退业务时区当前月。"""

    month: str | None = None


class BudgetOut(BaseModel):
    """月度预算响应体；未设置时 `amount` 为 null。"""

    month: str
    amount: float | None = None
