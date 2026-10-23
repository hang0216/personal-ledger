"""SQLAlchemy ORM 声明式基类（architecture §6 database/base.py）。

后续 models/ 中的 categories、transactions 实体将继承 Base，
由 init_db 统一建表。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""