"""数据库引擎与连接级 PRAGMA（architecture §6、database-design §8.1）。

关键点：SQLite 默认**不启用**外键，必须对每个连接显式执行
`PRAGMA foreign_keys = ON`，否则 `ON DELETE RESTRICT` 不会生效
（"无孤儿账单"能否成立的前提）。
"""

from sqlalchemy import create_engine, event

from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    # FastAPI 的线程池中可能由不同线程复用连接
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """每个新连接建立后立即打开外键约束。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()