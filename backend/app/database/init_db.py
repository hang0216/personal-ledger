"""数据库初始化（architecture §6 database/init_db.py、database-design §7 / §8）。

职责：
1. 确保数据库文件所在目录存在；
2. 建表（categories / transactions / budgets）；
3. 幂等写入 13 条预置分类（仅当 categories 为空时）。
"""

import logging

from sqlalchemy import func, select

from app.core.config import DATABASE_FILE
from app.database.base import Base
from app.database.engine import engine
from app.database.session import SessionLocal
# 导入模型以注册到 Base.metadata（建表前提）
from app.models.budget import Budget  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401

logger = logging.getLogger(__name__)

# 预置分类：13 条（database-design §7，严格取自 spec §4.3，不自行增加）
PRESET_CATEGORIES: list[tuple[int, str, str]] = [
    (1, "工资", "income"),
    (2, "奖金", "income"),
    (3, "兼职", "income"),
    (4, "投资收益", "income"),
    (5, "其他收入", "income"),
    (6, "餐饮", "expense"),
    (7, "交通", "expense"),
    (8, "购物", "expense"),
    (9, "居住", "expense"),
    (10, "娱乐", "expense"),
    (11, "医疗", "expense"),
    (12, "学习", "expense"),
    (13, "其他支出", "expense"),
]


def init_db() -> None:
    """初始化数据库文件、表结构与预置分类（幂等）。"""
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _seed_categories()
    logger.info("数据库初始化完成：%s", DATABASE_FILE)


def _seed_categories() -> None:
    """仅当 categories 为空时写入预置分类，避免重复插入。"""
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Category))
        if count:
            return
        db.add_all(
            Category(id=category_id, name=name, type=type_)
            for category_id, name, type_ in PRESET_CATEGORIES
        )
        db.commit()
        logger.info("已写入 %d 条预置分类", len(PRESET_CATEGORIES))