"""分类 ORM 实体（database-design §2.1、§8.2）。

说明：本 MVP 只实现账单 CRUD，因此**不提供分类接口**；
但 transactions.category_id 依赖本表，且"category_id 必须存在"
要求该表真实存在，故保留模型与预置数据（database-design §7）。
"""

from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Category(Base):
    """分类表：收入 / 支出分类（预置 + 用户自建）。"""

    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("length(name) BETWEEN 1 AND 20", name="ck_categories_name_len"),
        CheckConstraint("type IN ('income', 'expense')", name="ck_categories_type"),
        UniqueConstraint("name", "type", name="ux_categories_name_type"),
        # 自增 id 删除后不复用（database-design §2.1 / §7）
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("(datetime('now', '+8 hours'))"),
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<Category id={self.id} name={self.name!r} type={self.type!r}>"