"""分类数据契约（spec §5.2 / §6.1、api-design §3.5–§3.7、§4）。

`name` 声明为可选字符串，使"名称为空 / 非字符串"落到 spec E-10 的
专用文案"分类名称不合法"（由 core.validators 产生），而非 Pydantic 的通用 1001。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.transaction import TransactionType

CategoryType = TransactionType


class CategoryCreate(BaseModel):
    """新增分类请求体。"""

    name: str | None = None
    type: CategoryType


class CategoryOut(BaseModel):
    """分类响应体（created_at 为内部审计字段，不对外暴露）。"""

    id: int
    name: str
    type: CategoryType

    model_config = ConfigDict(from_attributes=True)


class CategoryQuery(BaseModel):
    """分类列表查询参数（api-design §3.5）：`type` 可选，缺省返回全部。"""

    type: CategoryType | None = None