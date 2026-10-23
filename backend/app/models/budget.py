"""月度预算 ORM 实体（选做功能 1：预算提醒）。

设计要点：
- 一个月一条预算，`month`（YYYY-MM）作为主键；
- 金额与账单一致，使用 INTEGER「分」存储，避免浮点误差；
- 仅新增本表，不修改现有 categories / transactions 表。
"""

from sqlalchemy import CheckConstraint, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Budget(Base):
    """月度预算表：每个月份最多一条记录。"""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount > 0 AND amount <= 9999999999", name="ck_budgets_amount"),
        CheckConstraint(
            "month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'",
            name="ck_budgets_month",
        ),
    )

    month: Mapped[str] = mapped_column(Text, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 单位：分
    created_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("(datetime('now', '+8 hours'))"),
    )
    updated_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("(datetime('now', '+8 hours'))"),
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Budget month={self.month!r} amount={self.amount}>"
