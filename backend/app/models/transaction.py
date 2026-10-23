"""收支记录 ORM 实体（database-design §2.2、§8.2）。

关键点：
- `amount` 为 INTEGER「分」，CHECK > 0 且 ≤ 上限（9,999,999,999 分）；
- `category_id` 外键 ON DELETE RESTRICT（无孤儿账单，spec §7.5 R-18）；
- `date` 字典序 = 时间序，支撑月度区间范围扫描；
- `type` 与 `categories.type` 的一致性由**应用层统一校验**（spec §4.2 R-02，不使用触发器）。
"""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Transaction(Base):
    """收支记录表（账单）。"""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "amount > 0 AND amount <= 9999999999", name="ck_transactions_amount"
        ),
        CheckConstraint("type IN ('income', 'expense')", name="ck_transactions_type"),
        CheckConstraint(
            "date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' "
            "AND date >= '2000-01-01'",
            name="ck_transactions_date",
        ),
        CheckConstraint(
            "note IS NULL OR length(note) <= 100", name="ck_transactions_note_len"
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 单位：分
    type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    date: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now', '+8 hours'))")
    )
    updated_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now', '+8 hours'))")
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Transaction id={self.id} amount={self.amount} date={self.date!r}>"