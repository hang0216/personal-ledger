"""月度报表数据契约（spec §6.3 / §7.6、api-design §3.8、§4）。

金额类型严格按 R-01 区分：
- `total_income` / `total_expense` / `expense_by_category[].amount` 为 AggregateAmount（≥ 0，允许 0.00）；
- `balance` 为 SignedAmount（可为负）。
"""

from pydantic import BaseModel


class CategoryExpenseOut(BaseModel):
    """某个支出分类的金额与占比。"""

    category_id: int
    category_name: str
    amount: float
    percentage: float


class MonthlyReportOut(BaseModel):
    """月度报表响应体。"""

    month: str
    total_income: float
    total_expense: float
    balance: float
    expense_by_category: list[CategoryExpenseOut]


class ReportQuery(BaseModel):
    """月度报表查询参数（api-design §3.8）。

    `month` 声明为可选字符串，使格式错误落到 spec E-07 的 1005（`月份不合法`），
    而非 Pydantic 的通用 1001；缺省时回退业务时区当前月。
    """

    month: str | None = None